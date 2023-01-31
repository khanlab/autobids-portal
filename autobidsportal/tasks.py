"""Utilities to handle tasks put on the queue."""

from datetime import datetime
import tempfile
import pathlib
import re
from shutil import copy2
import subprocess

from datalad.support.gitrepo import GitRepo
from rq import get_current_job

from autobidsportal.app import create_app
from autobidsportal.models import (
    db,
    Study,
    Task,
    Cfmm2tarOutput,
    DataladDataset,
    Tar2bidsOutput,
    DatasetType,
    User,
)
from autobidsportal.datalad import (
    RiaDataset,
    ensure_dataset_exists,
    finalize_dataset_changes,
    get_tar_file_from_dataset,
    get_all_dataset_content,
    archive_dataset,
)
from autobidsportal.bids import merge_datasets
from autobidsportal.dcm4cheutils import (
    gen_utils,
    Tar2bidsArgs,
    Cfmm2tarError,
    Cfmm2tarTimeoutError,
    Tar2bidsError,
)
from autobidsportal.dicom import get_study_records
from autobidsportal.email import send_email
from autobidsportal.filesystem import gen_dir_dict, render_dir_dict


app = create_app()
app.app_context().push()


def _set_task_progress(progress):
    if not (job := get_current_job()):
        return
    job.meta["progress"] = progress
    job.save_meta()
    task = Task.query.get(job.id)
    if task.user is not None:
        task.user.add_notification(
            "task_progress", {"task_id": job.id, "progress": progress}
        )
    if progress == 100:
        task.complete = True
        task.success = True
        task.error = None
        task.end_time = datetime.utcnow()
    db.session.commit()


def _set_task_error(msg):
    if not (job := get_current_job()):
        return
    task = Task.query.get(job.id)
    task.complete = True
    task.success = False
    task.error = msg[:128] if msg else ""
    task.end_time = datetime.utcnow()
    db.session.commit()


def _append_task_log(log):
    if not (job := get_current_job()):
        return
    task = Task.query.get(job.id)
    task.log = "".join([task.log if task.log is not None else "", log])
    db.session.commit()


def run_cfmm2tar_with_retries(out_dir, target, study_description):
    """Run cfmm2tar, retrying multiple times if it times out.

    Parameters
    ----------
    out_dir : str
        Directory to which to download tar files.
    target : str
        PatientName string.
    study_description : str
        "Principal^Project" to search for.

    Raises
    ------
    Cfmm2tarTimeoutError
        If cfmm2tar times out too many times.
    """
    for attempt in range(1, 6):
        try:
            cfmm2tar_result, log = gen_utils().run_cfmm2tar(
                out_dir=out_dir,
                patient_name=target,
                project=study_description,
            )
        except Cfmm2tarTimeoutError as err:
            if attempt < 5:
                app.logger.warning(
                    "cfmm2tar timeout after %i attempt(s) (target %s).",
                    attempt,
                    target,
                )
                continue
            raise err
        break
    return cfmm2tar_result, log


def record_cfmm2tar(tar_file, uid, study_id, attached_tar_file=None):
    """Parse cfmm2tar output files and record them in the db.

    Parameters
    ----------
    tar_file : str
        Name of the downloaded tar file.
    uid : str
        StudyInstanceUID of the tar file..
    study_id : int
        ID of the study associated with this cfmm2tar output.
    attached_tar_file : str, optional
        Name of the attached tar file.

    Raises
    ------
    Cfmm2tarError
        If cfmm2tar fails.
    """
    try:
        date_match = re.fullmatch(
            r"[a-zA-Z]+_[\w\-]+_(\d{8})_[\w\-]+_[\.a-zA-Z\d]+\.tar", tar_file
        ).group(1)
    except AttributeError as err:
        raise Cfmm2tarError(f"Output {tar_file} could not be parsed.") from err

    cfmm2tar = Cfmm2tarOutput(
        study_id=study_id,
        tar_file=tar_file,
        uid=uid.strip(),
        date=datetime(
            int(date_match[0:4]),
            int(date_match[4:6]),
            int(date_match[6:8]),
        ),
        attached_tar_file=attached_tar_file,
    )
    db.session.add(cfmm2tar)
    db.session.commit()


def process_uid_file(uid_path):
    """Read a UID file, delete it, and return the UID."""
    with open(uid_path, "r", encoding="utf-8") as uid_file:
        uid = uid_file.read()
    pathlib.Path(uid_path).unlink()
    return uid


