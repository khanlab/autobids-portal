from autobidsportal import app, db
from autobidsportal.dcm4cheutils import Dcm4cheUtils, gen_utils, Dcm4cheError
from autobidsportal.models import User, Answer, Submitter, Task
from datetime import datetime
import time


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Answer': Answer, 'Submitter': Submitter, 'Task': Task}

@app.cli.command()
def scheduled():
    """Run scheduled job."""
    print(str(datetime.utcnow()), 'Importing principal names...')
    try:
        principal_names = [(p, p) for p in gen_utils().get_all_pi_names()]
    except Dcm4cheError as err:
        principal_names = []
    print(str(datetime.utcnow()), principal_names)
    print(str(datetime.utcnow()), 'Done!')
    return principal_names