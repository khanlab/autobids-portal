"""All routes in the portal are defined here."""
from __future__ import annotations

import tempfile
import uuid
from datetime import datetime
from json import dumps, loads
from pathlib import Path
from typing import NoReturn

import flask_excel as excel
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import desc
from werkzeug.urls import url_parse
from werkzeug.wrappers.response import Response

from autobidsportal.datalad import (
    RiaDataset,
    delete_all_content,
    delete_tar_file,
    rename_tar_file,
)
from autobidsportal.dateutils import TIME_ZONE
from autobidsportal.dcm4cheutils import Dcm4cheError
from autobidsportal.dicom import get_study_records
from autobidsportal.email import send_email
from autobidsportal.forms import (
    DEFAULT_HEURISTICS,
    AccessForm,
    BidsForm,
    ExcludeScansForm,
    ExplicitCfmm2tarForm,
    GenResetForm,
    IncludeScansForm,
    LoginForm,
    RegistrationForm,
    RemoveAccessForm,
    ResetPasswordForm,
    StudyConfigForm,
    Tar2bidsRunForm,
)
from autobidsportal.models import (
    Cfmm2tarOutput,
    DataladDataset,
    DatasetType,
    ExplicitPatient,
    Principal,
    Study,
    Task,
    User,
    db,
)
from autobidsportal.ssh import remove_zip_files

portal_blueprint = Blueprint(
    "portal_blueprint",
    __name__,
    template_folder="templates",
)


def check_current_authorized(study: Study):
    """Check that the current_user is authorized to view this study.

    Parameters
    ----------
    study
        Study to check for user authorization
    """
    if (not current_user.admin) and (  # pyright: ignore
        current_user not in study.users_authorized
    ):
        abort(404)


@portal_blueprint.route("/", methods=["GET"])
@portal_blueprint.route("/index", methods=["GET"])
def index() -> str:
    """Render a splash page to describe autobids.

    Returns
    -------
    str
        Rendered path for homepage / index.html
    """
    return render_template("index.html")


@portal_blueprint.route("/getting-started", methods=["GET"])
def getting_started() -> str:
    """Render a page with getting started instructions.

    Returns
    -------
    str
        Rendered path for getting staged page
    """
    return render_template("getting_started.html")


@portal_blueprint.route("/new", methods=["GET", "POST"])
def new_study() -> str | Response:
    """Provide users with a survey form to fill (new study page).

    If the Principal table is not empty, the principal names are added to
    the principal dropdown in the form. Submitter information and their
    answer is added to the database.

    Returns
    -------
    str | Response
        Rendered path to survey or refresh page if valid submission of form
    """
    form = BidsForm()
    principal_names = [
        (p.principal_name, p.principal_name)
        for p in db.session.query(Principal).all()  # pyright: ignore
    ]
    form.principal.choices = principal_names
    form.principal.choices.insert(0, ("Other", "Other"))

    if form.validate_on_submit():
        study = form.gen_study()
        db.session.add(study)  # pyright: ignore
        db.session.commit()  # pyright: ignore

        flash(
            "Thanks, the survey has been submitted! "
            "If you haven't already, please add 'bidsdump' as an authorized user to "
            "your study on the CFMM DICOM server.",
        )
        send_email(
            "New study request",
            (
                f"A new request has been submitted by {form.name.data}"
                f" ({form.email.data}). ID: {study.id}"
            ),
            additional_recipients=[
                admin.email for admin in User.query.filter_by(admin=True).all()
            ],
        )

        return redirect(url_for("portal_blueprint.new_study"))
    return render_template("survey.html", form=form)