def find_studies_to_download(study, study_description, explicit_scans=None):
    """Find the studies to download, or override them with explicit scans."""
    existing_outputs = Cfmm2tarOutput.query.filter_by(study_id=study.id).all()
    if explicit_scans is not None:
        return [
            scan
            for scan in explicit_scans
            if scan["StudyInstanceUID"]
            not in {output.uid.strip() for output in existing_outputs}
        ]
    return [
        record
        for record in get_study_records(study, description=study_description)
        if record["StudyInstanceUID"]
        not in {output.uid.strip() for output in existing_outputs}
    ]


def check_tar_files(study_id, explicit_scans=None, user_id=None):
    """Launch cfmm2tar if there are any new tar files."""
    study = Study.query.get(study_id)
    user = User.query.get(user_id) if user_id is not None else None
    studies_to_download = find_studies_to_download(
        study, f"{study.principal}^{study.project_name}", explicit_scans
    )
    if not studies_to_download:
        return
    new_studies = ", ".join(
        [new_study["PatientName"] for new_study in studies_to_download]
    )
    Task.launch_task(
        "run_cfmm2tar",
        f"Get tar files {new_studies} in study {study_id}",
        study_id,
        studies_to_download,
        user=user,
        study_id=study_id,
        timeout=app.config["CFMM2TAR_TIMEOUT"],
    )


def ensure_complete(error_log):
    """Ensure a cfmm2tar job is complete."""

    def decorate(task):
        def wrapped_task(*args):
            try:
                task(*args)
            finally:
                if not Task.query.get(get_current_job().id).complete:
                    app.logger.error(error_log)
                    _set_task_error("Unknown uncaught exception")

        return wrapped_task

    return decorate


def handle_cfmm2tar(download_dir, study, target, dataset):
    """Run cfmm2tar on one target."""

    _, log = run_cfmm2tar_with_retries(
        str(download_dir),
        target["PatientName"],
        f"{study.principal}^{study.project_name}",
    )

    _append_task_log(log)
    app.logger.info(
        "Successfully ran cfmm2tar for target %s.",
        target["PatientName"],
    )
    app.logger.info("Log: %s", log)

    if not (
        created_files := list(pathlib.Path(download_dir).iterdir())
    ):
        raise Cfmm2tarError(
            f"No cfmm2tar results parsed for target f{target}. "
            "Check the stderr for more information."
        )

    tar, uid_file, attached_tar = None, None, None
    for file_ in created_files:
        if file_.name.endswith(".attached.tar"):
            attached_tar = file_.name
        elif file_.name.endswith(".uid"):
            uid_file = file_
        elif file_.name.endswith(".tar"):
            tar = file_.name
        else:
            app.logger.warning("Unknown cfmm2tar output: %s", file_)
    if not tar:
        raise Cfmm2tarError("No tar file produced.")
    if not uid_file:
        raise Cfmm2tarError("No uid file produced.")

    created_files = list(set(created_files) - {uid_file})
    uid = process_uid_file(uid_file)

    with RiaDataset(
        download_dir, dataset.ria_alias, ria_url=dataset.custom_ria_url
    ) as path_dataset:
        for file_ in created_files:
            copy2(file_, path_dataset / file_.name)
        finalize_dataset_changes(str(path_dataset), "Add new tar file.")
    record_cfmm2tar(
        tar,
        uid,
        study.id,
        attached_tar_file=attached_tar,
    )


@ensure_complete("Cfmm2tar failed for an unknown reason.")
def run_cfmm2tar(study_id, studies_to_download):
    """Run cfmm2tar for a given study

    This will check which patients have already been downloaded, download any
    new ones, and record them in the database.

    Parameters
    ----------
    study_id : int
        ID of the study for which to run cfmm2tar.
    studies_to_download : list of dict, optional
        List of scans to get with cfmm2tar, where each scan is represented by
        a dict with keys "StudyInstanceUID" and "PatientName".
    """
    _set_task_progress(0)
    study = Study.query.get(study_id)
    app.logger.info(
        "Running cfmm2tar for patients %s in study %i",
        [record["PatientName"] for record in studies_to_download],
        study.id,
    )

    dataset = ensure_dataset_exists(study.id, DatasetType.SOURCE_DATA)
    error_msgs = []
    for target in studies_to_download:
        with tempfile.TemporaryDirectory(
            dir=app.config["CFMM2TAR_DOWNLOAD_DIR"]
        ) as download_dir:
            try:
                handle_cfmm2tar(download_dir, study, target, dataset)
            except Cfmm2tarError as err:
                app.logger.error("cfmm2tar failed: %s", err)
                _append_task_log(str(err))
                error_msgs.append(str(err))
                continue
    if len(studies_to_download) > 0:
        send_email(
            "New cfmm2tar run",
            "\n".join(
                [
                    (
                        "Attempted to download the following tar files "
                        f"for study {study.id}:"
                    )
                ]
                + [
                    f"PatientName: {target['PatientName']}"
                    for target in studies_to_download
                ]
                + ["\nErrors:\n"]
                + error_msgs
            ),
        )

    if len(error_msgs) > 0:
        _set_task_error("\n".join(error_msgs))
    else:
        _set_task_progress(100)


