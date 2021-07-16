from datetime import datetime
from autobidsportal import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email, self.last_seen}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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

class Principal(db.Model):
    __tablename__ = 'principal'
    id = db.Column(db.Integer, primary_key=True)
    principal_name = db.Column(db.String(200))

    def __repr__(self):
        return f'<Prinicpal {self.principal_name}>'