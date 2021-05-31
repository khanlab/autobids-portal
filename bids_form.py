from autobidsportal import app, db
from autobidsportal.models import User, Answer, Submitter


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Answer': Answer, 'Submitter': Submitter}
