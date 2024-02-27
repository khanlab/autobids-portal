"""Forms to be used in some views."""
from __future__ import annotations

from functools import lru_cache
from json import dumps
from pathlib import Path

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    widgets,
)
from wtforms.fields.html5 import DateField, EmailField, IntegerField
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Optional,
    ValidationError,
)

from autobidsportal.models import ExplicitPatient, GlobusUsername, Study, User

CHOICES_FAMILIARITY = [
    ("1", "Not familiar at all"),
    ("2", "Have heard of it"),
    ("3", "Have used of it"),
    ("4", "Used it regularly"),
    ("5", "I consider myself an expert"),
]


@lru_cache
def get_default_bidsignore() -> str:
    """Read the default bidsignore file.

    Returns
    -------
    str
        Contents of bidsignore file
    """
    with (Path(__file__).parent / "resources" / "bidsignore.default").open(
        encoding="utf-8",
    ) as bidsignore_file:
        return bidsignore_file.read()

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


def _gen_familiarity_field(label: str) -> SelectField:
    """Generate familiarty selections.

    Parameters
    ----------
    label
        String representation of choice

    Returns
    -------
    SelectField
        User selection field
    """
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


def unique_email(_, email: str):
    """Check that no user with this email address exists.

    Parameters
    ----------
    email
        User email address

    Raises
    ------
    ValidationError
        If email address is already registered to an account

    """
    if (
        User.query.filter_by(email=email.data).one_or_none()  # pyright: ignore
        is not None
    ):
        msg = (
            "There is already an account using this email address. Please use "
            "a different email address."
        )
        raise ValidationError(
            msg,
        )


class RegistrationForm(FlaskForm):
    """A form for registering new users."""

    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), unique_email],
    )
    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password",
        validators=[DataRequired(), EqualTo("password")],
    )
    submit = SubmitField("Register")


class GenResetForm(FlaskForm):
    """A form for generating a reset password workflow."""

    email = EmailField(
        "Your email address",
        validators=[DataRequired()],
    )
    submit = SubmitField("Reset password")


