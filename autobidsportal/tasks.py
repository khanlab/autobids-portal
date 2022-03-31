"""Utilities to handle tasks put on the queue."""

from datetime import datetime
import tempfile
import pathlib
import re
import os
import subprocess
import shutil

from rq import get_current_job
from rq.job import Job

from autobidsportal import create_app
from autobidsportal.models import (
    db,
    Study,
    Task,
    Cfmm2tarOutput,
    Tar2bidsOutput,
)
from autobidsportal.dcm4cheutils import (
    gen_utils,
    Tar2bidsArgs,
    Cfmm2tarError,
    Cfmm2tarTimeoutError,
    Tar2bidsError,
)
from autobidsportal.dicom import get_study_records


app = create_app()
app.app_context().push()


def _set_task_progress(job_id, progress):
    job = Job.fetch(job_id)
    if job:
        job.meta["progress"] = progress
        job.save_meta()
    task = Task.query.get(job_id)
    if task.user is not None:
        task.user.add_notification(
            "task_progress", {"task_id": job_id, "progress": progress}
        )
    if progress == 100:
        task.complete = True
        task.success = True
        task.error = None
        task.end_time = datetime.utcnow()
    db.session.commit()


def _set_task_error(job_id, msg):
    task = Task.query.get(job_id)
    task.complete = True
    task.success = False
    task.error = msg[:128] if msg else ""
    task.end_time = datetime.utcnow()
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
    """
    attempts = 0
    success = False
    while not success:
        try:
            attempts += 1
            cfmm2tar_result = gen_utils().run_cfmm2tar(
                out_dir=out_dir,
                patient_name=target,
                project=study_description,
            )
            success = True
        except Cfmm2tarTimeoutError as err:
            if attempts < 5:
                app.logger.warning(
                    "cfmm2tar timeout after %i attempt(s) (target %s).",
                    attempts,
                    target,
                )
                continue
            raise err
    return cfmm2tar_result


def move_downloaded_tar(tar_file_tmp, out_dir):
    """Move a downloaded tar file to its permanent home."""
    tar_orig = pathlib.Path(tar_file_tmp)
    return pathlib.Path(
        shutil.move(str(tar_orig), str(pathlib.Path(out_dir) / tar_orig.name))
    )


def record_cfmm2tar(tar_path, uid_path, study_id):
    """Parse cfmm2tar output files and record them in the db.

    Parameters
    ----------
    tar_path : str
        Path to the downloaded tar file.
    uid_path : str
        Path to the downloaded uid file.
    study_id : int
        ID of the study associated with this cfmm2tar output.
    """
    tar_file = pathlib.PurePath(tar_path).name
    try:
        date_match = re.fullmatch(
            r"[a-zA-Z]+_\w+_(\d{8})_[\w\-]+_[\.a-zA-Z\d]+\.tar", tar_file
        ).group(1)
    except AttributeError as err:
        raise Cfmm2tarError(f"Output {tar_file} could not be parsed.") from err

    with open(uid_path, "r", encoding="utf-8") as uid_file:
        uid = uid_file.read()
    cfmm2tar = Cfmm2tarOutput(
        study_id=study_id,
        tar_file=tar_path,
        uid=uid.strip(),
        date=datetime(
            int(date_match[0:4]),
            int(date_match[4:6]),
            int(date_match[6:8]),
        ),
    )
    db.session.add(cfmm2tar)
    db.session.commit()
    pathlib.Path(uid_path).unlink()


def get_info_from_cfmm2tar(study_id):
    """Run cfmm2tar for a given study

    This will check which patients have already been downloaded, download any
    new ones, and record them in the database.

    Parameters
    ----------
    study_id : int
        ID of the study for which to run cfmm2tar.
    """
    job = get_current_job()
    _set_task_progress(job.id, 0)
    study = Study.query.get(study_id)
    study_description = f"{study.principal}^{study.project_name}"
    out_dir = str(
        pathlib.Path(app.config["CFMM2TAR_STORAGE_DIR"]) / str(study.id)
    )
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)

    existing_outputs = Cfmm2tarOutput.query.filter_by(study_id=study_id).all()

    try:
        studies_to_download = [
            record
            for record in get_study_records(
                study, description=study_description
            )
            if record["StudyInstanceUID"]
            not in {output.uid.strip() for output in existing_outputs}
        ]
        app.logger.info(
            "Running cfmm2tar for studies %s in study %i",
            [record["PatientName"] for record in studies_to_download],
            study_id,
        )
        error_msgs = []
        for target in studies_to_download:
            with tempfile.TemporaryDirectory(
                dir=app.config["CFMM2TAR_DOWNLOAD_DIR"]
            ) as download_dir:
                result = run_cfmm2tar_with_retries(
                    download_dir, target["PatientName"], study_description
                )
                app.logger.info(
                    "Successfully ran cfmm2tar for target %s.",
                    target["PatientName"],
                )
                app.logger.info("Result: %s", result)

                if result == []:
                    app.logger.error(
                        "No cfmm2tar results parsed for target %s", target
                    )
                    error_msgs.append(
                        f"No cfmm2tar results parsed for target f{target}. "
                        "Check the stderr for more information."
                    )
                for individual_result in result:
                    record_cfmm2tar(
                        str(
                            move_downloaded_tar(individual_result[0], out_dir)
                        ),
                        individual_result[1],
                        study_id,
                    )
                    app.logger.info(
                        "Moved downloaded tar file from %s to %s",
                        individual_result[0],
                        out_dir,
                    )
        if len(error_msgs) > 0:
            _set_task_error(job.id, "\n".join(error_msgs))
        else:
            _set_task_progress(job.id, 100)
    except Cfmm2tarError as err:
        app.logger.error(f"Cfmm2tar error: {err.message}")
        _set_task_error(job.id, err.message)
    finally:
        if not Task.query.get(job.id).complete:
            app.logger.error("Cfmm2tar failed for an unknown reason.")
            _set_task_error(job.id, "Unknown uncaught exception")


def get_info_from_tar2bids(study_id, tar_file_ids):
    """Run tar2bids for a specific study.

    Parameters
    ----------
    study_id : int
        ID of the study the tar files are associated with.

    tar_file_ids : list of int
        IDs of the tar files to be included in the tar2bids run.
    """
    job = get_current_job()
    _set_task_progress(job.id, 0)
    study = Study.query.get(study_id)
    cfmm2tar_outputs = [
        Cfmm2tarOutput.query.get(tar_file_id) for tar_file_id in tar_file_ids
    ]
    tar_files = [
        cfmm2tar_output.tar_file for cfmm2tar_output in cfmm2tar_outputs
    ]
    prefix = app.config["TAR2BIDS_DOWNLOAD_DIR"]
    data = str(
        pathlib.Path(prefix)
        / str(study.id)
        / (
            study.dataset_name
            if study.dataset_name not in [None, ""]
            else study.project_name
        )
    )
    if not os.path.isdir(data):
        os.makedirs(data)
    try:
        with tempfile.TemporaryDirectory(
            dir=app.config["TAR2BIDS_TEMP_DIR"]
        ) as temp_dir:
            app.logger.info("Running tar2bids for study %i", study.id)
            tar2bids_results = gen_utils().run_tar2bids(
                Tar2bidsArgs(
                    output_dir=data,
                    tar_files=tar_files,
                    heuristic=study.heuristic,
                    patient_str=study.subj_expr,
                    temp_dir=temp_dir,
                )
            )
        tar2bids = Tar2bidsOutput(
            study_id=study_id,
            cfmm2tar_outputs=cfmm2tar_outputs,
            bids_dir=tar2bids_results,
            heuristic=study.heuristic,
        )
        db.session.add(tar2bids)
        db.session.commit()
        _set_task_progress(job.id, 100)
    except Tar2bidsError as err:
        app.logger.error("tar2bids failed: %s", err)
        _set_task_error(
            job.id,
            err.__cause__.stderr if err.__cause__ is not None else str(err),
        )
    finally:
        if not Task.query.get(job.id).complete:
            app.logger.error(
                "tar2bids for study %i failed with an uncaught exception.",
                study.id,
            )
            _set_task_error(job.id, "Unknown uncaught exception.")


def update_heuristics():
    """Clone the heuristic repo if it doesn't exist, then pull from it."""
    job = get_current_job()
    if job is not None:
        _set_task_progress(job.id, 0)
    if (
        subprocess.run(
            ["git", "-C", app.config["HEURISTIC_REPO_PATH"], "status"],
            check=False,
        ).returncode
        != 0
    ):
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

    try:
        app.logger.info("Pulling heuristic repo.")
        subprocess.run(
            ["git", "-C", app.config["HEURISTIC_REPO_PATH"], "pull"],
            check=True,
        )
        if job is not None:
            _set_task_progress(job.id, 100)
    finally:
        if (job is not None) and not Task.query.get(job.id).complete:
            app.logger.error("Pull from heuristic repo unsuccessful.")
            _set_task_error(job.id, "Unknown uncaught exception.")
