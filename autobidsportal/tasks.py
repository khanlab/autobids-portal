from autobidsportal import app, db
from autobidsportal.models import User, Answer, Task, Notification, Cfmm2tar
from autobidsportal.dcm4cheutils import Dcm4cheUtils, gen_utils, Cfmm2tarError
from rq import get_current_job 
from datetime import datetime
import time
import os
import subprocess

def _set_task_progress(progress, error):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {'task_id': job.get_id(), 'progress': progress})
        print(progress)
        print(error)
        if progress != 100:
            if error != None:
                task.error = error
        else:
            task.complete = True
            task.success = True
            task.error = error
            task.end_time = datetime.utcnow()
        db.session.commit()

def get_info_from_cfmm2tar(user_id, button_id):
    _set_task_progress(0, "None")
    user = User.query.get(user_id)
    submitter_answer = db.session.query(Answer).filter(Answer.submitter_id==button_id)[0]
    if submitter_answer.principal_other != '':
        study_info = f"{submitter_answer.principal_other}^{submitter_answer.project_name}"
    else:
        study_info = f"{submitter_answer.principal}^{submitter_answer.project_name}"
    data = "/home/debian/cfmm2tar-download"
    try:
        cfmm2tar_result = gen_utils().run_cfmm2tar(out_dir=data, project=study_info)
        if cfmm2tar_result != None:
            for result in cfmm2tar_result:
                cfmm2tar = Cfmm2tar(user_id=user_id, tar_file=result[0], uid_file=result[1])
                db.session.add(cfmm2tar)
                db.session.commit()
            time.sleep(10)
            _set_task_progress(100, "None")
        else:
            err = "Invalid Principal or Project Name"
            _set_task_progress(0, err)
    except Cfmm2tarError as err:
        _set_task_progress(0, err.__cause__.stderr)
        raise err
        return err
    except Exception as err:
        _set_task_progress(0, err.__cause__.stderr)
        raise err
        return err