from autobidsportal import app, db, mail
from autobidsportal.models import User, Submitter, Answer, Principal, Task
from autobidsportal.dcm4cheutils import Dcm4cheUtils, gen_utils, Cfmm2tarError
from rq import get_current_job 
import time

app.app_context().push()

def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.add(task)
        db.session.commit()

def get_info_from_cfmm2tar(user_id, button_id):
    user = User.query.get(user_id)
    submitter_answer = db.session.query(Answer).filter(Answer.submitter_id==button_id)[0]
    if submitter_answer.principal_other is not None:
        study_info = f"{submitter_answer.principal_other}^{submitter_answer.project_name}"
    else:
        study_info = f"{submitter_answer.principal}^{submitter_answer.project_name}"
    data = ""
    try:
        cfmm2tar_results = gen_utils().run_cfmm2tar(out_dir=data, project=study_info)
    except Cfmm2tarError as err:
        _set_task_progress(100)
        err_cause = err.__cause__.stderr