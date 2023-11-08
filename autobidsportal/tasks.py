"""Utilities to handle tasks put on the queue."""
from __future__ import annotations

import pathlib
import re
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from os import PathLike, unlink
from os.path import islink
from shutil import copy2, rmtree
from zipfile import ZipFile

from bids import BIDSLayout
from datalad.support.gitrepo import GitRepo
from rq.job import get_current_job

from autobidsportal.app import create_app
from autobidsportal.apptainer import apptainer_exec
from autobidsportal.bids import merge_datasets
from autobidsportal.datalad import (
    RiaDataset,
    archive_dataset,
    delete_tar_file,
    ensure_dataset_exists,
    finalize_dataset_changes,
    get_all_dataset_content,
    get_tar_file_from_dataset,
)
from autobidsportal.dateutils import TIME_ZONE
from autobidsportal.dcm4cheutils import (
    Cfmm2tarArgs,
    Cfmm2tarError,
    Cfmm2tarTimeoutError,
    Tar2bidsArgs,
    Tar2bidsError,
    gen_utils,
)
from autobidsportal.dicom import get_study_records
from autobidsportal.email import send_email
from autobidsportal.filesystem import gen_dir_dict, render_dir_dict
from autobidsportal.models import (
    Cfmm2tarOutput,
    DataladDataset,
    DatasetArchive,
    DatasetType,
    Study,
    Tar2bidsOutput,
    Task,
    User,
    db,
)
from autobidsportal.ssh import copy_file, make_remote_dir

app = create_app()
app.app_context().push()

COMPLETION_PROGRESS = 100
MAX_CFMM2TAR_ATTEMPTS = 5


def _set_task_progress(progress: int):
    """Set progress of current task.

    Parameters
    ----------
    progress
        Integer value (between 0 and 100) to set progress of current task to

    """
    # If no current job in progress
    if not (job := get_current_job()):
        return

    job.meta["progress"] = progress
    job.save_meta()
    task = Task.query.get(job.id)
    if task.user is not None:
        task.user.add_notification(
            "task_progress",
            {"task_id": job.id, "progress": progress},
        )

    # If task completed
    if progress == COMPLETION_PROGRESS:
        task.complete = True
        task.success = True
        task.error = None
        task.end_time = datetime.now(tz=TIME_ZONE)

    db.session.commit()  # pyright: ignore


def _set_task_error(msg: str):
    """Set error message of a given task.

    Parameters
    ----------
    msg
        Error message to provide / log
    """
    # If no jobs in progress
    if not (job := get_current_job()):
        return

    task = Task.query.get(job.id)
    task.complete = True
    task.success = False
    task.error = msg[:128] if msg else ""
    task.end_time = datetime.now(tz=TIME_ZONE)

    db.session.commit()  # pyright: ignore


def _append_task_log(log: str):
    """Append to task log.

    Parameters
    ----------
    log
        Message to append to log of task
    """
    # If no jobs in progress
    if not (job := get_current_job()):
        return

    task = Task.query.get(job.id)
    task.log = "".join([task.log if task.log is not None else "", log])

    db.session.commit()  # pyright: ignore


def run_cfmm2tar_with_retries(
    out_dir: PathLike[str] | str,
    study_instance_uid: str,
) -> tuple[list[list[str]], str]:
    """Run cfmm2tar, retrying multiple times if it times out.

    Parameters
    ----------
    out_dir
        Directory to which to download tar files.

    study_instance_uid
        StudyInstanceUid to download

    Returns
    -------
    tuple[list[list[str]], str]
        List of tar files associated with study id processed and log

    Raises
    ------
    Cfmm2tarTimeoutError
        If cfmm2tar times out too many times.
    """
    cfmm2tar_result, log = [], ""
    # Attempt 5 times before timing out
    for attempt in range(1, 6):
        try:
            cfmm2tar_result, log = gen_utils().run_cfmm2tar(
                Cfmm2tarArgs(
                    out_dir=out_dir,
                    study_instance_uid=study_instance_uid,
                ),
            )
        except Cfmm2tarTimeoutError:
            if attempt < MAX_CFMM2TAR_ATTEMPTS:
                app.logger.warning(
                    "cfmm2tar timeout after %i attempt(s) (target %s).",
                    attempt,
                    study_instance_uid,
                )
                continue
            raise
        break

    return cfmm2tar_result, log


