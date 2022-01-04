"""Utilities to handle tasks put on the queue."""

from datetime import datetime
import tempfile
import pathlib
import re
import os
import subprocess

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
    DicomQueryAttributes,
    Tar2bidsArgs,
    Cfmm2tarError,
    Cfmm2tarTimeoutError,
    Tar2bidsError,
)


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
    task.error = msg
    task.end_time = datetime.utcnow()
    db.session.commit()


def get_info_from_cfmm2tar(study_id):
    """Get all info related to a specific cfmm2tar run."""
    job = get_current_job()
    _set_task_progress(job.id, 0)
    study = Study.query.get(study_id)
    study_description = f"{study.principal}^{study.project_name}"
    patient_str = study.patient_str
    out_dir = str(
        pathlib.Path(app.config["CFMM2TAR_DOWNLOAD_DIR"])
        / str(study.id)
        / datetime.utcnow().strftime("%Y%m%d%H%M")
    )
    try:
        for result in get_new_cfmm2tar_results(
            study_description=study_description,
            patient_str=patient_str,
            out_dir=out_dir,
            study_id=study_id,
        ):
            tar_file = pathlib.PurePath(result[0]).name
            try:
                date_match = re.fullmatch(
                    r"[a-zA-Z]+_\w+_(\d{8})_\w+_[\.a-zA-Z\d]+\.tar", tar_file
                ).group(1)
            except AttributeError as err:
                raise Cfmm2tarError(
                    f"Output {tar_file} could not be parsed."
                ) from err

            with open(result[1], "r", encoding="utf-8") as uid_file:
                uid = uid_file.read()
            cfmm2tar = Cfmm2tarOutput(
                study_id=study_id,
                tar_file=result[0],
                uid=uid,
                date=datetime(
                    int(date_match[0:4]),
                    int(date_match[4:6]),
                    int(date_match[6:8]),
                ),
            )
            db.session.add(cfmm2tar)
            pathlib.Path(result[1]).unlink()
        db.session.commit()
        _set_task_progress(job.id, 100)
    except Cfmm2tarError as err:
        _set_task_error(job.id, err.message)
    finally:
        if not Task.query.get(job.id).complete:
            _set_task_error(job.id, "Unknown uncaught exception")


def get_new_cfmm2tar_results(
    study_description, patient_str, out_dir, study_id
):
    """Run cfmm2tar and parse new results."""
    existing_outputs = Cfmm2tarOutput.query.filter_by(study_id=study_id).all()

    utils = gen_utils()
    dicom_studies = utils.query_single_study(
        ["PatientName"],
        DicomQueryAttributes(
            study_description=study_description,
            patient_name=patient_str,
        ),
    )
    studies_to_download = [
        study[0]["tag_value"]
        for study in dicom_studies
        if not any(
            study[0]["tag_value"] in pathlib.Path(output.tar_file).name
            for output in existing_outputs
        )
    ]
    all_results = []
    for target in studies_to_download:
        attempts = 0
        success = False
        while not success:
            try:
                attempts += 1
                cfmm2tar_result = gen_utils().run_cfmm2tar(
                    out_dir=out_dir, patient_name=target, project=study_description
                )
                success = True
            except Cfmm2tarTimeoutError as err:
                if attempts < 5:
                    continue
                raise err

        if cfmm2tar_result == []:
            err = "Invalid Principal or Project Name"
            _set_task_error(get_current_job().id, err)
            raise Cfmm2tarError(err)
        all_results.extend(cfmm2tar_result)

    return all_results


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
        _set_task_error(job.id, err.__cause__.stderr)
    finally:
        if not Task.query.get(job.id).complete:
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
        subprocess.run(
            ["git", "-C", app.config["HEURISTIC_REPO_PATH"], "pull"],
            check=True,
        )
        if job is not None:
            _set_task_progress(job.id, 100)
    finally:
        if (job is not None) and not Task.query.get(job.id).complete:
            _set_task_error(job.id, "Unknown uncaught exception.")
