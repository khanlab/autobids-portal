from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, RadioField, SelectField, DateField, TextAreaField
from wtforms.fields.html5 import EmailField, IntegerField, DateField
from wtforms.validators import ValidationError, DataRequired, Length, Optional, InputRequired, Email, EqualTo
from app.models import Submitter, User, Answer

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class BidsForm(FlaskForm):

    name = StringField('Name:', validators=[DataRequired()])

    email = EmailField('Email:', validators=[DataRequired()])
    
    status = RadioField('Current status:', choices=[
        ('undergraduate', 'Undergraduate Student'),
        ('graduate', 'Graduate Student'),
        ('staff', 'Staff'),
        ('post-doc', 'Post-Doc'),
        ('faculty', 'Faculty'),
        ('other', 'Other'),
    ], validators=[InputRequired()])
    
    scanner = RadioField('Which scanner?:', choices=[
        ('type1', '3T'),
        ('type2', '7T'),
    ], validators=[InputRequired()])
    
    scan_number = IntegerField('How many scans are expected in this study (approximate)?:', validators=[DataRequired()])
    
    study_type = RadioField('Is this study longitudinal or multi-session (i.e. same subject scanned multiple times)?:', choices=[
        ('yes', 'Yes'),
        ('no', 'No'),
    ], validators=[InputRequired()])

    familiarity_bids = SelectField('BIDS:', choices=[
        ('1', 'Not familiar at all'),
        ('2', 'Have heard of it'),
        ('3', 'Have used of it'),
        ('4', 'Used it regularly'),
        ('5', 'I consider myself an expert'),
    ], validators=[InputRequired()])

    familiarity_bidsapp = SelectField('BIDS Apps:', choices=[
        ('1', 'Not familiar at all'),
        ('2', 'Have heard of it'),
        ('3', 'Have used of it'),
        ('4', 'Used it regularly'),
        ('5', 'I consider myself an expert'),
    ], validators=[InputRequired()])

    familiarity_python = SelectField('Python:', choices=[
        ('1', 'Not familiar at all'),
        ('2', 'Have heard of it'),
        ('3', 'Have used of it'),
        ('4', 'Used it regularly'),
        ('5', 'I consider myself an expert'),
    ], validators=[InputRequired()])

    familiarity_linux = SelectField('Linux:', choices=[
        ('1', 'Not familiar at all'),
        ('2', 'Have heard of it'),
        ('3', 'Have used of it'),
        ('4', 'Used it regularly'),
        ('5', 'I consider myself an expert'),
    ], validators=[InputRequired()])

    familiarity_bash = SelectField('BASH:', choices=[
        ('1', 'Not familiar at all'),
        ('2', 'Have heard of it'),
        ('3', 'Have used of it'),
        ('4', 'Used it regularly'),
        ('5', 'I consider myself an expert'),
    ], validators=[InputRequired()])

    familiarity_hpc = SelectField('HPC Systems:', choices=[
        ('1', 'Not familiar at all'),
        ('2', 'Have heard of it'),
        ('3', 'Have used of it'),
        ('4', 'Used it regularly'),
        ('5', 'I consider myself an expert'),
    ], validators=[InputRequired()])

    familiarity_openneuro = SelectField('Open Neuro:', choices=[
        ('1', 'Not familiar at all'),
        ('2', 'Have heard of it'),
        ('3', 'Have used of it'),
        ('4', 'Used it regularly'),
        ('5', 'I consider myself an expert'),
    ], validators=[InputRequired()])

    familiarity_cbrain = SelectField('CBRAIN:', choices=[
        ('1', 'Not familiar at all'),
        ('2', 'Have heard of it'),
        ('3', 'Have used of it'),
        ('4', 'Used it regularly'),
        ('5', 'I consider myself an expert'),
    ], validators=[InputRequired()])

    principal = StringField('What is the "Principal" or "PI" identifier for this study?:', validators=[DataRequired()])

    project_name = StringField('What is the "Project Name" identifier for this study?:', validators=[DataRequired()])

    dataset_name = StringField('The name for your BIDS dataset will by default be the "Project Name". If you wish to override this, please enter a new name below (optional):', validators=[Optional()])

    retrospective_data = RadioField('Does this study have retrospective (previously acquired) data to convert?:', choices=[
        ('yes', 'Yes'),
        ('no', 'No'),
    ], validators=[InputRequired()])
    
    retrospective_start = DateField('If so, please enter start date of retrospective conversion:', format='%m/%d/%Y', validators=[Optional()])

    retrospective_end = DateField('Please enter end date of retrospective conversion (or leave blank if ongoing):', format='%m/%d/%Y', validators=[Optional()])

    consent = RadioField('By clicking yes below, you agree with these general terms.', choices=[
        ('yes', 'Yes'),
    ], validators=[InputRequired()])

    comment = TextAreaField('Comments')

    submit = SubmitField('Submit')