@portal_blueprint.route("/login", methods=["GET", "POST"])
def login() -> str | Response:
    """User login page.

    Returns
    -------
    str | Response
        Rendered home page is user is authenticated or credentials valid,
        login page if invalid credentials or login page if user not logged in
    """
    if current_user.is_authenticated:  # pyright: ignore
        return redirect(url_for("portal_blueprint.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password")
            return redirect(url_for("portal_blueprint.login"))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if (not next_page) or url_parse(next_page).netloc:
            next_page = url_for("portal_blueprint.index")

        return redirect(next_page)
    return render_template("login.html", title="Sign In", form=form)


@portal_blueprint.route("/register", methods=["GET", "POST"])
def register() -> str | Response:
    """User registration page.

    Returns
    -------
    str | Response
        Rendered registration page, or if user successfully registers, they
        are redirected to the login page
    """
    if current_user.is_authenticated:  # pyright: ignore
        return redirect(url_for("portal_blueprint.index"))
    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(email=form.email.data, admin=False)  # pyright: ignore
        user.set_password(form.password.data)

        db.session.add(user)  # pyright: ignore
        db.session.commit()  # pyright: ignore
        current_app.logger.info("New user %i registered.", user.id)
        flash("Congratulations, you are now a registered user!")

        return redirect(url_for("portal_blueprint.login"))
    return render_template("register.html", title="Register", form=form)


@portal_blueprint.route("/reset", methods=["GET", "POST"])
def gen_reset() -> str:
    """Generate a workflow to reset a user's password.

    Returns
    -------
    str
        Rendered page for user to reset their password
    """
    form = GenResetForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).one_or_none()
        exists = False
        # If email is found to be associated with a user
        if user is not None:
            for key in current_app.redis.scan_iter(  # pyright: ignore
                match="reset_*",
            ):
                # If there is ongoing process within reset time frame
                if current_app.redis.get(key) == email:  # pyright: ignore
                    exists = True
                    current_app.logger.info(
                        "Found existing key for user %s. Key: %s.",
                        email,
                        key,
                    )
                    break
            # If no ongoing process, send user email with unique reset URL
            if not exists:
                uuid_reset = str(uuid.uuid4())
                key_reset = f"reset_{uuid_reset}"
                current_app.redis.set(  # pyright: ignore
                    key_reset,
                    email,
                    ex=10 * 60,
                )
                current_app.logger.info(
                    "Generated reset url for user %s. UUID: %s",
                    user.email,
                    uuid_reset,
                )
                root_url = current_app.config["ROOT_URL"]
                sub_url = url_for(
                    "portal_blueprint.reset_password",
                    uuid_reset=uuid_reset,
                )
                send_email(
                    "Autobids password reset",
                    (
                        "Please visit the following link to reset your "
                        "password. The link will expire in ten minutes.\n\n"
                        f"{root_url}{sub_url}\n\n"
                        "Ignore this email if it has been sent in error."
                    ),
                    additional_recipients=[email],
                )
        # No users are found associated with provided email
        else:
            current_app.logger.info(
                "Attempted reset for nonassociated email %s ignored.",
                email,
            )
        flash(
            "An email with further instructions has been sent if the "
            "provided email is associated with a user account.",
        )
    return render_template("gen_reset.html", form=form)


@portal_blueprint.route("/reset/<uuid_reset>", methods=["GET", "POST"])
def reset_password(uuid_reset: str) -> str | Response:
    """Reset a user's password, given a workflow has started.

    Parameters
    ----------
    uuid_reset
        Key associated with unique reset process

    Returns
    -------
    str | Response
        Renders reset password page, or redirects user to regenerate reset
        password URL
    """
    # Check if reset key is valid
    key_reset = f"reset_{uuid_reset}"
    if current_app.redis.exists(key_reset) < 1:  # pyright: ignore
        flash(
            "The reset password link is incorrect or has expired. Please "
            "resubmit your password reset request.",
        )
        return redirect(url_for("portal_blueprint.gen_reset"))

    form = ResetPasswordForm()
    email = current_app.redis.get(key_reset)  # pyright: ignore
    # If no user is found by email
    if (user := User.query.filter_by(email=email).one_or_none()) is None:
        flash(
            "This password reset link encountered an unexpected error. "
            "Please resubmit your password reset request.",
        )
        current_app.redis.delete(key_reset)  # pyright: ignore
        return redirect(url_for("portal_blueprint.gen_reset"))

    if form.validate_on_submit():
        new_password = form.password.data
        user.set_password(new_password)
        db.session.commit()  # pyright: ignore
        current_app.redis.delete(key_reset)  # pyright: ignore
        flash("Your password has been reset.")
        return redirect(url_for("portal_blueprint.login"))
    return render_template("reset_password.html", email=email, form=form)


@portal_blueprint.route("/admin", methods=["GET", "POST"])
@login_required
def user_list() -> str:
    """Obtain all registered users from the database.

    Returns
    -------
    str
        Renders main admin page with user info, available studies, and
        heuristics
    """
    if not current_user.admin:  # pyright: ignore
        abort(404)

    users = User.query.all()
    ria_url = current_app.config["DATALAD_RIA_URL"]
    archive_url = current_app.config["ARCHIVE_BASE_URL"]

    return render_template(
        "admin.html",
        title="Administration",
        users=users,
        ria_url=ria_url,
        archive_url=archive_url,
    )


