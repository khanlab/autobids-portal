from autobidsportal import app, db, mail
from autobidsportal.models import User, Submitter, Answer, Principal, Task
from rq import get_current_job 
import time
import sys

app.app_context().push()

def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.answer.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.add(task)
        db.session.commit()

def get_info_from_cfm2tarr(button_id):
    try:
        _set_task_progress(0)
        data = []
        i = 0
        total_answers = len(answers)
        for a in answers:
            # data.append({'timestamp': a.timestamp.isoformat() + 'Z'})
            time.sleep(5)
            i += 1
            _set_task_progress(100 * i // total_answers)
    except:
        _set_task_progress(100)
#display task bar until task is completed on failed
# if not current run disply most recent task bar or task table -> never been a run display just the button
#pulling a dataset that has been referenced
#use a button on dataset page that initiates cfm to tar to download any available data and put it on a table and puts it on a page