"""Flask entry point with extra CLI commands."""

from autobidsportal import create_app
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
)


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
