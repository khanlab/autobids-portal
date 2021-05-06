from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    answers = db.relationship('Answer', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Answer(db.Model):
    id= db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20))
    scanner = db.Column(db.String(20))
    scan_number = db.Column(db.Integer)
    study_type = db.Column(db.String(20))
    familiarity = db.Column(db.String(20))
    principal = db.Column(db.String(20))
    project_name = db.Column(db.String(20))
    dataset_name = db.Column(db.String(20))
    retrospective_data = db.Column(db.String(20))
    retrospective_start = db.Column(db.Integer)
    retrospective_end = db.Column(db.Integer)
    consent = db.Column(db.String(20))
    comment = db.Column(db.String(200))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Answer {self.status, self.scanner, self.scan_number, self.study_type, self.familiarity, self.principal, self.project_name, self.dataset_name, self.retrospective_data, self.retrospective_start, self.retrospective_end, self.consent, self.comment}>'