def record_cfmm2tar(
    tar_file: str,
    uid: str,
    study_id: int,
    attached_tar_file: str | None = None,
):
    """Parse cfmm2tar output files and record them in the db.

    Parameters
    ----------
    tar_file
        Name of the downloaded tar file.

    uid
        StudyInstanceUID of the tar file..

    study_id
        ID of the study associated with this cfmm2tar output.

    attached_tar_file
        Name of the attached tar file.

    Raises
    ------
    Cfmm2tarError
        If cfmm2tar fails.
    """
    date_match = re.fullmatch(
        r"[a-zA-Z]+_[\w\-]+_(\d{8})_[\w\-]+_[\.a-zA-Z\d]+\.tar",
        tar_file,
    )
    if not date_match:
        msg = f"Output {tar_file} could not be parsed."
        raise Cfmm2tarError(msg)

    date_match = date_match.group(1)
    cfmm2tar = Cfmm2tarOutput(
        study_id=study_id,
        tar_file=tar_file,
        uid=uid.strip(),
        date=datetime(
            int(date_match[0:4]),
            int(date_match[4:6]),
            int(date_match[6:8]),
            tzinfo=TIME_ZONE,
        ),
        attached_tar_file=attached_tar_file,
    )
    db.session.add(cfmm2tar)  # pyright: ignore
    db.session.commit()  # pyright: ignore


def process_uid_file(uid_path: PathLike[str] | str) -> str:
    """Read a UID file, delete it, and return the UID.

    Parameters
    ----------
    uid_path
        Path to UID file to be read

    Returns
    -------
    str
        Associated file UID
    """
    path = pathlib.Path(uid_path)
    with path.open(encoding="utf-8") as uid_file:
        uid = uid_file.read()
    path.unlink()

    return uid


def find_studies_to_download(
    study: Study,
    study_description: str,
    explicit_scans: list[dict[str, str | list[dict[str, str]]]] | None = None,
) -> list[dict[str, str | list[dict[str, str]]]]:
    """Find the studies to download, or override them with explicit scans.

    Parameters
    ----------
    study
        Study to return scan / record information from

    study_description
        Description to search by

    explicit_scans
        Scans, explicitly defined to override with

    Returns
    -------
    list[dict[str, str | list[dict[str, str]]]]
        List of studies if explicit scans are provided or list of study
        records matching study_description
    """
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


