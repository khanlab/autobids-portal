from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    BooleanField,
    RadioField,
    SelectField,
    DateField,
    TextAreaField,
    SelectMultipleField,
    widgets,
)
from wtforms.fields.html5 import EmailField, IntegerField, DateField
from wtforms.validators import (
    ValidationError,
    DataRequired,
    Length,
    Optional,
    InputRequired,
    Email,
    EqualTo,
)
from autobidsportal.models import Submitter, User, Answer
from autobidsportal.dcm4cheutils import Dcm4cheUtils, gen_utils, Dcm4cheError


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(
                "There is already an account using this email address. Please use a different email address."
            )


class BidsForm(FlaskForm):

    name = StringField("Name:", validators=[DataRequired()])

    email = EmailField("Email:", validators=[DataRequired()])

    status = RadioField(
        "Current status:",
        choices=[
            ("undergraduate", "Undergraduate Student"),
            ("graduate", "Graduate Student"),
            ("staff", "Staff"),
            ("post-doc", "Post-Doc"),
            ("faculty", "Faculty"),
            ("other", "Other"),
        ],
        validators=[InputRequired()],
    )

    scanner = RadioField(
        "Which scanner?:",
        choices=[
            ("type1", "3T"),
            ("type2", "7T"),
        ],
        validators=[InputRequired()],
    )

    scan_number = IntegerField(
        "How many scans are expected in this study (approximate)?:",
        validators=[DataRequired()],
    )

    study_type = BooleanField(
        "Is this study longitudinal or multi-session (i.e. same subject scanned multiple times)? If so, check the box below.:",
        validators=[Optional()],
    )

    familiarity_bids = SelectField(
        "BIDS:",
        choices=[
            ("1", "Not familiar at all"),
            ("2", "Have heard of it"),
            ("3", "Have used of it"),
            ("4", "Used it regularly"),
            ("5", "I consider myself an expert"),
        ],
        validators=[InputRequired()],
    )

    familiarity_bidsapp = SelectField(
        "BIDS Apps:",
        choices=[
            ("1", "Not familiar at all"),
            ("2", "Have heard of it"),
            ("3", "Have used of it"),
            ("4", "Used it regularly"),
            ("5", "I consider myself an expert"),
        ],
        validators=[InputRequired()],
    )

    familiarity_python = SelectField(
        "Python:",
        choices=[
            ("1", "Not familiar at all"),
            ("2", "Have heard of it"),
            ("3", "Have used of it"),
            ("4", "Used it regularly"),
            ("5", "I consider myself an expert"),
        ],
        validators=[InputRequired()],
    )

    familiarity_linux = SelectField(
        "Linux:",
        choices=[
            ("1", "Not familiar at all"),
            ("2", "Have heard of it"),
            ("3", "Have used of it"),
            ("4", "Used it regularly"),
            ("5", "I consider myself an expert"),
        ],
        validators=[InputRequired()],
    )

    familiarity_bash = SelectField(
        "BASH:",
        choices=[
            ("1", "Not familiar at all"),
            ("2", "Have heard of it"),
            ("3", "Have used of it"),
            ("4", "Used it regularly"),
            ("5", "I consider myself an expert"),
        ],
        validators=[InputRequired()],
    )

    familiarity_hpc = SelectField(
        "HPC Systems:",
        choices=[
            ("1", "Not familiar at all"),
            ("2", "Have heard of it"),
            ("3", "Have used of it"),
            ("4", "Used it regularly"),
            ("5", "I consider myself an expert"),
        ],
        validators=[InputRequired()],
    )

    familiarity_openneuro = SelectField(
        "Open Neuro:",
        choices=[
            ("1", "Not familiar at all"),
            ("2", "Have heard of it"),
            ("3", "Have used of it"),
            ("4", "Used it regularly"),
            ("5", "I consider myself an expert"),
        ],
        validators=[InputRequired()],
    )

    familiarity_cbrain = SelectField(
        "CBRAIN:",
        choices=[
            ("1", "Not familiar at all"),
            ("2", "Have heard of it"),
            ("3", "Have used of it"),
            ("4", "Used it regularly"),
            ("5", "I consider myself an expert"),
        ],
        validators=[InputRequired()],
    )

    principal = SelectField(
        'What is the "Principal" or "PI" identifier for this study?:',
        choices=[],
    )

    principal_other = StringField(
        'If you selected "Other" for the question above please enter the "Principal" or "PI" identifier for this study below:',
        validators=[Optional()],
    )

    project_name = StringField(
        'What is the "Project Name" identifier for this study?:',
        validators=[DataRequired()],
    )

    dataset_name = StringField(
        'The name for your BIDS dataset will by default be the "Project Name". If you wish to override this, please enter a new name below (optional):',
        validators=[Optional()],
    )

    sample = DateField(
        "Please enter the scan date for this example session:",
        format="%Y-%m-%d",
        validators=[Optional()],
    )

    retrospective_data = BooleanField(
        "Does this study have retrospective (previously acquired) data to convert? If so, check the box below.:"
    )

    retrospective_start = DateField(
        "Please enter start date of retrospective conversion.:",
        format="%Y-%m-%d",
        validators=[Optional()],
    )

    retrospective_end = DateField(
        "Please enter end date of retrospective conversion (or leave blank if ongoing).:",
        format="%Y-%m-%d",
        validators=[Optional()],
    )

    consent = BooleanField(
        "By checking the box below, you are agreeing with these general terms.",
        validators=[DataRequired()],
    )

    comment = TextAreaField("Comments")

    submit = SubmitField("Submit")


class HeuristicForm(FlaskForm):
    heuristic = SelectField(
        "Heuristic:",
        choices=[
            ("cfmm_baron.py", "cfmm_baron.py"),
            ("cfmm_base.py", "cfmm_base.py"),
            ("cfmm_bold_rest.py", "cfmm_bold_rest.py"),
            ("cfmm_bruker.py", "cfmm_bruker.py"),
            ("cfmm_PS_PRC_3T.py", "cfmm_PS_PRC_3T.py"),
            ("clinicalDBS.py", "clinicalDBS.py"),
            ("cmrr_ANNA_OBJCAT_MTL_3T.py", "cmrr_ANNA_OBJCAT_MTL_3T.py"),
            ("EPL14A_GE_3T.py", "EPL14A_GE_3T.py"),
            ("EPL14B_3T.py", "EPL14B_3T.py"),
            ("GEvSE.py", "GEvSE.py"),
            ("Kohler_HcECT.py", "Kohler_HcECT.py"),
            ("Menon_CogMS.py", "Menon_CogMS.py"),
        ],
        validators=[InputRequired()],
    )


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class AccessForm(FlaskForm):
    choices = MultiCheckboxField("Access", coerce=int)


class RemoveAccessForm(FlaskForm):
    choices_to_remove = MultiCheckboxField("Remove access", coerce=int)