def find_unprocessed_tar_files(study_id):
    """Check for tar files that aren't in the dataset and add them."""
    study = Study.query.get(study_id)
    dataset = DataladDataset.query.filter_by(
        study_id=study.id, dataset_type=DatasetType.RAW_DATA
    ).one_or_none()
    existing_tar_file_ids = (
        set()
        if dataset is None
        else {out.id for out in dataset.cfmm2tar_outputs}
    )
    new_tar_file_ids = {
        tar_file.id for tar_file in study.cfmm2tar_outputs
    } - existing_tar_file_ids
    if not new_tar_file_ids:
        return
    Task.launch_task(
        "run_tar2bids",
        "tar2bids run for all new tar files",
        study_id,
        list(new_tar_file_ids),
        study_id=study_id,
        timeout=app.config["TAR2BIDS_TIMEOUT"],
    )


@ensure_complete("tar2bids failed with an uncaught exception.")
def run_tar2bids(study_id, tar_file_ids):
    """Run tar2bids for a specific study.

    Parameters
    ----------
    study_id : int
        ID of the study the tar files are associated with.

    tar_file_ids : list of int
        IDs of the tar files to be included in the tar2bids run.

    Raises
    ------
    Tar2bidsError
        If tar2bids fails.
    """
    _set_task_progress(0)
    study = Study.query.get(study_id)
    cfmm2tar_outputs = [
        Cfmm2tarOutput.query.get(tar_file_id) for tar_file_id in tar_file_ids
    ]
    dataset_tar = ensure_dataset_exists(study_id, DatasetType.SOURCE_DATA)
    dataset_bids = ensure_dataset_exists(study_id, DatasetType.RAW_DATA)
    with tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"]
    ) as bids_dir, tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_TEMP_DIR"]
    ) as temp_dir, tempfile.TemporaryDirectory(
        dir=app.config["CFMM2TAR_DOWNLOAD_DIR"]
    ) as download_dir, tempfile.NamedTemporaryFile(
        mode="w+",
        encoding="utf-8",
        buffering=1,
    ) as bidsignore:
        app.logger.info("Running tar2bids for study %i", study.id)
        if study.custom_bidsignore is not None:
            bidsignore.write(study.custom_bidsignore)
        for tar_out in cfmm2tar_outputs:
            with RiaDataset(
                download_dir,
                dataset_tar.ria_alias,
                ria_url=dataset_tar.custom_ria_url,
            ) as path_dataset_tar:
                tar_path = get_tar_file_from_dataset(
                    tar_out.tar_file, path_dataset_tar
                )
                try:
                    _append_task_log(
                        gen_utils().run_tar2bids(
                            Tar2bidsArgs(
                                output_dir=pathlib.Path(bids_dir) / "incoming",
                                tar_files=[tar_path],
                                heuristic=study.heuristic,
                                patient_str=study.subj_expr,
                                temp_dir=temp_dir,
                                bidsignore=None
                                if study.custom_bidsignore is None
                                else bidsignore.name,
                                deface=study.deface,
                            )
                        ),
                    )
                except Tar2bidsError as err:
                    app.logger.error("tar2bids failed: %s", err)
                    _set_task_error(
                        err.__cause__.stderr
                        if err.__cause__ is not None
                        else str(err),
                    )
                    _append_task_log(str(err))
                    _append_task_log("Dataset contents:\n")
                    _append_task_log(
                        "\n".join(
                            render_dir_dict(
                                gen_dir_dict(
                                    str(pathlib.Path(bids_dir) / "incoming"),
                                    {".git", ".datalad"},
                                )
                            )
                        ),
                    )
                    send_email(
                        "Failed tar2bids run",
                        "\n".join(
                            ["Tar2bids failed for tar files:"]
                            + [output.tar_file for output in cfmm2tar_outputs]
                            + [
                                (
                                    "Note: Some of the tar2bids runs may have "
                                    "completed. This email is sent if any of them "
                                    "fail."
                                ),
                                "Error:",
                                str(err),
                            ]
                        ),
                    )
                    raise err
            with RiaDataset(
                pathlib.Path(bids_dir) / "existing",
                dataset_bids.ria_alias,
                ria_url=dataset_bids.custom_ria_url,
            ) as path_dataset_study:
                merge_datasets(
                    pathlib.Path(bids_dir) / "incoming", path_dataset_study
                )
                finalize_dataset_changes(
                    path_dataset_study,
                    f"Ran tar2bids on tar file {tar_path}",
                )
                study.dataset_content = gen_dir_dict(
                    path_dataset_study, {".git", ".datalad"}
                )
                tar_out.datalad_dataset = dataset_bids
                db.session.commit()
        db.session.add(
            Tar2bidsOutput(
                study_id=study_id,
                cfmm2tar_outputs=cfmm2tar_outputs,
                bids_dir=None,
                heuristic=study.heuristic,
            )
        )
        db.session.commit()
    _set_task_progress(100)
    if len(tar_file_ids) > 0:
        send_email(
            "Successful tar2bids run.",
            "\n".join(
                ["Tar2bids successfully run for tar files:"]
                + [output.tar_file for output in cfmm2tar_outputs]
            ),
        )


