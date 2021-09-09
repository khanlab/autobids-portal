"""Utilities to handle tasks put on the queue."""

from datetime import datetime
import pathlib
import re
import os

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
    Cfmm2tarError,
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
    study_info = f"{study.principal}^{study.project_name}"
    out_dir = "%s/%s/%s" % (
        app.config["CFMM2TAR_DOWNLOAD_DIR"],
        study.id,
        datetime.utcnow().strftime("%Y%m%d%H%M"),
    )
    try:
        for result in get_new_cfmm2tar_results(
            study_info=study_info, out_dir=out_dir, study_id=study_id
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
                study_id,
                tar_file=result[0],
                uid=uid,
                date=datetime(
                    int(date_match[0:4]),
                    int(date_match[4:6]),
                    int(date_match[6:8]),
                ),
            )
            db.session.add(cfmm2tar)
        db.session.commit()
        _set_task_progress(job.id, 100)
    except Cfmm2tarError as err:
        _set_task_error(job.id, err.__cause__.stderr)
    finally:
        if not Task.query.get(job.id).complete:
            _set_task_error(job.id, "Unknown uncaught exception")


def get_new_cfmm2tar_results(study_info, out_dir, study_id):
    """Run cfmm2tar and parse new results."""
    cfmm2tar_result = gen_utils().run_cfmm2tar(
        out_dir=out_dir, project=study_info
    )
    if cfmm2tar_result == []:
        err = "Invalid Principal or Project Name"
        _set_task_error(get_current_job().id, err)
        return []

    tar_files_existing = [
        pathlib.PurePath(output.tar_file).name
        for output in Cfmm2tarOutput.query.filter_by(study_id=study_id).all()
    ]

    return [
        result
        for result in cfmm2tar_result
        if pathlib.PurePath(result[0]).name not in tar_files_existing
    ]


def get_info_from_tar2bids(study_id, tar_file_id):
    """Run tar2bids for a specific study."""
    job = get_current_job()
    _set_task_progress(job.id, 0)
    study = Study.query.get(study_id)
    study_info = f"{study.principal}^{study.project_name}"
    tar_file = Cfmm2tarOutput.query.get(tar_file_id).tar_file
    prefix = app.config["TAR2BIDS_DOWNLOAD_DIR"]
    data = "%s/%s/%s" % (prefix, study_info, study.dataset_name)
    if not os.path.isdir(data):
        os.makedirs(data)
    try:
        tar2bids_results = gen_utils().run_tar2bids(
            output_dir=data,
            tar_files=[tar_file],
            heuristic=study.heuristic,
            patient_str=study.subj_expr,
        )
        tar2bids = Tar2bidsOutput(
            study_id=study_id,
            cfmm2tar_output_id=tar_file_id,
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
