from autobidsportal import app, db
from autobidsportal.dcm4cheutils import Dcm4cheUtils, gen_utils, Dcm4cheError
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
from datetime import datetime
import time


@app.shell_context_processor
def make_shell_context():
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
    """Run scheduled job that gets the list of pi names from dicom and appends them to the Principal table in the database"""
    try:
        principal_names = gen_utils().get_all_pi_names()
        db.session.query(Principal).delete()
        for p in principal_names:
            principal = Principal(principal_name=p)
            db.session.add(principal)
            db.session.commit()
    except Dcm4cheError as err:
        err_cause = err.__cause__.stderr
        print(err_cause)
    return "Success"