@portal_blueprint.route("/admin/update_heuristics", methods=["POST"])
@login_required
def update_heuristics() -> str:
    """Launch an update heuristics task.

    Returns
    -------
    str
        Renders main admin page with user info, available studies, and
        heuristics
    """
    if not current_user.admin:  # pyright: ignore
        abort(404)

    Task.launch_task(
        "update_heuristics",
        "Manually triggered heuristic update",
        user=current_user,  # pyright: ignore
        timeout=1000,
    )
    current_app.logger.info("Update heuristic task launched.")
    flash("Currently updating heuristics... Give it a minute or two.")

    return user_list()


@portal_blueprint.route("/admin/<int:user_id>", methods=["GET", "POST"])
@login_required
def admin(user_id: int) -> str:
    """Exposes information about a specific registered user.

    A GET request shows a page with information about the user.

    A POST request alters some aspect of the user, then shows the same page.

    Parameters
    ----------
    user_id : int
        ID of the user to expose.

    Returns
    -------
    str
        Renders admin page with study authorization forms
    """
    if not current_user.admin:  # pyright: ignore
        abort(404)

    # Render access and removal forms
    form = AccessForm()
    removal_form = RemoveAccessForm()

    # Get all available studies
    all_studies = db.session.query(Study).all()  # pyright: ignore
    form.choices.choices = [
        (study.id, f"{study.principal}^{study.project_name}")
        for study in all_studies
    ]
    removal_form.choices_to_remove.choices = form.choices.choices

    user = User.query.get(user_id)
    if request.method == "POST":
        # Change admin status for a given user
        if "admin" in request.form:
            user.admin = request.form["admin"].lower() == "true"
            db.session.commit()  # pyright: ignore
            current_app.logger.info(
                "Changed user %i's admin status to %s",
                user.id,
                user.admin,
            )
        # If form valid, authorize user to selected studies
        if form.validate_on_submit():
            for study_id in form.choices.data:  # pyright: ignore
                print(study_id)
                study = Study.query.get(study_id)
                current_app.logger.info(
                    "Added user %i to study %i.",
                    user.id,
                    study.id,
                )
                if user not in study.users_authorized:
                    study.users_authorized.append(user)
            db.session.commit()  # pyright: ignore
        # If valid form, remove user authorization from selected studies
        if removal_form.validate_on_submit():
            for (
                study_id
            ) in removal_form.choices_to_remove.data:  # pyright: ignore
                study = Study.query.get(study_id)
                if user in study.users_authorized:
                    study.users_authorized.remove(user)
                    current_app.logger.info(
                        "Removed user %i from study %i",
                        user.id,
                        study.id,
                    )
            db.session.commit()  # pyright: ignore

    return render_template(
        "administration.html",
        title="Administration",
        form=form,
        removal_form=removal_form,
        user=user,
    )


@portal_blueprint.route("/results", methods=["GET"])
@login_required
def results() -> str:
    """Get responses and last login.

    Returns
    -------
    str
        Renders page with responses date and time current user was last logged
        in
    """
    last = current_user.last_seen  # pyright: ignore

    studies = (
        Study.query.all()
        if current_user.admin  # pyright: ignore
        else current_user.studies  # pyright: ignore
    )
    studies = sorted(
        studies,
        key=lambda x: x.submission_date,
        reverse=True,
    )

    return render_template(
        "results.html",
        title="Responses",
        answers=studies,
        last=last,
    )


