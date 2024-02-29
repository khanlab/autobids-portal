"""Define SQL models."""

# id is needed for these models
# ruff: noqa: A003
from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
from time import time
from typing import Any

from flask import current_app
from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from redis.exceptions import RedisError
from rq.exceptions import NoSuchJobError
from rq.job import Job
from sqlalchemy import MetaData
from werkzeug.security import check_password_hash, generate_password_hash

from autobidsportal.dateutils import TIME_ZONE


@lru_cache
def get_default_heuristic() -> str:
    """Read default heuristic file.

    Returns
    -------
    str
        Contents of heuristic
    """
    with (Path(__file__).parent / "resources" / "heuristics.py.default").open(
        encoding="utf-8",
    ) as heuristics_file:
        return heuristics_file.read()


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
        "user_id",
        db.Integer,
        db.ForeignKey("user.id"),
        primary_key=True,
    ),
    db.Column(
        "study_id",
        db.Integer,
        db.ForeignKey("study.id"),
        primary_key=True,
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

    def __repr__(self) -> str:
        """Generate a str representation of this notification."""
        return f"<Notification {self.name}, {self.timestamp}>"


class Task(db.Model):
    """A task deferred to the task queue."""

    TASKS = (
        "run_cfmm2tar",
        "run_tar2bids",
        "archive_raw_data",
        "gradcorrect_study",
        "archive_derivative_data",
    )

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=True)
    complete = db.Column(db.Boolean, default=False, nullable=False)
    success = db.Column(db.Boolean, default=False, nullable=True)
    error = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    log = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        """Generate a string representation of this task."""
        task_cols = (
            self.user_id,
            self.study_id,
            self.complete,
            self.success,
            self.error,
        )
        return f"<Task {task_cols}>"

    @classmethod
    def launch_task(
        cls,
        name: str,
        description: str,
        *args,
        user: Any | None = None,
        timeout: int = 100000,
        study_id: int | None = None,
        **kwargs,
    ):
        """Enqueue a task with rq and record it in the DB.

        Parameters
        ----------
        name
            Task name to complete

        description
            Description of task

        *args
            Variable positional arguments to be passed to task function

        user
            User associated with task

        timeout
            Time in milliseconds before task times out

        study_id
            Study id associated with task

        **kwargs
            Additional keyword arguments to be passed to task function

        Returns
        -------
        Task
            Object defining task to be completed
        """
        if name not in cls.TASKS:
            msg = "Invalid task name"
            raise ValueError(msg)

        rq_job = Job.create(
            f"autobidsportal.tasks.{name}",
            args=args,
            kwargs=kwargs,
            timeout=timeout,
            connection=current_app.redis,  # pyright: ignore
        )

        task = cls(
            id=rq_job.get_id(),
            name=name,
            description=description,
            user=user,
            start_time=datetime.now(tz=TIME_ZONE),
            study_id=study_id,
        )

        db.session.add(task)  # pyright: ignore
        db.session.commit()  # pyright: ignore
        current_app.task_queue.enqueue_job(rq_job)  # pyright: ignore

        return task

    def get_rq_job(self):
        """Get the rq job associated with this task."""
        try:
            rq_job = Job.fetch(
                self.id,
                connection=current_app.redis,  # pyright: ignore
            )
        except (RedisError, NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        """Get the progress of this task."""
        job = self.get_rq_job()
        return job.meta.get("progress", 0) if job is not None else 100


class User(UserMixin, db.Model):
    """Information related to registered users."""

    id = db.Column(db.Integer, primary_key=True)
    admin = db.Column(db.Boolean, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship("Task", backref="user", lazy=True)
    notifications = db.relationship("Notification", backref="user", lazy=True)

    def __repr__(self) -> str:
        """Generate a nice str representation of this user."""
        return f"<User ID {self.id} {self.admin, self.email, self.last_seen}>"

    def set_password(self, password: str):
        """Generate a hash for a password and assign it to the user.

        Parameters
        ----------
        password
            User-set password to generate hash for
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check whether the password matches this user's password.

        Parameters
        ----------
        password
            User-provided password to check against hash

        Returns
        -------
        bool
            Indicator of whether password matches expected
        """
        return check_password_hash(self.password_hash, password)

    def add_notification(
        self,
        name: str,
        data: dict[str, Any],
    ) -> Notification:
        """Set the user's active notification.

        Parameters
        ----------
        name
            Notification name

        data
            Dictionary containing notification payload

        Returns
        -------
        Notification
            Notification object
        """
        Notification.query.filter_by(name=name, user_id=self.id).delete()

        notification = Notification(
            name=name,
            payload_json=json.dumps(data),
            user=self,
        )

        db.session.add(notification)  # pyright: ignore

        return notification

    def get_completed_tasks(self) -> Sequence[Task]:
        """Get all completed tasks.

        Returns
        -------
        Sequence[Task]
            All completed tasks associated with this user.
        """
        return Task.query.filter_by(user=self, complete=True).all()

    def get_task_in_progress(self, name: str):
        """Get this user's active task with the given name.

        Parameters
        ----------
        name
            Notification name

        Returns
        -------
        Task
            Get first active task in-progress for user

        """
        return Task.query.filter_by(
            name=name,
            user=self,
            complete=False,
        ).first()


@login.user_loader
def load_user(user_id: str) -> User:
    """Get a user with a specific ID.

    Parameters
    ----------
    user_id
        String representation of specific ID for given user

    Returns
    -------
    User
        User object
    """
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
        db.DateTime,
        index=True,
        default=datetime.utcnow,
        nullable=False,
    )

    active = db.Column(db.Boolean, nullable=False, default=False)

    # Study config
    patient_str = db.Column(db.String(50), nullable=False, default="*")
    subj_expr = db.Column(db.String(50), nullable=False, default="*_{subject}")
    deface = db.Column(db.Boolean, nullable=False, default=False)
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
        "Cfmm2tarOutput",
        backref="study",
        lazy=True,
    )
    tar2bids_outputs = db.relationship(
        "Tar2bidsOutput",
        backref="study",
        lazy=True,
    )
    dataset_content = db.Column(db.JSON(), nullable=True)
    datalad_datasets = db.relationship("DataladDataset", backref="study")

    custom_ria_url = db.Column(db.Text, nullable=True)
    globus_usernames = db.relationship("GlobusUsername", backref="study")

    custom_bidsignore = db.Column(db.Text, nullable=True)

    # There should be a default here
    heuristic = db.Column(
        db.Text,
        nullable=False,
        default=get_default_heuristic(),
    )

    def __repr__(self) -> str:
        """Generate a str representation of this study."""
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

    def get_tasks_in_progress(self) -> Sequence[Task]:
        """Return all active tasks associated with this study.

        Returns
        -------
        Sequence[Task]
            All active tasks in study
        """
        return Task.query.filter_by(study=self, complete=False).all()

    def update_custom_ria_url(self, new_url: str | None):
        """Update custom ria URL for this study and its associated datasets.

        Parameters
        ----------
        new_url
            New RIA url for study (Optional)
        """
        self.custom_ria_url = new_url
        for dataset in self.datalad_datasets:  # pyright: ignore
            dataset.custom_ria_url = new_url


