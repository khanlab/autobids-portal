from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from autobidsportal import db, login
from time import time
import json
import redis
import rq

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_pressed_button_id = db.Column(db.Integer)
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')
    cfmm2tar_results = db.relationship('Cfmm2tar', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email, self.last_seen, self.last_pressed_button_id}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('autobidsportal.tasks.' + name, self.id, self.last_pressed_button_id, *args, **kwargs, job_timeout=100000)
        task = Task(id=rq_job.get_id(), name=name, description=description, user_id=self.id, user=self, start_time=datetime.utcnow(), task_button_id=self.last_pressed_button_id)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self, complete=False, task_button_id=self.last_pressed_button_id).first()

    def get_completed_tasks(self):
        return Task.query.filter_by(user=self, complete=True).all()

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Submitter(db.Model):
    __tablename__ = 'submitter'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40))
    email = db.Column(db.String(40))
    answers = db.relationship('Answer', backref='submitter', lazy='dynamic')

    def __repr__(self):
        return f'<Submitter {self.name, self.email}>'

class Answer(db.Model):
    __tablename__ = 'answer'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20))
    scanner = db.Column(db.String(20))
    scan_number = db.Column(db.Integer)
    study_type = db.Column(db.Boolean)
    familiarity_bids = db.Column(db.String(20))
    familiarity_bidsapp = db.Column(db.String(20))
    familiarity_python = db.Column(db.String(20))
    familiarity_linux = db.Column(db.String(20))
    familiarity_bash = db.Column(db.String(20))
    familiarity_hpc = db.Column(db.String(20))
    familiarity_openneuro = db.Column(db.String(20))
    familiarity_cbrain = db.Column(db.String(20))
    principal = db.Column(db.String(20))
    principal_other = db.Column(db.String(20))
    project_name = db.Column(db.String(20))
    dataset_name = db.Column(db.String(20))
    sample = db.Column(db.DateTime)
    retrospective_data = db.Column(db.Boolean)
    retrospective_start = db.Column(db.DateTime)
    retrospective_end = db.Column(db.DateTime)
    consent = db.Column(db.Boolean)
    comment = db.Column(db.String(200))
    submission_date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    submitter_id = db.Column(db.Integer, db.ForeignKey('submitter.id'))

    def __repr__(self):
        return f'<Answer {self.status, self.scanner, self.scan_number, self.study_type, self.familiarity_bids, self.familiarity_bidsapp, self.familiarity_python, self.familiarity_linux, self.familiarity_bash, self.familiarity_hpc, self.familiarity_openneuro, self.familiarity_cbrain, self.principal, self.principal_other, self.project_name, self.dataset_name, self.sample, self.retrospective_data, self.retrospective_start, self.retrospective_end, self.consent, self.comment, self.submission_date}>'

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))

class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    task_button_id = db.Column(db.Integer)
    complete = db.Column(db.Boolean, default=False)
    success = db.Column(db.Boolean, default=False)
    error = db.Column(db.String(128))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Task {self.user_id, self.task_button_id, self.complete, self.success, self.error}>'

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100

class Cfmm2tar(db.Model):
    __tablename__ = 'cfmm2tar'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    task_button_id = db.Column(db.Integer)
    tar_file = db.Column(db.String(200), index=True)
    uid_file = db.Column(db.String(200), index=True)
    date = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Cfmm2tar {self.tar_file, self.uid_file, self.date}>'

class Principal(db.Model):
    __tablename__ = 'principal'
    id = db.Column(db.Integer, primary_key=True)
    principal_name = db.Column(db.String(200))

    def __repr__(self):
        return f'<Prinicpal {self.principal_name}>'