@portal_blueprint.route("/results/<int:study_id>", methods=["GET"])
@login_required
def answer_info(study_id: int):
    """Obtain complete survey response based on the submission id.

    Parameters
    ----------
    study_id
        Study ID to query survey response of

    Returns
    -------
    str
        Render survery response page of provided study id

    """
    # Retrieve study id and check current user is authorized
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    # Query database to retrieve tasks and files associated with cfmm2tar
    cfmm2tar_tasks = (
        Task.query.filter_by(study_id=study_id, name="run_cfmm2tar")
        .order_by(desc("start_time"))
        .all()
    )
    cfmm2tar_files = study.cfmm2tar_outputs
    cfmm2tar_file_names = [
        Path(cfmm2tar_file.tar_file).name for cfmm2tar_file in cfmm2tar_files
    ]

    # Query database to retrieve tasks and files associated with tar2bids
    tar2bids_tasks = (
        Task.query.filter_by(study_id=study_id, name="run_tar2bids")
        .order_by(desc("start_time"))
        .all()
    )
    tar2bids_files = study.tar2bids_outputs

    # Dump dataset content to dictionary
    bids_dict = (
        study.dataset_content
        if study.dataset_content is not None
        else {"files": [], "dirs": []}
    )
    json_filetree = dumps(bids_dict)

    # Query database for raw dataset archives
    archive_dataset = DataladDataset.query.filter_by(
        study_id=study_id,
        dataset_type=DatasetType.RAW_DATA,
    ).one_or_none()
    archive_exists = bool(
        (archive_dataset) and (archive_dataset.dataset_archives),
    )

    # Render form for running tar2bids and handle processing
    form = Tar2bidsRunForm()
    form.tar_files.choices = [
        (tar_file.id, "Yes") for tar_file in cfmm2tar_files
    ]
    form.tar_files.default = []
    form.process()  # pyright: ignore

    return render_template(
        "answer_info.html",
        title="Response",
        submitter_answer=study,
        cfmm2tar_tasks=cfmm2tar_tasks,
        button_id=study_id,
        form_data=sorted(
            zip(form.tar_files, cfmm2tar_file_names, cfmm2tar_files),
            key=lambda item: item[1],
        ),
        tar2bids_tasks=tar2bids_tasks,
        tar2bids_files=tar2bids_files,
        json_filetree=json_filetree,
        archive_exists=archive_exists,
    )


@portal_blueprint.route(
    "/results/<int:study_id>/demographics",
    methods=["GET"],
)
def study_demographics(study_id: int) -> str:
    """Render page with information about a study's submitter.

    Parameters
    ----------
    study_id
        Study ID to query demographics from

    Returns
    -------
    str
        Render page with study demographics
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    return render_template("study_demographics.html", study=study)


@portal_blueprint.route(
    "/results/<int:study_id>/config",
    methods=["GET", "POST"],
)
@login_required  # pylint: disable=too-many-statements,too-many-branches
def study_config(study_id: int) -> str:
    """Page to display and edit study config.

    Parameters
    ----------
    study_id
        Study ID to query demographics from

    Returns
    -------
    str
        Render page for study config with option to edit
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    form = StudyConfigForm()
    if request.method == "POST":
        study, to_add, to_delete, users_authorized = form.update_study(
            study,
            user_is_admin=current_user.admin,  # pyright: ignore
        )
        study.users_authorized = [  # pyright: ignore
            User.query.get(user_id) for user_id in users_authorized
        ]

        for patient in to_add:
            db.session.add(patient)  # pyright: ignore

        for patient in to_delete:
            db.session.delete(patient)  # pyright: ignore

        current_app.logger.info("Updated study %i config", study.id)
        db.session.commit()  # pyright: ignore

    available_heuristics = sorted(
        [
            (str(heuristic_path), f"{heuristic_path.name} (git)")
            for heuristic_path in (
                Path(current_app.config["HEURISTIC_REPO_PATH"])
                / current_app.config["HEURISTIC_DIR_PATH"]
            ).iterdir()
        ]
        + [
            (heuristic, f"{heuristic} (container)")
            for heuristic in DEFAULT_HEURISTICS
        ],
        key=lambda option: option[1].lower(),
    )

    principal_names = [
        p.principal_name
        for p in db.session.query(Principal).all()  # pyright: ignore
    ]
    if study.principal not in principal_names:
        principal_names.insert(0, study.principal)

    form.defaults_from_study(
        study,
        principal_names,
        available_heuristics,
        User.query.all(),
    )

    return render_template(
        "study_config.html",
        form=form,
        study=study,
        admin_disable=not current_user.admin,  # pyright: ignore
    )