def check_tar_files(
    study_id: int,
    explicit_scans: list[dict[str, str | list[dict[str, str]]]] | None = None,
    user_id: int | None = None,
):
    """Launch cfmm2tar if there are any new tar files.

    Parameters
    ----------
    study_id
        Associated study id to check for tar files from

    explicit_scans
        Scans to explicitly defined to download

    user_id
        ID of the user to associate task with
    """
    study = Study.query.get(study_id)
    user = User.query.get(user_id) if user_id is not None else None
    studies_to_download = find_studies_to_download(
        study,
        f"{study.principal}^{study.project_name}",
        explicit_scans,
    )
    if not studies_to_download:
        return

    new_studies = ", ".join(
        [
            new_study["PatientName"]
            for new_study in studies_to_download  # pyright: ignore
        ],
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


def ensure_complete(error_log: str) -> Callable:
    """Ensure a cfmm2tar job is complete (decorator function).

    Example:
    @ensure_complete("Task did not complete successfully")
    def some_task(*args):
        # Task implemenetation

    Parameters
    ----------
    error_log
        Error message to log if task does not complete

    Returns
    -------
    Callable
        Wrapped task function to ensure completion and logs errors
    """

    def decorate(task: Callable) -> Callable:
        def wrapped_task(*args):
            try:
                task(*args)
            finally:
                if (job := get_current_job()) and (
                    not Task.query.get(job.id).complete
                ):
                    app.logger.error(error_log)
                    _set_task_error("Unknown uncaught exception")

        return wrapped_task

    return decorate


def handle_cfmm2tar(
    download_dir: PathLike[str] | str,
    study: Study,
    target: Mapping[str, str],
    dataset: DataladDataset,
):
    """Run cfmm2tar on one target."""
    _, log = run_cfmm2tar_with_retries(
        str(download_dir),
        target["StudyInstanceUID"],
    )

    _append_task_log(log)
    app.logger.info(
        "Successfully ran cfmm2tar for target %s.",
        target["PatientName"],
    )
    app.logger.info("Log: %s", log)

    if not (created_files := list(pathlib.Path(download_dir).iterdir())):
        msg = (
            f"No cfmm2tar results parsed for target {target}. "
            "Check the stderr for more information."
        )
        raise Cfmm2tarError(
            msg,
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
        msg = "No tar file produced."
        raise Cfmm2tarError(msg)

    if not uid_file:
        msg = "No uid file produced."
        raise Cfmm2tarError(msg)

    created_files = list(set(created_files) - {uid_file})
    uid = process_uid_file(uid_file)

    with RiaDataset(
        download_dir,
        dataset.ria_alias,
        ria_url=dataset.custom_ria_url,
    ) as path_dataset:
        for file_ in created_files:
            app.logger.info("file_: %s", file_)
            app.logger.info(
                "tmp contents: %s",
                list(pathlib.Path(file_.parent).iterdir()),
            )
            app.logger.info("path_dataset: %s", path_dataset)

            # If an existing git annex symlink exists, copying will fail
            if islink(path_dataset / file_.name):
                app.logger.info("Unlinking existing tar file.")
                unlink(path_dataset / file_.name)
            copy2(file_, path_dataset / file_.name)
        finalize_dataset_changes(str(path_dataset), "Add new tar file.")

    record_cfmm2tar(
        tar,
        uid,
        study.id,
        attached_tar_file=attached_tar,
    )


@ensure_complete("Cfmm2tar failed for an unknown reason.")
def run_cfmm2tar(
    study_id: int,
    studies_to_download: Sequence[Mapping[str, str]],
):
    """Run cfmm2tar for a given study.

    This will check which patients have already been downloaded, download any
    new ones, and record them in the database.

    Parameters
    ----------
    study_id
        ID of the study for which to run cfmm2tar.

    studies_to_download
        List of scans to get with cfmm2tar, where each scan is represented by
        a dict with keys "StudyInstanceUID" and "PatientName".
    """
    _set_task_progress(0)
    study = Study.query.get(study_id)
    app.logger.info(
        "Running cfmm2tar for patients %s in study %i",
        [
            record["PatientName"]
            for record in studies_to_download  # pyright: ignore
        ],
        study.id,
    )

    dataset = ensure_dataset_exists(study.id, DatasetType.SOURCE_DATA)
    error_msgs = []
    for target in studies_to_download:  # pyright: ignore
        with tempfile.TemporaryDirectory(
            dir=app.config["CFMM2TAR_DOWNLOAD_DIR"],
        ) as download_dir:
            try:
                handle_cfmm2tar(download_dir, study, target, dataset)
            except Cfmm2tarError as err:
                app.logger.exception("cfmm2tar failed")
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
                    ),
                ]
                + [
                    f"PatientName: {target['PatientName']}"
                    for target in studies_to_download
                ]
                + ["\nErrors:\n"]
                + error_msgs,
            ),
            additional_recipients=[
                admin.email for admin in User.query.filter_by(admin=True).all()
            ]
            if error_msgs
            else None,
        )

    if len(error_msgs) > 0:
        _set_task_error("\n".join(error_msgs))
    else:
        _set_task_progress(100)


