"""Flask entry point with extra CLI commands."""

from autobidsportal.app import create_app
from autobidsportal.dcm4cheutils import gen_utils, Dcm4cheError
from autobidsportal.models import (
    db,
    User,
    Study,
    Principal,
    Notification,
    Task,
    Cfmm2tarOutput,
    Tar2bidsOutput,
    ExplicitPatient,
)
from autobidsportal.tasks import update_heuristics


app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Add useful variables into the shell context."""
    return {
        "db": db,
        "User": User,
        "Study": Study,
        "Principal": Principal,
        "Notification": Notification,
        "Task": Task,
        "Cfmm2tarOutput": Cfmm2tarOutput,
        "Tar2bidsOutput": Tar2bidsOutput,
        "ExplicitPatient": ExplicitPatient,
    }


@app.cli.command()
def check_pis():
    """Add a list of pi names from dicom server to the Principal table."""
    try:
        principal_names = gen_utils().get_all_pi_names()
        db.session.query(Principal).delete()
        for principal_name in principal_names:
            principal = Principal(principal_name=principal_name)
            db.session.add(principal)
            db.session.commit()
    except Dcm4cheError as err:
        print(err)
    return "Success"


@app.cli.command()
def run_update_heuristics():
    """Clone the heuristic repo if it doesn't exist, then pull from it.

    The point of this wrapper function is to expose the task to the CLI.
    """

    update_heuristics()


@app.cli.command()
def run_all_cfmm2tar():
    """Run cfmm2tar on all active studies.

    This won't run cfmm2tar on studies that currently have cfmm2tar runs in
    progress.
    """
    for study in Study.query.all():
        if (
            len(
                Task.query.filter_by(
                    study_id=study.id,
                    name="run_cfmm2tar",
                    complete=False,
                ).all()
            )
            > 0
        ) or (not study.active):
            print(f"Skipping study {study.id}. Active: {study.active}")
            continue
        app.task_queue.enqueue(
            "autobidsportal.tasks.check_tar_files", study.id
        )


@app.cli.command()
def run_all_tar2bids():
    """Run tar2bids on all active studies."""
    for study in Study.query.all():
        if (
            len(
                Task.query.filter_by(
                    study_id=study.id,
                    name="run_tar2bids",
                    complete=False,
                ).all()
            )
            > 0
        ) or not study.active:
            print(f"Skipping study {study.id}. Active: {study.active}")
            continue
        app.task_queue.enqueue(
            "autobidsportal.tasks.find_unprocessed_tar_files", study.id
        )


@app.cli.command()
def run_all_archive():
    """Archive all active studies' raw datasets.

    This won't archive studies that currently have tar2bids runs in
    progress.
    """
    for study in Study.query.all():
        print(f"study: {study.id}")
        if (
            len(
                Task.query.filter_by(
                    study_id=study.id,
                    name="get_info_from_tar2bids",
                    complete=False,
                ).all()
            )
            > 0
        ) or (not study.active):
            continue
        Task.launch_task(
            "archive_raw_data",
            "automatic archive task",
            study.id,
            study_id=study.id,
        )