@portal_blueprint.route("/results/<int:study_id>/cfmm2tar", methods=["POST"])
@login_required
def run_cfmm2tar(study_id: int):
    """Launch cfmm2tar task and refresh answer_info.html.

    Parameters
    ----------
    study_id
        Study ID to query demographics from

    Returns
    -------
    str
        Render page to launch cfmm2tar task
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)
    if (
        len(
            Task.query.filter_by(
                study_id=study_id,
                name="run_cfmm2tar",
                complete=False,
            ).all(),
        )
        > 0
    ):
        flash("An Cfmm2tar run is currently in progress")
        return answer_info(study_id)
    if not study.active:
        return answer_info(study_id)

    form = ExplicitCfmm2tarForm()

    explicit_scans = (
        [
            loads(loads(val_json))
            for val_json in form.choices_to_run.data  # pyright: ignore
        ]
        if form.choices_to_run.data not in [None, []]
        else None
    )
    current_app.task_queue.enqueue(  # pyright: ignore
        "autobidsportal.tasks.check_tar_files",
        study_id,
        explicit_scans=explicit_scans,
        user_id=current_user.id,  # pyright: ignore
    )
    current_app.logger.info("Launched cfmm2tar for study %i", study_id)
    db.session.commit()  # pyright: ignore

    return answer_info(study_id)


@portal_blueprint.route(
    "/results/<int:study_id>/cfmm2tar/<int:cfmm2tar_id>/delete",
    methods=["GET"],
)
@portal_blueprint.route(
    "/results/<int:study_id>/cfmm2tar/<int:cfmm2tar_id>",
    methods=["DELETE"],
)
@login_required
def delete_cfmm2tar(study_id: int, cfmm2tar_id: int):
    """Delete a single tar file.

    Parameters
    ----------
    study_id
        Study ID to query demographics from

    cfmm2tar_id
        ID associated with cfmm2tar output tar file to be deleted

    Returns
    -------
    str
        Render page with survey response based on study id
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    if not study.active:
        return answer_info(study_id)

    cfmm2tar_output = Cfmm2tarOutput.query.get(cfmm2tar_id)
    if (cfmm2tar_output is not None) and (
        cfmm2tar_output.study_id == study_id
    ):
        delete_tar_file(study_id, cfmm2tar_output.tar_file)
        db.session.delete(cfmm2tar_output)  # pyright: ignore
        db.session.commit()  # pyright: ignore

    return answer_info(study_id)


@portal_blueprint.route(
    "/results/<int:study_id>/cfmm2tar/<int:cfmm2tar_id>/rename",
    methods=["POST"],
)
@login_required
def rename_cfmm2tar(study_id: int, cfmm2tar_id: int) -> str:
    """Rename a single tar file.

    Parameters
    ----------
    study_id
        Study ID to query demographics from

    cfmm2tar_id
        ID associated with cfmm2tar output tar file to be renamed

    Returns
    -------
    str
        Render page with survey response based on study id
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    if not study.active:
        return answer_info(study_id)

    current_app.logger.info(
        "Attempting to rename cfmm2tar output %s",
        cfmm2tar_id,
    )
    cfmm2tar_output = Cfmm2tarOutput.query.get_or_404(cfmm2tar_id)
    current_app.logger.info(
        "Checking that cfmm2tar output %s belongs to study %s",
        cfmm2tar_id,
        study_id,
    )

    # If cfmm2tar study id does not match provided
    if cfmm2tar_output.study_id != study_id:
        abort(404)

    new_name = request.form["new_name"]
    current_app.logger.info(
        "Renaming cfmm2tar output %s to %s.",
        cfmm2tar_output.tar_file,
        new_name,
    )
    rename_tar_file(study_id, cfmm2tar_output.tar_file, new_name)
    cfmm2tar_output.tar_file = new_name
    db.session.commit()  # pyright: ignore

    return answer_info(study_id)


@portal_blueprint.route(
    "/results/<int:study_id>/tar2bids/archive",
    methods=["GET"],
)
@login_required
def archive_tar2bids(study_id: int) -> str:
    """Archive a study's BIDS directory.

    Parameters
    ----------
    study_id
        Associated study id to be archived

    Returns
    -------
    str
        Render page with survey response based on study id
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    if not study.active:
        return answer_info(study_id)

    if (
        len(
            Task.query.filter_by(
                study_id=study_id,
                complete=False,
            ).all(),
        )
        > 0
    ):
        flash("An task is currently in progress for this study.")
    else:
        Task.launch_task(
            "archive_raw_data",
            f"dataset archive for study {study_id}",
            study_id,
            user=current_user,  # pyright: ignore
            timeout=current_app.config["ARCHIVE_TIMEOUT"],
            study_id=study_id,
        )
        current_app.logger.info(
            "Launched archive task for study %i",
            study_id,
        )
        db.session.commit()  # pyright: ignore

    return answer_info(study_id)


