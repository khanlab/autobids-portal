"""All routes in the portal are defined here."""

from datetime import datetime
from smtplib import SMTPAuthenticationError

from flask import (
    current_app,
    Blueprint,
    render_template,
    flash,
    redirect,
    url_for,
    request,
    abort,
)
from flask_login import login_user, logout_user, current_user, login_required
from flask_mail import Mail, Message
import flask_excel as excel

from werkzeug.urls import url_parse
from autobidsportal.models import (
    db,
    User,
    Submitter,
    Answer,
    Principal,
    Task,
    Cfmm2tar,
    Tar2bids,
    Choice,
)
from autobidsportal.dcm4cheutils import gen_utils, Dcm4cheError
from autobidsportal.forms import (
    LoginForm,
    BidsForm,
    RegistrationForm,
    HeuristicForm,
    AccessForm,
    RemoveAccessForm,
)

portal_blueprint = Blueprint(
    "portal_blueprint", __name__, template_folder="templates"
)

mail = Mail()


@portal_blueprint.route("/", methods=["GET", "POST"])
@portal_blueprint.route("/index", methods=["GET", "POST"])
def index():
    """Provides a survey form for users to fill out.

    If the Principal table is not empty, the principal names are added to
    the principal dropdown in the form. Submitter information and their
    answer is added to the database.
    """
    form = BidsForm()
    principal_names = [
        (p.principal_name, p.principal_name)
        for p in db.session.query(Principal).all()
    ]
    form.principal.choices = principal_names
    form.principal.choices.insert(0, ("Other", "Other"))

    if form.validate_on_submit():

        submitter = Submitter(name=form.name.data, email=form.email.data)
        db.session.add(submitter)
        db.session.commit()

        answer = Answer(
            status=form.status.data,
            scanner=form.scanner.data,
            scan_number=form.scan_number.data,
            study_type=form.study_type.data,
            familiarity_bids=form.familiarity_bids.data,
            familiarity_bidsapp=form.familiarity_bidsapp.data,
            familiarity_python=form.familiarity_python.data,
            familiarity_linux=form.familiarity_linux.data,
            familiarity_bash=form.familiarity_bash.data,
            familiarity_hpc=form.familiarity_hpc.data,
            familiarity_openneuro=form.familiarity_openneuro.data,
            familiarity_cbrain=form.familiarity_cbrain.data,
            principal=form.principal.data,
            principal_other=form.principal_other.data,
            project_name=form.project_name.data,
            dataset_name=form.dataset_name.data,
            sample=form.sample.data,
            retrospective_data=form.retrospective_data.data,
            retrospective_start=form.retrospective_start.data,
            retrospective_end=form.retrospective_end.data,
            consent=form.consent.data,
            comment=form.comment.data,
            submitter=submitter,
        )

        db.session.add(answer)
        db.session.commit()

        if answer.principal_other != "":
            study_info = f"{answer.principal_other} {answer.project_name}"
        else:
            study_info = f"{answer.principal} {answer.project_name}"
        if Choice.query.filter_by(desc=study_info).all() == []:
            choice = Choice(desc=study_info)

            db.session.add(choice)
            db.session.commit()

        flash("Thanks, the survey has been submitted!")

        if current_app.config["MAIL_ENABLED"]:
            subject = "A new request has been submitted by %s" % (
                answer.submitter.name
            )
            sender = current_app.config["MAIL_USERNAME"]
            recipients = current_app.config["MAIL_RECIPIENTS"]

            msg = Message(
                subject=subject,
                body="A new request has been submitted. Please login to "
                + "see the submitter's response",
                sender=sender,
                recipients=recipients.split(),
            )
            mail.send(msg)

        return redirect(url_for("portal_blueprint.index"))
    return render_template("survey.html", form=form)


