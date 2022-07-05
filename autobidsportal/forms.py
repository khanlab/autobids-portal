"""Forms to be used in some views."""

from json import dumps

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    BooleanField,
    RadioField,
    SelectField,
    TextAreaField,
    SelectMultipleField,
    widgets,
)
from wtforms.fields.html5 import EmailField, IntegerField, DateField
from wtforms.validators import (
    ValidationError,
    DataRequired,
    Optional,
    InputRequired,
    Email,
    EqualTo,
)

from autobidsportal.models import User, ExplicitPatient, Study, GlobusUsername


DEFAULT_HEURISTICS = [
    "cfmm_baron.py",
    "cfmm_base.py",
    "cfmm_bold_rest.py",
    "cfmm_bruker.py",
    "cfmm_PS_PRC_3T.py",
    "clinicalDBS.py",
    "cmrr_ANNA_OBJCAT_MTL_3T.py",
    "EPL14A_GE_3T.py",
    "EPL14B_3T.py",
    "GEvSE.py",
    "Kohler_HcECT.py",
    "Menon_CogMS.py",
]

CHOICES_FAMILIARITY = [
    ("1", "Not familiar at all"),
    ("2", "Have heard of it"),
    ("3", "Have used of it"),
    ("4", "Used it regularly"),
    ("5", "I consider myself an expert"),
]


def _gen_familiarity_field(label):
    return SelectField(
        label,
        choices=CHOICES_FAMILIARITY,
        validators=[InputRequired()],
    )


class MultiCheckboxField(SelectMultipleField):
    """Generic field for multiple checkboxes."""

    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class LoginForm(FlaskForm):
    """A form for logging users in."""

    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


def unique_email(_, email):
    """Check that no user with this email address exists."""
    user = User.query.filter_by(email=email.data).one_or_none()
    if user is not None:
        raise ValidationError(
            "There is already an account using this email address. "
            + "Please use a different email address."
        )


class RegistrationForm(FlaskForm):
    """A form for registering new users."""

    email = StringField(
        "Email", validators=[DataRequired(), Email(), unique_email]
    )
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Register")


class BidsForm(FlaskForm):
    """Form representing the new study survey."""

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
        "Is this study longitudinal or multi-session (i.e. same subject "
        + "scanned multiple times)? If so, check the box below.:",
        validators=[Optional()],
    )

    familiarity_bids = _gen_familiarity_field("BIDS:")
    familiarity_bidsapp = _gen_familiarity_field("BIDS Apps:")
    familiarity_python = _gen_familiarity_field("Python:")
    familiarity_linux = _gen_familiarity_field("Linux:")
    familiarity_bash = _gen_familiarity_field("BASH:")
    familiarity_hpc = _gen_familiarity_field("HPC Systems:")
    familiarity_openneuro = _gen_familiarity_field("Open Neuro:")
    familiarity_cbrain = _gen_familiarity_field("CBRAIN:")

    principal = SelectField(
        'What is the "Principal" or "PI" identifier for this study?:',
        choices=[],
    )

    principal_other = StringField(
        'If you selected "Other" for the question above please enter the '
        + '"Principal" or "PI" identifier for this study below:',
        validators=[Optional()],
    )

    project_name = StringField(
        'What is the "Project Name" identifier for this study?:',
        validators=[DataRequired()],
    )

    dataset_name = StringField(
        'The name for your BIDS dataset will by default be the "Project '
        + 'Name". If you wish to override this, please enter a new name '
        + "below (optional):",
        validators=[Optional()],
    )

    sample = DateField(
        "Please enter the scan date for this example session:",
        format="%Y-%m-%d",
        validators=[Optional()],
    )

    retrospective_data = BooleanField(
        "Does this study have retrospective (previously acquired) data to "
        + "convert? If so, check the box below.:"
    )

    retrospective_start = DateField(
        "Please enter start date of retrospective conversion.:",
        format="%Y-%m-%d",
        validators=[Optional()],
    )

    retrospective_end = DateField(
        (
            "Please enter end date of retrospective conversion (or leave "
            "blank if ongoing).:"
        ),
        format="%Y-%m-%d",
        validators=[Optional()],
    )

    consent = BooleanField(
        (
            "By checking the box below, you are agreeing with these general "
            "terms."
        ),
        validators=[DataRequired()],
    )

    comment = TextAreaField("Comments")

    submit = SubmitField("Submit")

    def gen_study(self):
        """Generate a study from this form."""
        principal = (
            self.principal_other.data
            if self.principal.data == "Other"
            else self.principal.data
        )

        if self.retrospective_data.data:
            retrospective_start = self.retrospective_start.data
            retrospective_end = self.retrospective_end.data
        else:
            retrospective_start = None
            retrospective_end = None

        dataset_name = (
            self.dataset_name.data
            if self.dataset_name.data != ""
            else self.project_name.data
        )

        return Study(
            submitter_name=self.name.data,
            submitter_email=self.email.data,
            status=self.status.data,
            scanner=self.scanner.data,
            scan_number=self.scan_number.data,
            study_type=self.study_type.data,
            familiarity_bids=self.familiarity_bids.data,
            familiarity_bidsapp=self.familiarity_bidsapp.data,
            familiarity_python=self.familiarity_python.data,
            familiarity_linux=self.familiarity_linux.data,
            familiarity_bash=self.familiarity_bash.data,
            familiarity_hpc=self.familiarity_hpc.data,
            familiarity_openneuro=self.familiarity_openneuro.data,
            familiarity_cbrain=self.familiarity_cbrain.data,
            principal=principal,
            project_name=self.project_name.data,
            dataset_name=dataset_name,
            sample=self.sample.data,
            retrospective_data=self.retrospective_data.data,
            retrospective_start=retrospective_start,
            retrospective_end=retrospective_end,
            consent=self.consent.data,
            comment=self.comment.data,
        )