@portal_blueprint.route(
    "/results/<int:study_id>/tar2bids/delete",
    methods=["GET"],
)
@portal_blueprint.route("/results/<int:study_id>/tar2bids", methods=["DELETE"])
@login_required
def delete_tar2bids(study_id: int) -> str:
    """Delete a study's BIDS directory.

    Parameters
    ----------
    study_id
        Associated study id of BIDS directory to be deleted

    Returns
    -------
    str
        Render page with survey response based on study id
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    if not study.active:
        return answer_info(study_id)

    dataset = DataladDataset.query.filter_by(
        study_id=study_id,
        dataset_type=DatasetType.RAW_DATA,
    ).first_or_404()

    with tempfile.TemporaryDirectory(
        dir=current_app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as bids_dir, RiaDataset(
        bids_dir,
        dataset.ria_alias,
        ria_url=dataset.custom_ria_url,
    ) as path_dataset:
        # Delete items within dataset
        delete_all_content(path_dataset)
        study.dataset_content = None
        dataset.cfmm2tar_outputs = []

        # Delete archives from db
        for archive in dataset.dataset_archives:
            db.session.delete(archive)  # pyright: ignore

        # Delete all zip files
        remove_zip_files(
            current_app.config["ARCHIVE_BASE_URL"].split(":")[0],
            current_app.config["ARCHIVE_BASE_URL"].split(":")[1]
            + f"/{dataset.ria_alias}",
        )

        db.session.commit()  # pyright: ignore

    return answer_info(study_id)


@portal_blueprint.route("/results/<int:study_id>/tar2bids", methods=["POST"])
@login_required
def run_tar2bids(study_id: int) -> str:
    """Launch tar2bids task and refresh answer_info.html.

    Parameters
    ----------
    study_id
        Associated study id to launch tar2bids task for

    Returns
    -------
    str
        Render page with survey response based on study id
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    if not study.active:
        return answer_info(study_id)

    form = Tar2bidsRunForm()
    tar_files = [
        Cfmm2tarOutput.query.get_or_404(tar_file_id)
        for tar_file_id in form.tar_files.data  # pyright: ignore
    ]
    tar_files = [
        tar_file for tar_file in tar_files if tar_file.study_id == study_id
    ]

    if (
        len(
            Task.query.filter_by(
                study_id=study_id,
                name="run_tar2bids",
                complete=False,
            ).all(),
        )
        > 0
    ):
        flash("An tar2bids run is currently in progress")
    else:
        Task.launch_task(
            "run_tar2bids",
            f"tar2bids for study {study_id}",
            study_id,
            [tar_file.id for tar_file in tar_files],
            user=current_user,
            study_id=study_id,
            timeout=current_app.config["TAR2BIDS_TIMEOUT"],
        )
        current_app.logger.info(
            "Launched tar2bids for study %i with files %s",
            study_id,
            [tar_file.tar_file for tar_file in tar_files],
        )
        db.session.commit()  # pyright: ignore

    return answer_info(study_id)


def update_scanner(scanner: str) -> str:
    """Parse scanner data into something readable.

    Parameters
    ----------
    scanner
        Type of scanner data

    Returns
    -------
    str
        Field strength of scanner, one of [3T, 7T]
    """
    return "3T" if scanner == "type1" else "7T"


def update_familiarity(familiarity: str) -> str:
    """Parse familiarity value into human-readable description.

    Parameters
    ----------
    familiarity
        String representation of integer value for familiarity

    Returns
    -------
    str
        String representation of familiarity
    """
    familiarity_map = {
        "1": "Not familiar at all",
        "2": "Have heard of it",
        "3": "Have used it before",
        "4": "Used it regularly",
        "5": "I consider myself an expert",
    }

    return familiarity_map[familiarity]


def update_date(date):
    """Parse date into string."""
    return date.date() if date is not None else date


def update_bool(bool_str: str) -> str:
    """Parse boolean int string into Yes/No.

    Parameters
    ----------
    bool_str
        String representation ('0' or '1') of boolean response

    Returns
    -------
    str
        'Yes' or 'No' depending on boolean input
    """
    return "Yes" if bool_str == "1" else "No"