@portal_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Redirects user to login if they their email and password is valid."""
    if current_user.is_authenticated:
        return redirect(url_for("portal_blueprint.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password")
            return redirect(url_for("portal_blueprint.login"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("portal_blueprint.index")
        return redirect(next_page)
    return render_template("login.html", title="Sign In", form=form)


@portal_blueprint.route("/register", methods=["GET", "POST"])
def register():
    """Validates that provided email and password are valid.

    After the user is registered, they are redirected to login.
    """
    if current_user.is_authenticated:
        return redirect(url_for("portal_blueprint.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("portal_blueprint.login"))
    return render_template("register.html", title="Register", form=form)


@portal_blueprint.route("/admin", methods=["GET", "POST"])
@login_required
def user_list():
    """Obtains all the registered users from the database."""
    users = User.query.all()
    return render_template("admin.html", title="Administration", users=users)


@portal_blueprint.route("/admin/<int:user_id>", methods=["GET", "POST"])
@login_required
def admin(user_id):
    """Exposes information about a specific registered user.

    A GET request shows a page with information about the user.

    A POST request alters some aspect of the user, then shows the same page.

    Parameters
    ----------
    user_id : int
        ID of the user to expose.
    """
    form = AccessForm()
    removal_form = RemoveAccessForm()
    form.choices.choices = [
        (c.id, c.desc) for c in db.session.query(Choice).all()
    ]
    removal_form.choices_to_remove.choices = form.choices.choices
    user = User.query.get(user_id)
    if request.method == "POST":
        c_records = Choice.query.all()
        if "admin" in request.form:
            make_admin = request.form["admin"].lower() == "true"
            if make_admin:
                user.admin = True
                new_choice = [
                    choice
                    for choice in c_records
                    if choice not in user.access_to
                ]
                user.access_to.extend(new_choice)
            else:
                user.admin = False
                user.access_to = []
            db.session.commit()
        if form.validate_on_submit():
            for choice in c_records:
                if (
                    choice.id in form.choices.data
                    and choice not in user.access_to
                ):
                    user.access_to.append(choice)
            db.session.commit()
        if removal_form.validate_on_submit():
            for choice in c_records:
                if (
                    choice.id in removal_form.choices_to_remove.data
                    and choice in user.access_to
                ):
                    user.access_to.remove(choice)
            db.session.commit()

    return render_template(
        "administration.html",
        title="Administration",
        form=form,
        removal_form=removal_form,
        user=user,
    )


@portal_blueprint.route("/results", methods=["GET", "POST"])
@login_required
def results():
    """Get responses and the date and time the current user last logged in."""
    last = current_user.last_seen
    answers = []
    for choice in current_user.access_to:
        ans = Answer.query.filter_by(
            principal=choice.desc.rsplit(" ", 2)[0],
            project_name=choice.desc.rsplit(" ", 2)[1],
        ).all()
        if ans == []:
            ans = Answer.query.filter_by(
                principal_other=choice.desc.rsplit(" ", 2)[0],
                project_name=choice.desc.rsplit(" ", 2)[1],
            ).all()
        answers.extend(ans)

    answers = sorted(answers, key=lambda x: x.submission_date, reverse=True)

    return render_template(
        "results.html", title="Responses", answers=answers, last=last
    )


@portal_blueprint.route("/results/<int:answer_id>", methods=["GET"])
@login_required
def answer_info(answer_id):
    """Obtains complete survey response based on the submission id"""
    form = HeuristicForm()
    answer = Answer.query.get(answer_id)
    cfmm2tar_tasks = Task.query.filter_by(
        task_button_id=answer_id, description="Running cfmm2tar-"
    ).all()
    cfmm2tar_files = Cfmm2tar.query.filter_by(task_button_id=answer_id).all()
    tar2bids_tasks = Task.query.filter_by(
        task_button_id=answer_id, description="Running tar2bids-"
    ).all()
    tar2bids_files = Tar2bids.query.filter_by(task_button_id=answer_id).all()
    return render_template(
        "answer_info.html",
        title="Response",
        submitter_answer=answer,
        cfmm2tar_tasks=cfmm2tar_tasks,
        button_id=answer_id,
        cfmm2tar_files=cfmm2tar_files,
        tar2bids_tasks=tar2bids_tasks,
        tar2bids_files=tar2bids_files,
        form=form,
    )


@portal_blueprint.route("/results/<int:answer_id>/cfmm2tar", methods=["POST"])
@login_required
def run_cfmm2tar(answer_id):
    """Launch cfmm2tar task and refresh answer_info.html"""
    form = HeuristicForm()
    submitter_answer = Answer.query.get(answer_id)
    if current_user.get_task_in_progress("get_info_from_cfmm2tar"):
        flash("An Cfmm2tar run is currently in progress")
    else:
        current_user.launch_task(
            "get_info_from_cfmm2tar", ("Running cfmm2tar-")
        )
        db.session.commit()
    if current_app.config["MAIL_ENABLED"]:
        if submitter_answer.principal_other is None:
            principal_actual = submitter_answer.principal
        else:
            principal_actual = submitter_answer.principal_other
        subject = "A Cfmm2tar run for %s^%s has been submitted by %s" % (
            principal_actual,
            submitter_answer.project_name,
            submitter_answer.submitter.name,
        )
        body = "A Cfmm2tar run for %s^%s has been submitted." % (
            principal_actual,
            submitter_answer.project_name,
        )
        sender = current_app.config["MAIL_USERNAME"]
        recipients = current_app.config["MAIL_RECIPIENTS"]

        msg = Message(
            subject=subject,
            body=body,
            sender=sender,
            recipients=recipients.split(),
        )
        try:
            mail.send(msg)
        except SMTPAuthenticationError as err:
            print(err)

    cfmm2tar_tasks = Task.query.filter_by(
        task_button_id=answer_id, description="Running cfmm2tar-"
    ).all()
    cfmm2tar_files = Cfmm2tar.query.filter_by(task_button_id=answer_id).all()
    tar2bids_tasks = Task.query.filter_by(
        task_button_id=answer_id, description="Running tar2bids-"
    ).all()
    tar2bids_files = Tar2bids.query.filter_by(task_button_id=answer_id).all()

    return render_template(
        "answer_info.html",
        title="Response",
        submitter_answer=submitter_answer,
        cfmm2tar_tasks=cfmm2tar_tasks,
        button_id=answer_id,
        cfmm2tar_files=cfmm2tar_files,
        tar2bids_tasks=tar2bids_tasks,
        tar2bids_files=tar2bids_files,
        form=form,
    )


@portal_blueprint.route("/results/<int:answer_id>/tar2bids", methods=["POST"])
@login_required
def run_tar2bids(answer_id):
    """Launch tar2bids task and refresh answer_info.html"""
    form = HeuristicForm()
    if form.validate_on_submit():
        current_user.selected_heuristic = form.heuristic.data
        all_options = dict(form.heuristic.choices)
        options = list(all_options.values())
        options.remove(form.heuristic.data)
        current_user.other_heuristic = " ".join(options)

        submitter_answer = Answer.query.get(answer_id)
        if current_user.get_task_in_progress("get_info_from_tar2bids"):
            flash("An Tar2bids run is currently in progress")
        else:
            current_user.launch_task(
                "get_info_from_tar2bids", ("Running tar2bids-")
            )
            db.session.commit()

        if current_app.config["MAIL_ENABLED"]:
            if submitter_answer.principal_other is None:
                principal_actual = submitter_answer.principal
            else:
                principal_actual = submitter_answer.principal_other
            subject = "A Tar2bids run for %s^%s has been submitted by %s" % (
                principal_actual,
                submitter_answer.project_name,
                submitter_answer.submitter.name,
            )
            body = "A Tar2bids run for %s^%s has been submitted." % (
                principal_actual,
                submitter_answer.project_name,
            )
            sender = current_app.config["MAIL_USERNAME"]
            recipients = current_app.config["MAIL_RECIPIENTS"]

            try:
                mail.send(
                    Message(
                        subject=subject,
                        body=body,
                        sender=sender,
                        recipients=recipients.split(),
                    )
                )
            except SMTPAuthenticationError as err:
                print(err)

    cfmm2tar_tasks = Task.query.filter_by(
        task_button_id=answer_id, description="Running cfmm2tar-"
    ).all()
    cfmm2tar_files = Cfmm2tar.query.filter_by(task_button_id=answer_id).all()
    tar2bids_tasks = Task.query.filter_by(
        task_button_id=answer_id, description="Running tar2bids-"
    ).all()
    tar2bids_files = Tar2bids.query.filter_by(task_button_id=answer_id).all()

    return render_template(
        "answer_info.html",
        title="Response",
        submitter_answer=submitter_answer,
        cfmm2tar_tasks=cfmm2tar_tasks,
        button_id=answer_id,
        cfmm2tar_files=cfmm2tar_files,
        tar2bids_tasks=tar2bids_tasks,
        tar2bids_files=tar2bids_files,
        form=form,
    )


@portal_blueprint.route("/results/download", methods=["GET"])
@login_required
def download():
    """Downloads csv containing all the survey response"""
    response_list = db.session.query(Answer).all()
    file_name = "Response_report"

    csv_list = [
        [file_name],
        [
            "Name",
            "Email",
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
            "Principal (Other)",
            "Project Name",
            "Overridden Dataset Name",
            "Sample Date",
            "Retrospective Data",
            "Retrospective Data Start Date",
            "Retrospective Data End Date",
            "Consent",
            "Comment",
        ],
    ]

    def update_scanner(scanner):
        return "3T" if scanner == "type1" else "7T"

    def update_familiarity(familiarity):
        if familiarity == "1":
            new_familiarity = "Not familiar at all"
        elif familiarity == "2":
            new_familiarity = "Have heard of it"
        elif familiarity == "3":
            new_familiarity = "Have used it before"
        elif familiarity == "4":
            new_familiarity = "Used it regularly"
        elif familiarity == "5":
            new_familiarity = "I consider myself an expert"
        return new_familiarity

    def update_date(date):
        return date.date() if date is not None else date

    def update_bool(bool_str):
        return "Yes" if bool_str == "1" else "No"

    for response in response_list:
        csv_list.append(
            [
                response.submitter.name,
                response.submitter.email,
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
                response.principal_other,
                response.project_name,
                response.dataset_name,
                update_date(response.sample),
                update_bool(response.retrospective_data),
                update_date(response.retrospective_start),
                update_date(response.retrospective_end),
                update_bool(response.consent),
                response.comment,
            ]
        )
    return excel.make_response_from_array(csv_list, "csv", file_name=file_name)


@portal_blueprint.route(
    "/results/<int:answer_id>/dicom/<string:method>", methods=["GET"]
)
@login_required
def dicom_verify(answer_id, method):
    """Gets all DICOM results for a specific study."""
    submitter_answer = Answer.query.get(answer_id)
    if submitter_answer.principal_other != "":
        study_info = (
            f"{submitter_answer.principal_other}^"
            + f"{submitter_answer.project_name}"
        )
    else:
        study_info = (
            f"{submitter_answer.principal}^{submitter_answer.project_name}"
        )
    # 'PatientName', 'SeriesDescription', 'SeriesNumber','RepetitionTime',
    # 'EchoTime','ProtocolName','PatientID','SequenceName','PatientSex'
    if method.lower() == "both":
        description = study_info
        date = submitter_answer.sample.date()
    elif method.lower() == "date":
        description = None
        date = submitter_answer.sample.date()
    elif method.lower() == "description":
        description = study_info
        date = None
    else:
        abort(404)
    try:
        dicom_response = gen_utils().query_single_study(
            study_description=description,
            study_date=date,
            output_fields=[
                "00100010",
                "0008103E",
                "00200011",
                "00180080",
                "00180081",
                "00181030",
                "00100020",
                "00180024",
                "00100040",
            ],
            retrieve_level="SERIES",
        )
        return render_template(
            "dicom.html",
            title="Dicom Result",
            dicom_response=dicom_response,
            submitter_answer=submitter_answer,
        )
    except Dcm4cheError as err:
        err_cause = err.__cause__.stderr
        return render_template(
            "dicom_error.html",
            err=err,
            err_cause=err_cause,
            title="DICOM Result Not Found",
        )


@portal_blueprint.route("/logout", methods=["GET", "POST"])
def logout():
    """Logs out current user."""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    logout_user()
    return redirect(url_for("portal_blueprint.index"))