class StudyConfigForm(FlaskForm):
    """Form for editing an existing study."""

    active = BooleanField("Active")

    pi_name = SelectField("PI Name", choices=[])
    project_name = StringField("Project Name")
    dataset_name = StringField("Dataset Name")
    example_date = DateField("Example Date")
    retrospective_data = BooleanField("Retrospective?")
    retrospective_start = DateField("Start Date")
    retrospective_end = DateField("End Date")
    heuristic = SelectField("Heuristic", choices=[])
    subj_expr = StringField("Tar2bids Patient Name Search String")
    patient_str = StringField("DICOM PatientName Identifier")
    patient_re = StringField(
        "Regular expression to match with returned PatientNames"
    )
    excluded_patients = MultiCheckboxField(
        "Excluded Patient StudyInstanceUIDs"
    )
    newly_excluded = StringField("New StudyInstanceUID to exclude")
    included_patients = MultiCheckboxField(
        "Included Patient StudyInstanceUIDs"
    )
    newly_included = StringField("New StudyInstanceUID to include")
    users_authorized = MultiCheckboxField("Users With Access", coerce=int)
    custom_ria_url = StringField("Custom RIA URL")
    globus_usernames = MultiCheckboxField(
        "Globus identities with access to dataset archives"
    )
    new_globus_username = StringField("New Globus identity to grant access")

    def defaults_from_study(self, study, principals, heuristics, users):
        """Set up form defaults given options from the DB."""
        self.active.default = study.active
        self.pi_name.choices = principals
        self.pi_name.default = study.principal
        self.project_name.default = study.project_name
        if study.dataset_name is not None:
            self.dataset_name.default = study.dataset_name
        if study.sample is not None:
            self.example_date.default = study.sample
        self.retrospective_data.default = study.retrospective_data
        if study.retrospective_data:
            self.retrospective_start.default = study.retrospective_start
            self.retrospective_end.default = study.retrospective_end
        self.heuristic.choices = heuristics
        if study.heuristic is None:
            self.heuristic.default = "cfmm_base.py"
        else:
            self.heuristic.default = study.heuristic
        if study.subj_expr is None:
            self.subj_expr.default = "*_{subject}"
        else:
            self.subj_expr.default = study.subj_expr
        self.patient_str.default = study.patient_str
        if study.patient_name_re is None:
            self.patient_re.default = ".*"
        else:
            self.patient_re.default = study.patient_name_re
        self.excluded_patients.choices = [
            (
                patient.study_instance_uid,
                (
                    f"Patient Name: {patient.patient_name}, "
                    f"Study ID: {patient.dicom_study_id}"
                ),
            )
            for patient in study.explicit_patients
            if not patient.included
        ]
        self.excluded_patients.default = [
            patient.study_instance_uid
            for patient in study.explicit_patients
            if not patient.included
        ]
        self.newly_excluded.default = ""
        self.included_patients.choices = [
            (
                patient.study_instance_uid,
                (
                    f"Patient Name: {patient.patient_name}, "
                    f"Study ID: {patient.dicom_study_id}"
                ),
            )
            for patient in study.explicit_patients
            if patient.included
        ]
        self.included_patients.default = [
            patient.study_instance_uid
            for patient in study.explicit_patients
            if patient.included
        ]
        self.newly_included.default = ""
        self.users_authorized.choices = [
            (user.id, user.email) for user in users
        ]
        self.users_authorized.default = [
            user.id for user in study.users_authorized
        ]
        self.custom_ria_url.default = (
            study.custom_ria_url if study.custom_ria_url is not None else ""
        )
        self.globus_usernames.choices = [
            (username.id, username.username)
            for username in study.globus_usernames
        ]
        self.globus_usernames.default = [
            username.id for username in study.globus_usernames
        ]
        self.new_globus_username.default = ""

        self.process()

    def update_study(self, study, user_is_admin=False):
        """Process updates to a study from this form.

        Parameters
        ----------
        study : Study
            The study to update

        Returns
        -------
        study : Study
            The updated study.
        to_add : list of ExplicitPatient
            New ExplicitPatients to add.
        to_delete : list of ExplicitPatient
            Existing ExplicitPatients to delete.
        ids_authorized : list of int
            IDs of users to add to the authorized list.
        """
        # pylint: disable=too-many-branches
        study.principal = self.pi_name.data
        study.project_name = self.project_name.data
        study.dataset_name = self.dataset_name.data
        if self.example_date.data:
            study.sample = self.example_date.data
        else:
            study.sample = None
        if self.retrospective_data.data:
            study.retrospective_data = True
            study.retrospective_start = self.retrospective_start.data
            study.retrospective_end = self.retrospective_end.data
        else:
            study.retrospective_data = False
            study.retrospective_start = None
            study.retrospective_end = None
        study.heuristic = self.heuristic.data
        study.subj_expr = self.subj_expr.data
        study.patient_str = self.patient_str.data
        study.patient_name_re = self.patient_re.data
        to_delete = []
        for explicit_patient in study.explicit_patients:
            if explicit_patient.included and (
                explicit_patient.study_instance_uid
                not in self.included_patients.data
            ):
                to_delete.append(explicit_patient)
            elif (not explicit_patient.included) and (
                explicit_patient.study_instance_uid
                not in self.excluded_patients.data
            ):
                to_delete.append(explicit_patient)
        to_add = []
        if self.newly_excluded.data != "":
            to_add.append(
                ExplicitPatient(
                    study_id=study.id,
                    study_instance_uid=self.newly_excluded.data,
                    included=False,
                )
            )
        if self.newly_included.data != "":
            to_add.append(
                ExplicitPatient(
                    study_id=study.id,
                    study_instance_uid=self.newly_included.data,
                    included=True,
                )
            )
        ids_authorized = self.users_authorized.data
        if user_is_admin:
            study.active = self.active.data
            if self.custom_ria_url.data == "":
                study.update_custom_ria_url(None)
            else:
                study.update_custom_ria_url(self.custom_ria_url.data)
        self.globus_usernames.default = [
            username.id for username in study.globus_usernames
        ]
        if self.new_globus_username.data != "":
            to_add.append(
                GlobusUsername(
                    study_id=study.id, username=self.new_globus_username.data
                )
            )
        for username in study.globus_usernames:
            if str(username.id) not in self.globus_usernames.data:
                to_delete.append(username)

        return study, to_add, to_delete, ids_authorized


class Tar2bidsRunForm(FlaskForm):
    """Form for choosing which tar files to BIDSify."""

    tar_files = MultiCheckboxField("Tar files to use", coerce=int)


class AccessForm(FlaskForm):
    """A field to pick new studies for access."""

    choices = MultiCheckboxField("Access", coerce=int)


class RemoveAccessForm(FlaskForm):
    """A field to pick studies for which to remove access."""

    choices_to_remove = MultiCheckboxField("Remove access", coerce=int)


class ExcludeScansForm(FlaskForm):
    """A form for picking specific scans to exclude from a study."""

    choices_to_exclude = MultiCheckboxField("Exclude from study", coerce=dumps)


class IncludeScansForm(FlaskForm):
    """A form for picking specific scans to include from a study."""

    choices_to_include = MultiCheckboxField("Include in study", coerce=dumps)


class ExplicitCfmm2tarForm(FlaskForm):
    """A form for picking specific scans to include in a cfmm2tar run."""

    choices_to_run = MultiCheckboxField(
        "Include in cfmm2tar run", coerce=dumps
    )