@portal_blueprint.route("/results/download", methods=["GET"])
@login_required
def download() -> Response:
    """Download csv containing all the survey response.

    Returns
    -------
    Response
        Object containing generated excel data
    """
    response_list = (
        Study.query.all()
        if current_user.admin  # pyright: ignore
        else current_user.studies  # pyright: ignore
    )
    file_name = "Response_report"

    csv_list = [
        [file_name],
        [
            "Submitter Name",
            "Submitter Email",
            "Status",
            "Scanner",
            "Number of Scans",
            "Study Type",
            "Bids Familiarity",
            "Bids App Familiarity",
            "Python Familiarity",
            "Linux Familiarity",
            "Bash Familiarity",
            "HPC Familiarity",
            "OPENNEURO Familiarity",
            "CBRAIN Familiarity",
            "Principal",
            "Project Name",
            "Dataset Name",
            "Sample Date",
            "Retrospective Data",
            "Retrospective Data Start Date",
            "Retrospective Data End Date",
            "Consent",
            "Comment",
        ],
    ]

    for response in response_list:
        csv_list.append(
            [
                response.submitter_name,
                response.submitter_email,
                response.status.capitalize(),
                update_scanner(response.scanner),
                response.scan_number,
                update_bool(response.study_type),
                update_familiarity(response.familiarity_bids),
                update_familiarity(response.familiarity_bidsapp),
                update_familiarity(response.familiarity_python),
                update_familiarity(response.familiarity_linux),
                update_familiarity(response.familiarity_bash),
                update_familiarity(response.familiarity_hpc),
                update_familiarity(response.familiarity_openneuro),
                update_familiarity(response.familiarity_cbrain),
                response.principal,
                response.project_name,
                response.dataset_name,
                update_date(response.sample),
                update_bool(response.retrospective_data),
                update_date(response.retrospective_start),
                update_date(response.retrospective_end),
                update_bool(response.consent),
                response.comment,
            ],
        )

    # Type hinted to return (Unknown | None), but docstring suggests
    # return type should be Response
    return excel.make_response_from_array(  # pyright: ignore
        csv_list,
        "csv",
        file_name=file_name,
    )


@portal_blueprint.route(
    "results/<int:study_id>/dicom/process",
    methods=["POST"],
)
@login_required
def process_dicom_form(study_id: int) -> str | NoReturn:
    """Pass off processing to run cfmm2tar or update exclusions.

    Parameters
    ----------
    study_id
        Id to query information from or run cfmm2tar

    Returns
    -------
    str
        If excluded UIDs are to be updated or cfmm2tar is to be launched,
        otherwise cancel if study not found
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    if "update-exclusions" in request.form:
        return update_exclusions(study_id)

    if "run-cfmm2tar" in request.form:
        return run_cfmm2tar(study_id)

    return abort(404)


@portal_blueprint.route("results/<int:study_id>/exclusions", methods=["POST"])
@login_required
def update_exclusions(study_id: int) -> str:
    """Update the excluded UIDs for a study.

    Parameters
    ----------
    study_id
        Associated study id to update excluded UIDs

    Returns
    -------
    str
        Returns all dicoms associated with study id
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    # Participants to be excluded
    form_exclude = ExcludeScansForm()
    for val_json in form_exclude.choices_to_exclude.data:  # pyright: ignore
        val = loads(loads(val_json))
        old_uid = ExplicitPatient.query.filter_by(
            study_instance_uid=val["StudyInstanceUID"],
        ).one_or_none()
        if old_uid is not None:
            db.session.delete(old_uid)  # pyright: ignore

        excluded_uid = ExplicitPatient(
            study_id=study.id,
            study_instance_uid=val["StudyInstanceUID"],
            patient_name=val["PatientName"],
            dicom_study_id=val["StudyID"],
            included=False,
        )
        db.session.add(excluded_uid)  # pyright: ignore
        db.session.commit()  # pyright: ignore

    # Participants to be included
    form_include = IncludeScansForm()
    for val_json in form_include.choices_to_include.data:  # pyright: ignore
        val = loads(loads(val_json))
        old_uid = ExplicitPatient.query.filter_by(
            study_instance_uid=val["StudyInstanceUID"],
        ).one_or_none()
        if old_uid is not None:
            break
        included_uid = ExplicitPatient(
            study_id=study.id,
            study_instance_uid=val["StudyInstanceUID"],
            patient_name=val["PatientName"],
            dicom_study_id=val["StudyID"],
            included=True,
        )
        db.session.add(included_uid)  # pyright: ignore
        db.session.commit()  # pyright: ignore

    return dicom_verify(study_id, "description")