def find_unprocessed_tar_files(study_id: int):
    """Check for tar files that aren't in the dataset and add them.

    Parameters
    ----------
    study_id
        Id of study to query
    """
    study = Study.query.get(study_id)
    dataset = DataladDataset.query.filter_by(
        study_id=study.id,
        dataset_type=DatasetType.RAW_DATA,
    ).one_or_none()
    existing_tar_file_ids = (
        set()
        if dataset is None
        else {out.id for out in dataset.cfmm2tar_outputs}
    )
    new_tar_file_ids = {
        tar_file.id for tar_file in study.cfmm2tar_outputs
    } - existing_tar_file_ids

    # If no new unprocessed tars
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
def run_tar2bids(study_id: int, tar_file_ids: Sequence[int]):
    """Run tar2bids for a specific study.

    Parameters
    ----------
    study_id
        ID of the study the tar files are associated with.

    tar_file_ids
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
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as bids_dir, tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_TEMP_DIR"],
    ) as temp_dir, tempfile.TemporaryDirectory(
        dir=app.config["CFMM2TAR_DOWNLOAD_DIR"],
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
                    tar_out.tar_file,
                    path_dataset_tar,
                )
                try:
                    _append_task_log(
                        gen_utils().run_tar2bids(
                            Tar2bidsArgs(
                                output_dir=str(
                                    pathlib.Path(bids_dir) / "incoming",
                                ),
                                tar_files=[tar_path],
                                heuristic=study.heuristic,
                                patient_str=study.subj_expr,
                                temp_dir=temp_dir,
                                bidsignore=None
                                if study.custom_bidsignore is None
                                else bidsignore.name,
                                deface=study.deface,
                            ),
                        ),
                    )
                except Tar2bidsError as err:
                    app.logger.exception("tar2bids failed")
                    _set_task_error(
                        err.__cause__.stderr  # pyright: ignore
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
                                    frozenset({".git", ".datalad"}),
                                ),
                            ),
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
                                    "completed. This email is sent if any of "
                                    "them fail."
                                ),
                                "Error:",
                                str(err),
                            ],
                        ),
                        additional_recipients=[
                            admin.email
                            for admin in User.query.filter_by(admin=True).all()
                        ],
                    )
                    raise

            with RiaDataset(
                pathlib.Path(bids_dir) / "existing",
                dataset_bids.ria_alias,
                ria_url=dataset_bids.custom_ria_url,
            ) as path_dataset_study:
                merge_datasets(
                    pathlib.Path(bids_dir) / "incoming",
                    path_dataset_study,
                )
                finalize_dataset_changes(
                    path_dataset_study,
                    f"Ran tar2bids on tar file {tar_path}",
                )
                study.dataset_content = gen_dir_dict(
                    path_dataset_study,
                    frozenset({".git", ".datalad"}),
                )
                tar_out.datalad_dataset = dataset_bids
                db.session.commit()  # pyright: ignore

        db.session.add(  # pyright: ignore
            Tar2bidsOutput(
                study_id=study_id,
                cfmm2tar_outputs=cfmm2tar_outputs,
                bids_dir=None,
                heuristic=study.heuristic,
            ),
        )
        db.session.commit()  # pyright: ignore
    _set_task_progress(100)
    if len(tar_file_ids) > 0:
        send_email(
            "Successful tar2bids run.",
            "\n".join(
                ["Tar2bids successfully run for tar files:"]
                + [output.tar_file for output in cfmm2tar_outputs],
            ),
            additional_recipients={study.submitter_email}
            | {user.email for user in study.users_authorized},
        )


def archive_entire_dataset(
    path_dataset_raw: PathLike[str] | str,
    path_archive: PathLike[str] | str,
    dataset_id: int,
    repo: GitRepo,
) -> DatasetArchive:
    """Make a new archive of an entire dataset.

    Parameters
    ----------
    path_dataset_raw
        Path of raw datalad dataset

    path_archive
        Path where archive should be saved

    dataset_id
        Associated dataset id

    repo
        Object representation of github repository

    Returns
    -------
    DatasetArchive
        Archive containing dataset content
    """
    get_all_dataset_content(path_dataset_raw)
    archive_dataset(
        path_dataset_raw,
        path_archive,
    )

    return DatasetArchive(
        dataset_id=dataset_id,
        dataset_hexsha=repo.get_hexsha(),
        commit_datetime=datetime.fromtimestamp(
            repo.get_commit_date(date="committed"),  # pyright: ignore
            tz=TIME_ZONE,
        ),
    )


def archive_partial_dataset(
    repo: GitRepo,
    latest_archive: DataladDataset,
    path_archive: PathLike[str] | str,
    path_dataset_raw: PathLike[str] | str,
    dataset_id: int,
) -> DatasetArchive:
    """Make an archive of changed files since the latest archive.

    Parameters
    ----------
    repo
        Object representation of github repository

    latest_archive
        Datadlad dataset of latest archive

    path_archive
        Path where archive should be saved

    path_dataset_raw
        Path of raw datalad dataset

    dataset_id
        Associated dataset id

    Returns
    -------
    DatasetArchive
        Archive containing dataset content
    """
    updated_files = [
        path
        for path, entry in GitRepo(str(path_dataset_raw))
        .diff(latest_archive.dataset_hexsha, repo.get_hexsha())
        .items()
        if (entry["state"] in {"added", "modified"})
        and (entry["type"] in {"file", "symlink"})
    ]
    with ZipFile(path_archive, mode="x") as zip_file:
        for file_ in updated_files:
            get_tar_file_from_dataset(
                (archive_path := file_.relative_to(path_dataset_raw)),
                path_dataset_raw,
            )
            zip_file.write(file_, archive_path)

    return DatasetArchive(
        dataset_id=dataset_id,
        parent_id=latest_archive.id,
        dataset_hexsha=repo.get_hexsha(),
        commit_datetime=datetime.fromtimestamp(
            repo.get_commit_date(date="committed"),  # pyright: ignore
            tz=TIME_ZONE,
        ),
    )


@ensure_complete("raw dataset archival failed with an uncaught exception.")
def archive_raw_data(study_id: int):
    """Clone a study dataset and archive it if necessary.

    Parameters
    ----------
    study_id
        Associated study id to clone and archive
    """
    _set_task_progress(0)
    study = Study.query.get(study_id)

    # If study cannot be found or no content
    if (study.custom_ria_url is not None) or (study.dataset_content is None):
        _set_task_progress(100)
        return

    dataset_raw = ensure_dataset_exists(study_id, DatasetType.RAW_DATA)
    with tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as dir_raw_data, RiaDataset(
        dir_raw_data,
        dataset_raw.ria_alias,
        ria_url=dataset_raw.custom_ria_url,
    ) as path_dataset_raw, tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],  # pyright: ignore
    ) as dir_archive:
        latest_archive = max(
            dataset_raw.dataset_archives,  # pyright: ignore
            default=None,
            key=lambda archive: archive.commit_datetime,  # pyright: ignore
        )
        repo = GitRepo(str(path_dataset_raw))

        # If archive is up-to-date
        if (latest_archive) and (
            latest_archive.dataset_hexsha == repo.get_hexsha()
        ):
            app.logger.info("Archive for study %s up to date", study_id)
            _set_task_progress(100)
            return

        # Otherwise, update archive
        commit_datetime = datetime.fromtimestamp(
            repo.get_commit_date(date="committed"),  # pyright: ignore
            tz=TIME_ZONE,
        )
        path_archive = pathlib.Path(dir_archive) / (
            f"{dataset_raw.ria_alias}_"
            f"{commit_datetime.isoformat().replace(':', '.')}_"
            f"{repo.get_hexsha()[:6]}.zip"  # pyright: ignore
        )
        archive = (
            archive_entire_dataset(
                path_dataset_raw,
                path_archive,
                dataset_raw.id,
                repo,
            )
            if not latest_archive
            else archive_partial_dataset(
                repo,
                latest_archive,
                path_archive,
                path_dataset_raw,
                dataset_raw.id,
            )
        )
        make_remote_dir(
            app.config["ARCHIVE_BASE_URL"].split(":")[0],
            app.config["ARCHIVE_BASE_URL"].split(":")[1]
            + f"/{dataset_raw.ria_alias}",
        )
        copy_file(
            app.config["ARCHIVE_BASE_URL"],
            str(path_archive),
            f"/{dataset_raw.ria_alias}",
        )

    # Update database
    db.session.add(archive)  # pyright: ignore
    db.session.commit()  # pyright: ignore
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
        app.logger.exception("Pull from heuristic repo unsuccessful.")
        _set_task_error(f"Uncaught exception: {err}.")
    _set_task_progress(100)


def find_uncorrected_images(study_id: int):
    """Check for NIfTI images that haven't had gradcorrect applied.

    Parameters
    ----------
    study_id
        Study ID to search for uncorrected images
    """
    # anat,func,fmap,dwi,asl
    study = Study.query.get(study_id)

    # If not 7T scanner, skip (no gradient coeffient file)
    if study.scanner != "type2":
        return

    # If no raw datasets
    raw_dataset = DataladDataset.query.filter_by(
        study_id=study.id,
        dataset_type=DatasetType.RAW_DATA,
    ).one_or_none()
    if not raw_dataset:
        return

    # If derived dataset does not exist, launch gradcorrect ask
    derived_dataset = DataladDataset.query.filter_by(
        study_id=study.id,
        dataset_type=DatasetType.DERIVED_DATA,
    ).one_or_none()
    if not derived_dataset:
        Task.launch_task(
            "gradcorrect_study",
            "gradcorrect for new BIDS dataset",
            study_id,
            study_id=study_id,
            timeout=app.config["GRADCORRECT_TIMEOUT"],
        )
        return

    # Possible datatypes that gradcorrect can be performed on
    correctable_args = {
        "extension": "nii.gz",
        "datatype": ["anat", "func", "fmap", "dwi", "asl"],
    }

    # Find already corrected files
    with tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as derivatives_dir, RiaDataset(
        derivatives_dir,
        derived_dataset.ria_alias,
        ria_url=derived_dataset.custom_ria_url,
    ) as path_dataset_derived:
        gradcorrect_path = path_dataset_derived / "gradcorrect"
        gradcorrect_path.mkdir(exist_ok=True)
        derived_layout = BIDSLayout(
            gradcorrect_path,
            validate=False,
        )
        corrected_files = {
            str(
                pathlib.Path(img.path).relative_to(
                    path_dataset_derived / "gradcorrect",
                ),
            )
            for img in derived_layout.get(**correctable_args)
        }
    # Find subjects that correction still needs to be performed on
    with tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as bids_dir, RiaDataset(
        bids_dir,
        raw_dataset.ria_alias,
        ria_url=raw_dataset.custom_ria_url,
    ) as path_dataset_raw:
        raw_layout = BIDSLayout(path_dataset_raw, validate=False)
        subjects = {
            img.get_entities()["subject"]
            for img in raw_layout.get(**correctable_args)
            if str(pathlib.Path(img.path).relative_to(path_dataset_raw))
            not in corrected_files
        }

    if not subjects:
        return

    # Launch gradcorrect task for subjects with uncorrected data
    Task.launch_task(
        "gradcorrect_study",
        f"gradcorrect run for subjects {subjects}",
        study_id,
        study_id=study_id,
        timeout=app.config["GRADCORRECT_TIMEOUT"],
        subject_labels=subjects,
    )


def run_gradcorrect(
    path_dataset_raw: PathLike[str] | str,
    path_out: PathLike[str] | str,
    subject_ids: Sequence[str] | None,
):
    """Run gradcorrect on a BIDS dataset, optionally on a subset of subjects.

    Parameters
    ----------
    path_dataset_raw
        Input bids directory to perform gradcorrect on

    path_out
        Output directory to save results to

    subject_ids
        List of subject ids to process (optional)
    """
    participant_label = (
        ["--participant_label", *subject_ids] if subject_ids else []
    )
    apptainer_exec(
        [
            "/gradcorrect/run.sh",
            str(path_dataset_raw),
            str(path_out),
            "participant",
            "--grad_coeff_file",
            app.config["GRADCORRECT_COEFF_FILE"],
            *participant_label,
        ],
        app.config["GRADCORRECT_PATH"],
        app.config["GRADCORRECT_BINDS"].split(","),
    )


@ensure_complete("gradcorrect failed with an uncaught exception.")
def gradcorrect_study(
    study_id: int,
    subject_labels: Sequence[str] | None = None,
) -> None:
    """Run gradcorrect on a set of subjects in a study.

    Parameters
    ----------
    study_id
        Associated study id to perform gradcorrect for

    subject_labels
        List of subject ids to run gradcorrect on (Optional)
    """
    _set_task_progress(0)
    if (not (study := Study.query.get(study_id))) or (
        study.custom_ria_url is not None
    ):
        _set_task_progress(100)
        return
    dataset_bids = ensure_dataset_exists(study_id, DatasetType.RAW_DATA)
    dataset_derivatives = ensure_dataset_exists(
        study_id,
        DatasetType.DERIVED_DATA,
    )
    with tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as bids_dir, tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as derivatives_dir, RiaDataset(
        derivatives_dir,
        dataset_derivatives.ria_alias,
        ria_url=dataset_derivatives.custom_ria_url,
    ) as path_dataset_derivatives:
        with RiaDataset(
            bids_dir,
            dataset_bids.ria_alias,
            ria_url=dataset_bids.custom_ria_url,
        ) as path_dataset_bids:
            # Grab provided subjects' data, otherwise grab all
            if subject_labels:
                for subject_label in subject_labels:
                    get_tar_file_from_dataset(
                        f"sub-{subject_label}",
                        path_dataset_bids,
                    )
            else:
                get_all_dataset_content(path_dataset_bids)

            run_gradcorrect(
                path_dataset_bids,
                path_dataset_derivatives / "gradcorrect",
                subject_labels,
            )
        # Remove intermediate data
        rmtree(
            path_dataset_derivatives
            / "gradcorrect"
            / "sourcedata"
            / "scratch",
        )

        sub_string = (
            ",".join(subject_labels) if subject_labels else "all subjects"
        )
        finalize_dataset_changes(
            str(path_dataset_derivatives),
            f"Run gradcorrect on subjects {sub_string}",
        )
    _set_task_progress(100)


@ensure_complete(
    "derivative dataset archival failed with an uncaught exception.",
)
def archive_derivative_data(study_id: int):
    """Clone a study dataset and archive it if necessary.

    Parameters
    ----------
    study_id
        Associated id of study to clone and archive
    """
    _set_task_progress(0)
    study = Study.query.get(study_id)

    # If RIA already exists
    if study.custom_ria_url is not None:
        _set_task_progress(100)
        return

    dataset_derived = ensure_dataset_exists(study_id, DatasetType.DERIVED_DATA)
    with tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as dir_derived_data, RiaDataset(
        dir_derived_data,
        dataset_derived.ria_alias,
        ria_url=dataset_derived.custom_ria_url,
    ) as path_dataset_derived, tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as dir_archive:
        latest_archive = max(
            dataset_derived.dataset_archives,  # pyright: ignore
            default=None,
            key=lambda archive: archive.commit_datetime,  # pyright: ignore
        )
        repo = GitRepo(str(path_dataset_derived))
        # If archive is already up-to-date
        if (latest_archive) and (
            latest_archive.dataset_hexsha == repo.get_hexsha()
        ):
            app.logger.info("Archive for study %s up to date", study_id)
            _set_task_progress(100)
            return

        # If no archive exists, archive entire dataset, otherwise partial
        commit_datetime = datetime.fromtimestamp(
            repo.get_commit_date(date="committed"),  # pyright: ignore
            tz=TIME_ZONE,
        )
        path_archive = pathlib.Path(dir_archive) / (
            f"{dataset_derived.ria_alias}_"
            f"{commit_datetime.isoformat().replace(':', '.')}_"
            f"{repo.get_hexsha()[:6]}.zip"  # pyright: ignore
        )
        archive = (
            archive_entire_dataset(
                path_dataset_derived,
                path_archive,
                dataset_derived.id,
                repo,
            )
            if not latest_archive
            else archive_partial_dataset(
                repo,
                latest_archive,
                path_archive,
                path_dataset_derived,
                dataset_derived.id,
            )
        )

        # Copy archive to RIA
        make_remote_dir(
            app.config["ARCHIVE_BASE_URL"].split(":")[0],
            app.config["ARCHIVE_BASE_URL"].split(":")[1]
            + f"/{dataset_derived.ria_alias}",
        )
        copy_file(
            app.config["ARCHIVE_BASE_URL"],
            str(path_archive),
            f"/{dataset_derived.ria_alias}",
        )

    # Update database
    db.session.add(archive)  # pyright: ignore
    db.session.commit()  # pyright: ignore
    _set_task_progress(100)