class ResetPasswordForm(FlaskForm):
    """A form for resetting a user's password."""

    password = PasswordField("Password", validators=[DataRequired()])
    password2 = PasswordField(
        "Repeat Password",
        validators=[DataRequired(), EqualTo("password")],
    )
    submit = SubmitField("Reset password")


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
        "scanned multiple times)? If so, check the box below:",
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
        '"Principal" or "PI" identifier for this study below:',
        validators=[Optional()],
    )

    project_name = StringField(
        'What is the "Project Name" identifier for this study?:',
        validators=[DataRequired()],
    )

    dataset_name = StringField(
        'The name for your BIDS dataset will by default be the "Project '
        'Name". If you wish to override this, please enter a new name '
        "below (optional):",
        validators=[Optional()],
    )

    sample = DateField(
        "Please enter the scan date for this example session:",
        format="%Y-%m-%d",
        validators=[Optional()],
    )

    retrospective_data = BooleanField(
        "Does this study have retrospective (previously acquired) data to "
        "convert? If so, check the box below.:",
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

    def gen_study(self) -> Study:
        """Generate a study from this form.

        Returns
        -------
        Study
            Study object containing project and user metadata information
        """
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
            if self.dataset_name.data
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
    heuristic = TextAreaField("Custom heuristic contents")
    subj_expr = StringField("Tar2bids Patient Name Search String")
    bidsignore = TextAreaField("Custom .bidsignore contents")
    deface = BooleanField("Enable T1w image defacing?")
    patient_str = StringField("DICOM PatientName Identifier")
    patient_re = StringField(
        "Regular expression to match with returned PatientNames",
    )
    excluded_patients = MultiCheckboxField(
        "Excluded Patient StudyInstanceUIDs",
    )
    newly_excluded = StringField("New StudyInstanceUID to exclude")
    included_patients = MultiCheckboxField(
        "Included Patient StudyInstanceUIDs",
    )
    newly_included = StringField("New StudyInstanceUID to include")
    users_authorized = MultiCheckboxField(
        "Users With Access",
        coerce=int,  # pyright: ignore
    )
    custom_ria_url = StringField("Custom RIA URL")
    globus_usernames = MultiCheckboxField(
        "Globus identities with access to dataset archives",
    )
    new_globus_username = StringField("New Globus identity to grant access")

    def defaults_from_study(
        self,
        study: Study,
        principals: list[tuple[str, str]],
        users: list[User],
    ):
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
        self.heuristic.default = (
            get_default_heuristic()
            if study.custom_heuristic is None
            else study.custom_heuristic
        )
        if study.subj_expr is None:
            self.subj_expr.default = "*_{subject}"
        else:
            self.subj_expr.default = study.subj_expr
        self.deface.default = study.deface
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
            for patient in study.explicit_patients  # pyright: ignore
            if not patient.included
        ]
        self.excluded_patients.default = [
            patient.study_instance_uid
            for patient in study.explicit_patients  # pyright: ignore
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
            for patient in study.explicit_patients  # pyright: ignore
            if patient.included
        ]
        self.included_patients.default = [
            patient.study_instance_uid
            for patient in study.explicit_patients  # pyright: ignore
            if patient.included
        ]
        self.newly_included.default = ""
        self.users_authorized.choices = [
            (user.id, user.email) for user in users
        ]
        self.users_authorized.default = [
            user.id for user in study.users_authorized  # pyright: ignore
        ]
        self.custom_ria_url.default = (
            study.custom_ria_url if study.custom_ria_url is not None else ""
        )
        self.globus_usernames.choices = [
            (username.id, username.username)
            for username in study.globus_usernames  # pyright: ignore
        ]
        self.globus_usernames.default = [
            username.id
            for username in study.globus_usernames  # pyright: ignore
        ]
        self.new_globus_username.default = ""
        self.bidsignore.default = (
            get_default_bidsignore()
            if study.custom_bidsignore is None
            else study.custom_bidsignore
        )

        self.process()  # pyright: ignore

    def update_study(
        self,
        study: Study,
        *,
        user_is_admin: bool = False,
    ) -> tuple[
        Study,
        list[ExplicitPatient],
        list[ExplicitPatient],
        list[int | None],
    ]:
        """Process updates to a study from this form.

        Parameters
        ----------
        study
            The study to update

        user_is_admin
            True if the user updating is an administrator.

        Returns
        -------
        tuple[Study, list[ExplicitPatient], list[ExplicitPatient], list[int | None]]
            A tuple containing the updated study, a list of new
            ExplicitPatients to add, a list of existing ExplicitPatients to
            delete, and a list of IDs of users to add to the authorized list.
        """
        to_add: list[ExplicitPatient] = []
        to_delete: list[ExplicitPatient] = []
        ids_authorized: list[int | None] = (
            [int(user) for user in self.users_authorized.data]
            if self.users_authorized.data
            else []
        )

        # If new globus user
        if self.new_globus_username.data:
            to_add.append(
                GlobusUsername(
                    study_id=study.id,
                    username=self.new_globus_username.data,
                ),
            )
        study.sample = (
            self.example_date.data if self.example_date.data else None
        )

        # If retrospective study
        if self.retrospective_data.data:
            study.retrospective_data = True
            study.retrospective_start = self.retrospective_start.data
            study.retrospective_end = self.retrospective_end.data
        else:
            study.retrospective_data = False
            study.retrospective_start = None
            study.retrospective_end = None

        # If user not admin
        if not user_is_admin:
            return study, to_add, to_delete, ids_authorized

        study.principal = self.pi_name.data
        study.project_name = self.project_name.data
        study.dataset_name = self.dataset_name.data
        study.custom_heuristic = self.heuristic.data
        study.subj_expr = self.subj_expr.data
        study.deface = self.deface.data
        study.patient_str = self.patient_str.data
        study.patient_name_re = self.patient_re.data
        study.custom_bidsignore = self.bidsignore.data
        for explicit_patient in study.explicit_patients:  # pyright: ignore
            if (
                explicit_patient.included
                and (
                    explicit_patient.study_instance_uid
                    not in self.included_patients.data
                )
            ) or (
                (not explicit_patient.included)
                and (
                    explicit_patient.study_instance_uid
                    not in self.excluded_patients.data
                )
            ):
                to_delete.append(explicit_patient)

        # "New" participants to exclude
        if self.newly_excluded.data:
            to_add.append(
                ExplicitPatient(
                    study_id=study.id,
                    study_instance_uid=self.newly_excluded.data,
                    included=False,
                ),
            )

        # Include new participant to study
        if self.newly_included.data:
            to_add.append(
                ExplicitPatient(
                    study_id=study.id,
                    study_instance_uid=self.newly_included.data,
                    included=True,
                ),
            )

        study.active = self.active.data
        study.update_custom_ria_url(
            self.custom_ria_url.data if self.custom_ria_url.data else None,
        )

        for username in study.globus_usernames:  # pyright: ignore
            if (
                str(username.id)
                not in self.globus_usernames.data  # pyright: ignore
            ):
                to_delete.append(username)

        return study, to_add, to_delete, ids_authorized


class Tar2bidsRunForm(FlaskForm):
    """Form for choosing which tar files to BIDSify."""

    tar_files = MultiCheckboxField(
        "Tar files to use",
        coerce=int,  # pyright: ignore
    )


class AccessForm(FlaskForm):
    """A field to pick new studies for access."""

    choices = MultiCheckboxField("Access", coerce=int)  # pyright: ignore


class RemoveAccessForm(FlaskForm):
    """A field to pick studies for which to remove access."""

    choices_to_remove = MultiCheckboxField(
        "Remove access",
        coerce=int,  # pyright: ignore
    )


class ExcludeScansForm(FlaskForm):
    """A form for picking specific scans to exclude from a study."""

    choices_to_exclude = MultiCheckboxField(
        "Exclude from study",
        coerce=dumps,  # pyright: ignore
    )


class IncludeScansForm(FlaskForm):
    """A form for picking specific scans to include from a study."""

    choices_to_include = MultiCheckboxField(
        "Include in study",
        coerce=dumps,  # pyright: ignore
    )


class ExplicitCfmm2tarForm(FlaskForm):
    """A form for picking specific scans to include in a cfmm2tar run."""

    choices_to_run = MultiCheckboxField(
        "Include in cfmm2tar run",
        coerce=dumps,  # pyright: ignore
    )