@portal_blueprint.route(
    "/results/<int:study_id>/dicom/<string:method>",
    methods=["GET"],
)
@login_required
def dicom_verify(study_id: int, method: str):
    """Get all DICOM results for a specific study.

    Parameters
    ----------
    study_id
        Associated study id to update excluded UIDs

    method
        One of "date", "description" or "both" to query study ids by

    Returns
    -------
    str
        Renders page with DICOM results for a given study
    """
    study = Study.query.get_or_404(study_id)
    check_current_authorized(study)

    study_info = f"{study.principal}^{study.project_name}"

    if method.lower() == "both":
        if study.sample is None:
            abort(404)
        description = study_info
        date = study.sample.date()
    elif method.lower() == "date":
        if study.sample is None:
            abort(404)
        description = None
        date = study.sample.date()
    elif method.lower() == "description":
        description = study_info
        date = None
    else:
        abort(404)

    try:
        responses = get_study_records(
            study,
            date=date,
            description=description,
        )
    except Dcm4cheError as err:
        err_cause = (
            err.__cause__.stderr  # pyright: ignore
            if err.__cause__ is not None
            else ""  # pyright: ignore
        )
        current_app.logger.warning(
            "Failed to get DICOM info for study %i: %s",
            study_id,
            err,
        )
        return render_template(
            "dicom_error.html",
            err=err,
            err_cause=err_cause,
            title="DICOM Result Not Found",
        )

    # Generate forms for patient exclusion / inclusion, sorted by name
    sorted_responses = sorted(
        responses,
        key=lambda attr_dict: f'{attr_dict["PatientName"]}',
    )
    form_exclude = ExcludeScansForm()
    form_exclude.choices_to_exclude.choices = [
        (
            dumps(
                {
                    "StudyInstanceUID": response["StudyInstanceUID"],
                    "PatientName": response["PatientName"],
                    "StudyID": response["StudyID"],
                },
            ),
            "Exclude",
        )
        for response in sorted_responses
    ]

    form_include = IncludeScansForm()
    form_include.choices_to_include.choices = [
        (
            dumps(
                {
                    "StudyInstanceUID": response["StudyInstanceUID"],
                    "PatientName": response["PatientName"],
                    "StudyID": response["StudyID"],
                },
            ),
            "Include",
        )
        for response in responses
    ]

    # Generate form to run cfmm2tar
    form_cfmm2tar = ExplicitCfmm2tarForm()
    form_cfmm2tar.choices_to_run.choices = [
        (
            dumps(
                {
                    "StudyInstanceUID": response["StudyInstanceUID"],
                    "PatientName": response["PatientName"],
                },
            ),
            "Include in cfmm2tar",
        )
        for response in responses
    ]

    return render_template(
        "dicom.html",
        title="Dicom Result",
        dicom_response=sorted_responses,
        submitter_answer=study,
        form_exclude=form_exclude,
        form_include=form_include,
        form_cfmm2tar=form_cfmm2tar,
    )


@portal_blueprint.route("/logout", methods=["GET", "POST"])
def logout() -> Response:
    """Log out current user.

    Returns
    -------
    Response
        Redirect to homepage after logging user out
    """
    # Update last seen before logging out
    if current_user.is_authenticated:  # pyright: ignore
        current_user.last_seen = datetime.now(tz=TIME_ZONE)
        db.session.commit()  # pyright: ignore
    logout_user()

    return redirect(url_for("portal_blueprint.index"))


@portal_blueprint.route("/api/globus_users", methods=["GET"])
def list_globus_users() -> Response:
    """Return a JSON list of users.

    Returns
    -------
    Response
        Object containing list of globus users
    """
    path_base = current_app.config["ARCHIVE_BASE_URL"].split(":")[1]

    return jsonify(
        [
            {
                "id": dataset.study_id,
                "type": dataset.dataset_type.to_bids_str(),
                "path": f"{path_base}/{dataset.ria_alias}",
                "users": [
                    username.username
                    for username in dataset.study.globus_usernames
                ],
            }
            for dataset in DataladDataset.query.filter(
                DataladDataset.dataset_type.in_(
                    [DatasetType.RAW_DATA, DatasetType.DERIVED_DATA],
                ),
            ).all()
        ],
    )
