"""Define SQL models."""

# pylint: disable=too-few-public-methods
# Table classes are useful without public methods

from datetime import datetime
from time import time
import json

from flask import current_app
from flask_login import LoginManager, UserMixin
from sqlalchemy import MetaData
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import rq
from flask_sqlalchemy import SQLAlchemy


login = LoginManager()
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)

accessible_studies = db.Table(
    "accessible_studies",
    db.Column(
        "user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True
    ),
    db.Column(
        "study_id", db.Integer, db.ForeignKey("study.id"), primary_key=True
    ),
)

tar2bids_runs = db.Table(
    "tar2bids_runs",
    db.Column(
        "cfmm2tar_output_id",
        db.Integer,
        db.ForeignKey("cfmm2tar_output.id"),
        primary_key=True,
    ),
    db.Column(
        "tar2bids_output_id",
        db.Integer,
        db.ForeignKey("tar2bids_output.id"),
        primary_key=True,
    ),
)


class User(UserMixin, db.Model):
    """Information related to registered users."""

    id = db.Column(db.Integer, primary_key=True)
    admin = db.Column(db.Boolean, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship("Task", backref="user", lazy=True)
    notifications = db.relationship("Notification", backref="user", lazy=True)

    def __repr__(self):
        return f"<User ID {self.id} {self.admin, self.email, self.last_seen}>"

    def set_password(self, password):
        """Generate a hash for a password and assign it to the user."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check whether the password matches this user's password."""
        return check_password_hash(self.password_hash, password)

    def add_notification(self, name, data):
        """Set the user's active notification."""
        Notification.query.filter_by(name=name, user_id=self.id).delete()
        notification = Notification(
            name=name, payload_json=json.dumps(data), user=self
        )
        db.session.add(notification)
        return notification

    def launch_task(self, name, description, *args, **kwargs):
        """Enqueue a task with rq and record it in the DB."""
        if name == "get_info_from_cfmm2tar":
            rq_job = current_app.task_queue.enqueue(
                "autobidsportal.tasks." + name,
                *args,
                **kwargs,
                job_timeout=100000,
            )
            task = Task(
                id=rq_job.get_id(),
                name=name,
                description=description,
                user_id=self.id,
                user=self,
                start_time=datetime.utcnow(),
                study_id=args[0],
            )
        elif name == "get_info_from_tar2bids":
            rq_job = current_app.task_queue.enqueue(
                "autobidsportal.tasks." + name,
                *args,
                **kwargs,
                job_timeout=100000,
            )
            task = Task(
                id=rq_job.get_id(),
                name=name,
                description=description,
                user_id=self.id,
                user=self,
                start_time=datetime.utcnow(),
                study_id=args[0],
            )
        elif name == "update_heuristics":
            rq_job = current_app.task_queue.enqueue(
                "autobidsportal.tasks." + name,
                *args,
                **kwargs,
                job_timeout=1000,
            )
            task = Task(
                id=rq_job.get_id(),
                name=name,
                description=description,
                user_id=self.id,
                user=self,
                start_time=datetime.utcnow(),
            )
        db.session.add(task)
        db.session.commit()
        return task

    def get_completed_tasks(self):
        """Get all completed tasks associated with this user."""
        return Task.query.filter_by(user=self, complete=True).all()

    def get_task_in_progress(self, name):
        """Get this user's active task with the given name."""
        return Task.query.filter_by(
            name=name,
            user=self,
            complete=False,
            task_button_id=self.last_pressed_button_id,
        ).first()


@login.user_loader
def load_user(user_id):
    """Get a user with a specific ID."""
    return User.query.get(int(user_id))


class Study(db.Model):
    """One study on the DICOM server."""

    # Survey answers
    id = db.Column(db.Integer, primary_key=True)
    submitter_name = db.Column(db.String(100), nullable=False)
    submitter_email = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    scanner = db.Column(db.String(20), nullable=False)
    scan_number = db.Column(db.Integer, nullable=False)
    study_type = db.Column(db.Boolean, nullable=False)
    familiarity_bids = db.Column(db.String(20), nullable=False)
    familiarity_bidsapp = db.Column(db.String(20), nullable=False)
    familiarity_python = db.Column(db.String(20), nullable=False)
    familiarity_linux = db.Column(db.String(20), nullable=False)
    familiarity_bash = db.Column(db.String(20), nullable=False)
    familiarity_hpc = db.Column(db.String(20), nullable=False)
    familiarity_openneuro = db.Column(db.String(20), nullable=False)
    familiarity_cbrain = db.Column(db.String(20), nullable=False)
    principal = db.Column(db.String(20), nullable=False)
    project_name = db.Column(db.String(20), nullable=False)
    dataset_name = db.Column(db.String(20), nullable=False)
    sample = db.Column(db.DateTime, nullable=True)
    retrospective_data = db.Column(db.Boolean, nullable=False)
    retrospective_start = db.Column(db.DateTime, nullable=True)
    retrospective_end = db.Column(db.DateTime, nullable=True)
    consent = db.Column(db.Boolean, nullable=False)
    comment = db.Column(db.String(200), nullable=True)
    submission_date = db.Column(
        db.DateTime, index=True, default=datetime.utcnow, nullable=False
    )

    # Study config
    heuristic = db.Column(
        db.String(200), nullable=False, default="cfmm_base.py"
    )
    tar2bids_img = db.Column(db.Text(), nullable=False)
    patient_str = db.Column(db.String(50), nullable=False, default="*")
    subj_expr = db.Column(db.String(50), nullable=False, default="*_{subject}")
    users_authorized = db.relationship(
        "User",
        secondary=accessible_studies,
        lazy="subquery",
        backref=db.backref("studies", lazy=True),
    )
    patient_name_re = db.Column(db.Text())
    explicit_patients = db.relationship("ExplicitPatient", backref="study")

    # Study outputs
    tasks = db.relationship("Task", backref="study", lazy=True)
    cfmm2tar_outputs = db.relationship(
        "Cfmm2tarOutput", backref="study", lazy=True
    )
    tar2bids_outputs = db.relationship(
        "Tar2bidsOutput", backref="study", lazy=True
    )

    def __repr__(self):
        answer_cols = (
            self.status,
            self.scanner,
            self.scan_number,
            self.study_type,
            self.familiarity_bids,
            self.familiarity_bidsapp,
            self.familiarity_python,
            self.familiarity_linux,
            self.familiarity_bash,
            self.familiarity_hpc,
            self.familiarity_openneuro,
            self.familiarity_cbrain,
            self.principal,
            self.project_name,
            self.dataset_name,
            self.sample,
            self.retrospective_data,
            self.retrospective_start,
            self.retrospective_end,
            self.consent,
            self.comment,
            self.submission_date,
        )
        return f"<Answer {answer_cols}>"

    def get_tasks_in_progress(self):
        """Return all active tasks associated with this study."""
        return Task.query.filter_by(study=self, complete=False).all()


class Notification(db.Model):
    """An active notification for an active user."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text, nullable=False)

    def get_data(self):
        """Get the notification contents."""
        return json.loads(str(self.payload_json))

    def __repr__(self):
        return f"<Notification {self.name}, {self.timestamp}>"


class Task(db.Model):
    """A task deferred to the task queue."""

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True, nullable=False)
    description = db.Column(db.String(128), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=True)
    complete = db.Column(db.Boolean, default=False, nullable=False)
    success = db.Column(db.Boolean, default=False, nullable=True)
    error = db.Column(db.String(128), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        task_cols = (
            self.user_id,
            self.study_id,
            self.complete,
            self.success,
            self.error,
        )
        return f"<Task {task_cols}>"

    def get_rq_job(self):
        """Get the rq job associated with this task."""
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        """Get the progress of this task."""
        job = self.get_rq_job()
        return job.meta.get("progress", 0) if job is not None else 100


class Cfmm2tarOutput(db.Model):
    """One completed cfmm2tar run."""

    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    tar_file = db.Column(db.String(200), index=True, nullable=False)
    uid = db.Column(db.String(200), index=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    tar2bids_outputs = db.relationship(
        "Tar2bidsOutput",
        secondary=tar2bids_runs,
        lazy=True,
        backref=db.backref("cfmm2tar_outputs", lazy=True),
    )

    def __repr__(self):
        return f"<Cfmm2tar {self.tar_file, self.uid, self.date}>"


class Tar2bidsOutput(db.Model):
    """One completed tar2bids run."""

    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    bids_dir = db.Column(db.String(200), index=True)
    heuristic = db.Column(db.String(200), index=True)

    def __repr__(self):
        out_fields = (self.cfmm2tar_output_id, self.bids_dir, self.heuristic)
        return f"<Tar2bids {out_fields}>"


class Principal(db.Model):
    """One PI name known on the DICOM scanner."""

    id = db.Column(db.Integer, primary_key=True)
    principal_name = db.Column(db.String(200))

    def __repr__(self):
        return f"<Principal {self.principal_name}>"


class ExplicitPatient(db.Model):
    """A tar file to be explicitly included in or excluded from a study."""

    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    study_instance_uid = db.Column(db.String(64), unique=True)
    patient_name = db.Column(db.String(194))
    dicom_study_id = db.Column(db.String(16))
    included = db.Column(db.Boolean())