class Cfmm2tarOutput(db.Model):
    """One completed cfmm2tar run."""

    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    tar_file = db.Column(db.String(200), index=True, nullable=False)
    attached_tar_file = db.Column(db.Text, nullable=True)
    uid = db.Column(db.String(200), index=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    datalad_dataset_id = db.Column(
        db.Integer,
        db.ForeignKey("datalad_dataset.id"),
        nullable=True,
    )
    tar2bids_outputs = db.relationship(
        "Tar2bidsOutput",
        secondary=tar2bids_runs,
        lazy=True,
        backref=db.backref("cfmm2tar_outputs", lazy=True),
    )

    def __repr__(self) -> str:
        """Generate a str representation of this output."""
        return f"<Cfmm2tar {self.tar_file, self.uid, self.date}>"


class Tar2bidsOutput(db.Model):
    """One completed tar2bids run."""

    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    bids_dir = db.Column(db.String(200), index=True, nullable=True)
    heuristic = db.Column(db.Text, index=True, nullable=False)

    def __repr__(self) -> str:
        """Generate a str representation of this output."""
        out_fields = (self.study_id, self.bids_dir, self.heuristic)
        return f"<Tar2bids {out_fields}>"


class DatasetType(Enum):
    """Enum to describe the possible dataset types."""

    SOURCE_DATA = 1
    RAW_DATA = 2
    DERIVED_DATA = 3

    def to_bids_str(self) -> str:
        """Produce a BIDS-style string for serialization."""
        map_ = {
            DatasetType.SOURCE_DATA: "sourcedata",
            DatasetType.RAW_DATA: "rawdata",
            DatasetType.DERIVED_DATA: "deriveddata",
        }
        return map_[self]


class DataladDataset(db.Model):
    """A datalad dataset relating to a study."""

    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    dataset_type = db.Column(db.Enum(DatasetType), nullable=False)
    ria_alias = db.Column(db.String, nullable=False, unique=True)
    custom_ria_url = db.Column(db.Text, nullable=True)
    cfmm2tar_outputs = db.relationship(
        "Cfmm2tarOutput",
        backref="datalad_dataset",
    )
    dataset_archives = db.relationship(
        "DatasetArchive",
        backref="datalad_dataset",
    )
    db.UniqueConstraint(study_id, dataset_type)


class DatasetArchive(db.Model):
    """An archive containing a portion of the dataset's content."""

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(
        db.Integer,
        db.ForeignKey("datalad_dataset.id"),
        nullable=False,
    )
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("dataset_archive.id"),
        nullable=True,
    )
    parent = db.relationship("DatasetArchive", remote_side=[id])
    dataset_hexsha = db.Column(db.Text, nullable=False)
    commit_datetime = db.Column(db.DateTime, nullable=False)


class Principal(db.Model):
    """One PI name known on the DICOM scanner."""

    id = db.Column(db.Integer, primary_key=True)
    principal_name = db.Column(db.String(200))

    def __repr__(self) -> str:
        """Generate a string representation of this PI."""
        return f"<Principal {self.principal_name}>"


class ExplicitPatient(db.Model):
    """A tar file to be explicitly included in or excluded from a study."""

    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    study_instance_uid = db.Column(db.String(64), unique=True)
    patient_name = db.Column(db.String(194))
    dicom_study_id = db.Column(db.String(16))
    included = db.Column(db.Boolean())


class GlobusUsername(db.Model):
    """A globus username that should be given access to a study's archive."""

    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey("study.id"), nullable=False)
    username = db.Column(db.Text, nullable=False)