@ensure_complete("raw dataset archival failed with an uncaught exception.")
def archive_raw_data(study_id):
    """Clone a study dataset and archive it if necessary."""
    _set_task_progress(0)
    study = Study.query.get(study_id)
    if (study.custom_ria_url is not None) or (study.dataset_content is None):
        _set_task_progress(100)
        return
    dataset_raw = ensure_dataset_exists(study_id, DatasetType.RAW_DATA)
    with tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"]
    ) as dir_raw_data, RiaDataset(
        dir_raw_data,
        dataset_raw.ria_alias,
        ria_url=dataset_raw.custom_ria_url,
    ) as path_dataset_raw, tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"]
    ) as dir_archive:
        current_hexsha = GitRepo(str(path_dataset_raw)).get_hexsha()
        if (dataset_raw.archived_hexsha is not None) and (
            dataset_raw.archived_hexsha == current_hexsha
        ):
            app.logger.info("Archive for study %s up to date", study_id)
            _set_task_progress(100)
            return
        get_all_dataset_content(path_dataset_raw)
        path_archive = (
            pathlib.Path(dir_archive)
            / f"{dataset_raw.ria_alias}_{current_hexsha}.zip"
        )
        archive_dataset(
            path_dataset_raw,
            path_archive,
        )
        ssh_port = app.config["ARCHIVE_SSH_PORT"]
        ssh_key = app.config["ARCHIVE_SSH_KEY"]
        subprocess.run(
            [
                "ssh",
                "-p",
                f"{ssh_port}",
                "-i",
                f"{ssh_key}",
                app.config["ARCHIVE_BASE_URL"].split(":")[0],
                "mkdir",
                "-p",
                app.config["ARCHIVE_BASE_URL"].split(":")[1]
                + f"/{dataset_raw.ria_alias}",
            ],
            check=True,
        )
        subprocess.run(
            [
                "scp",
                "-P",
                f"{ssh_port}",
                "-i",
                f"{ssh_key}",
                str(path_archive),
                app.config["ARCHIVE_BASE_URL"] + f"/{dataset_raw.ria_alias}",
            ],
            check=True,
        )
        subprocess.run(
            [
                "ssh",
                "-p",
                f"{ssh_port}",
                "-i",
                f"{ssh_key}",
                app.config["ARCHIVE_BASE_URL"].split(":")[0],
                "find",
                app.config["ARCHIVE_BASE_URL"].split(":")[1]
                + f"/{dataset_raw.ria_alias}",
                "!",
                "-name",
                path_archive.name,
                "-type",
                "f",
                "-exec",
                "rm",
                "-f",
                "{}",
                "+",
            ],
            check=True,
        )
    dataset_raw.archived_hexsha = current_hexsha
    db.session.commit()
    _set_task_progress(100)


def update_heuristics():
    """Clone the heuristic repo if it doesn't exist, then pull from it."""
    _set_task_progress(0)
    if subprocess.run(
        ["git", "-C", app.config["HEURISTIC_REPO_PATH"], "status"],
        check=False,
    ).returncode:
        app.logger.info("No heuristic repo present. Cloning it...")
        subprocess.run(
            [
                "git",
                "clone",
                app.config["HEURISTIC_GIT_URL"],
                app.config["HEURISTIC_REPO_PATH"],
            ],
            check=True,
        )

    app.logger.info("Pulling heuristic repo.")
    try:
        subprocess.run(
            ["git", "-C", app.config["HEURISTIC_REPO_PATH"], "pull"],
            check=True,
        )
    except subprocess.CalledProcessError as err:
        app.logger.error("Pull from heuristic repo unsuccessful.")
        _set_task_error(f"Uncaught exception: {err}.")
    _set_task_progress(100)
