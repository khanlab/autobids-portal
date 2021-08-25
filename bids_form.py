"""Flask entry point with extra CLI commands."""

from autobidsportal import app, db
from autobidsportal.dcm4cheutils import gen_utils, Dcm4cheError
from autobidsportal.models import (
    User,
    Answer,
    Submitter,
    Principal,
    Notification,
    Task,
    Cfmm2tar,
    Tar2bids,
    Choice,
)


@app.shell_context_processor
def make_shell_context():
    """Add useful variables into the shell context."""
    return {
        "db": db,
        "User": User,
        "Answer": Answer,
        "Submitter": Submitter,
        "Principal": Principal,
        "Notification": Notification,
        "Task": Task,
        "Cfmm2tar": Cfmm2tar,
        "Tar2bids": Tar2bids,
        "Choice": Choice,
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
