from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from autobidsportal import app, db, mail
from autobidsportal.models import User, Submitter, Answer, Principal, Task, Cfmm2tar, Tar2bids
from autobidsportal.forms import LoginForm, BidsForm, RegistrationForm, HeuristicForm
from autobidsportal.dcm4cheutils import Dcm4cheUtils, gen_utils, Dcm4cheError
from smtplib import SMTPAuthenticationError
from datetime import datetime
from flask_mail import Message
import flask_excel as excel

@app.route('/', methods=['GET', 'POST'])

@app.route('/index', methods=['GET', 'POST'])
def index():
    """ If the Prinicpal table in the database is not empty, add the principal names as options for the Principal drop down in the BidsForm. 
    After submitter presses submit, their information and their answer is added to the database.
    
    """
    form = BidsForm()
    # List of principal names generated from the check-pis cron job and "Other" option are added as choices for the Principal drop down on the BidsForm.
    principal_names = [(p.principal_name, p.principal_name) for p in db.session.query(Principal).all()]
    form.principal.choices = principal_names
    form.principal.choices.insert(0, ('Other', 'Other'))

    if form.validate_on_submit():
        
        # Records name and email of the submitter in the "submitter" table in the database.
        submitter = Submitter(
            name=form.name.data,
            email=form.email.data
            )
        db.session.add(submitter)
        db.session.commit()

        # Records submitter's answer in the "answer" table in the database.
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
            sample = form.sample.data,
            retrospective_data=form.retrospective_data.data,
            retrospective_start=form.retrospective_start.data,
            retrospective_end=form.retrospective_end.data,
            consent=form.consent.data,
            comment=form.comment.data,
            submitter=submitter
            )
        
        db.session.add(answer)
        db.session.commit()
        
        flash(f"Thanks, the survey has been submitted!")

        # Email is sent to "MAIL_RECIPIENTS" after the BidsForm has been submitted.
        subject = "A new request has been submitted by %s" % (answer.submitter.name)
        sender = app.config["MAIL_USERNAME"]
        recipients = app.config["MAIL_RECIPIENTS"]

        msg = Message(
            subject = subject,
            body = "A new request has been submitted. Please login to see the submitter's response",
            sender = sender,
            recipients = recipients.split()
            )
        mail.send(msg)
        
        return redirect(url_for('index'))
    return render_template('survey.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ Validates that user inputed correct email and password. If so, user is redirected to login.html.

    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """ Validates that user is using a valid email and password when registering. After the user is registered, they are redirected to login.html.

    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/results', methods=['GET', 'POST'])
@login_required
def results():
    """ Obtains all the responses from the database as well as the date and time the current user last logged in.

    """
    last = db.session.query(User).filter(User.id==1)[0]
    res = db.session.query(Answer).order_by(Answer.submission_date.desc()).all()
    return render_template('results.html', title='Responses', res=res, last=last)

@app.route('/results/user', methods=['GET', 'POST'])
@login_required
def answer_info():
    """ Obtains complete survey response based on the submission id.

    """
    form = HeuristicForm()
    if request.method == 'POST':
        button_id = list(request.form.keys())[0]
        if len(button_id)>1:
            cfmm2tar_file_id = button_id.rsplit('-',2)[1]
            button_id = button_id.rsplit('-',2)[0]
            current_user.second_last_pressed_button_id = button_id
            current_user.last_pressed_button_id = cfmm2tar_file_id
        else:
            current_user.last_pressed_button_id = button_id
            current_user.second_last_pressed_button_id = None
        db.session.commit()
        submitter_answer = db.session.query(Answer).filter(Answer.submitter_id==button_id)[0]
        cfmm2tar_tasks = Task.query.filter_by(task_button_id = button_id, description = 'Running cfmm2tar-').all()
        cfmm2tar_files = Cfmm2tar.query.filter_by(task_button_id = button_id).all()
        tar2bids_tasks = Task.query.filter_by(task_button_id = button_id, description = 'Running tar2bids-').all()
        tar2bids_files = Tar2bids.query.filter_by(task_button_id = button_id).all()
    return render_template('answer_info.html', title='Response', submitter_answer=submitter_answer, cfmm2tar_tasks=cfmm2tar_tasks, button_id=current_user.last_pressed_button_id, cfmm2tar_files=cfmm2tar_files, tar2bids_tasks=tar2bids_tasks, tar2bids_files=tar2bids_files, form=form)

@app.route('/results/user/cfmm2tar', methods=['GET', 'POST'])
@login_required
def run_cfmm2tar():
    """ Launch cfmm2tar task and refresh answer_info.html.

    """
    form = HeuristicForm()
    if request.method == 'POST':
        button_id = list(request.form.keys())[0]
        if len(button_id)>1:
            cfmm2tar_file_id = button_id.rsplit('-',2)[1]
            button_id = button_id.rsplit('-',2)[0]
            current_user.second_last_pressed_button_id = button_id
            current_user.last_pressed_button_id = cfmm2tar_file_id
        else:
            current_user.last_pressed_button_id = button_id
            current_user.second_last_pressed_button_id = None
        db.session.commit()
        submitter_answer = db.session.query(Answer).filter(Answer.submitter_id==button_id)[0]
        if current_user.get_task_in_progress('get_info_from_cfmm2tar'):
            flash('An Cfmm2tar run is currently in progress')
        else:
            current_user.launch_task('get_info_from_cfmm2tar', ('Running cfmm2tar-'))
            db.session.commit()
        cfmm2tar_tasks = Task.query.filter_by(task_button_id = button_id, description = 'Running cfmm2tar-').all()
        cfmm2tar_files = Cfmm2tar.query.filter_by(task_button_id = button_id).all()
        tar2bids_tasks = Task.query.filter_by(task_button_id = button_id, description = 'Running tar2bids-').all()
        tar2bids_files = Tar2bids.query.filter_by(task_button_id = button_id).all()

        # Email is sent to "MAIL_RECIPIENTS" after a Cfmm2tar task has been started.
        try:
            if submitter_answer.principal_other == None:
                subject = "A Cfmm2tar run for %s^%s has been submitted by %s" % (submitter_answer.principal, submitter_answer.project_name, submitter_answer.submitter.name)
                body = "A Cfmm2tar run for %s^%s has been submitted." % (submitter_answer.principal, submitter_answer.project_name)
                sender = app.config["MAIL_USERNAME"]
                recipients = app.config["MAIL_RECIPIENTS"]

                msg = Message(
                    subject = subject,
                    body = body,
                    sender = sender,
                    recipients = recipients.split()
                    )
                mail.send(msg)
            else:
                subject = "A Cfmm2tar run for %s^%s has been submitted by %s" % (submitter_answer.principal_other, submitter_answer.project_name, submitter_answer.submitter.name)
                body = "A Cfmm2tar run for %s^%s has been submitted." % (submitter_answer.principal_other, submitter_answer.project_name)
                sender = app.config["MAIL_USERNAME"]
                recipients = app.config["MAIL_RECIPIENTS"]

                msg = Message(
                    subject = subject,
                    body = body,
                    sender = sender,
                    recipients = recipients.split()
                    )
                mail.send(msg)
        except SMTPAuthenticationError as err:
            print(err)

    return render_template('answer_info.html', title='Response', submitter_answer=submitter_answer, cfmm2tar_tasks=cfmm2tar_tasks, button_id=current_user.last_pressed_button_id, cfmm2tar_files=cfmm2tar_files, tar2bids_tasks=tar2bids_tasks, tar2bids_files=tar2bids_files, form=form)

@app.route('/results/user/tar2bids', methods=['GET', 'POST'])
@login_required
def run_tar2bids():
    """ Launch tar2bids task and refresh answer_info.html.

    """
    # A heuristic is selected using HeuristicForm. The selected heuristic is recorded and used when running Tar2bids.
    form = HeuristicForm()
    if form.validate_on_submit() and request.method == 'POST':
        current_user.selected_heuristic = form.heuristic.data
        all_options = dict(form.heuristic.choices)
        options=list(all_options.values())
        options.remove(form.heuristic.data)
        current_user.other_heuristic = ' '.join(options)
    
        button_id = list(request.form.keys())[2]
        if len(button_id)>1:
            cfmm2tar_file_id = button_id.rsplit('-',2)[1]
            button_id = button_id.rsplit('-',2)[0]
            current_user.second_last_pressed_button_id = button_id
            current_user.last_pressed_button_id = cfmm2tar_file_id
        else:
            current_user.last_pressed_button_id = button_id
            current_user.second_last_pressed_button_id = None
        db.session.commit()
        submitter_answer = db.session.query(Answer).filter(Answer.submitter_id==button_id)[0]
        tar_file = db.session.query(Cfmm2tar).filter(Cfmm2tar.id==cfmm2tar_file_id)[0].tar_file
        if current_user.get_task_in_progress('get_info_from_tar2bids'):
            flash('An Tar2bids run is currently in progress')
        else:
            current_user.launch_task('get_info_from_tar2bids', ('Running tar2bids-'))
            db.session.commit()
        cfmm2tar_tasks = Task.query.filter_by(task_button_id = button_id, description = 'Running cfmm2tar-').all()
        cfmm2tar_files = Cfmm2tar.query.filter_by(task_button_id = button_id).all()
        tar2bids_tasks = Task.query.filter_by(task_button_id = button_id, description = 'Running tar2bids-').all()
        tar2bids_files = Tar2bids.query.filter_by(task_button_id = button_id).all()

        # Email is sent to "MAIL_RECIPIENTS" after a Tar2bids task has been started.
        try:
            if submitter_answer.principal_other == None:
                subject = "A Tar2bids run for %s^%s has been submitted by %s" % (submitter_answer.principal, submitter_answer.project_name, submitter_answer.submitter.name)
                body = "A Tar2bids run for %s^%s has been submitted." % (submitter_answer.principal, submitter_answer.project_name)
                sender = app.config["MAIL_USERNAME"]
                recipients = app.config["MAIL_RECIPIENTS"]

                msg = Message(
                    subject = subject,
                    body = body,
                    sender = sender,
                    recipients = recipients.split()
                    )
                mail.send(msg)
            else:
                subject = "A Tar2bids run for %s^%s has been submitted by %s" % (submitter_answer.principal_other, submitter_answer.project_name, submitter_answer.submitter.name)
                body = "A Tar2bids run for %s^%s has been submitted." % (submitter_answer.principal_other, submitter_answer.project_name)
                sender = app.config["MAIL_USERNAME"]
                recipients = app.config["MAIL_RECIPIENTS"]

                msg = Message(
                    subject = subject,
                    body = body,
                    sender = sender,
                    recipients = recipients.split()
                    )
                mail.send(msg)
        except SMTPAuthenticationError as err:
            print(err_cause)

    return render_template('answer_info.html', title='Response', submitter_answer=submitter_answer, cfmm2tar_tasks=cfmm2tar_tasks, button_id=current_user.last_pressed_button_id, cfmm2tar_files=cfmm2tar_files, tar2bids_tasks=tar2bids_tasks, tar2bids_files=tar2bids_files, form=form)

@app.route("/results/download", methods=['GET'])
@login_required
def download():
    """ Downloads csv containing all the survey response.

    """
    response_list = db.session.query(Answer).all()
    file_name='Response_report'

    csv_list = [[file_name], [
        'Name',
        'Email',
        'Status',
        'Scanner',
        'Number of Scans',
        'Study Type',
        'Bids Familiarity',
        'Bids App Familiarity',
        'Python Familiarity',
        'Linux Familiarity',
        'Bash Familiarity',
        'HPC Familiarity',
        'OPENNEURO Familiarity',
        'CBRAIN Familiarity',
        'Principal',
        'Principal (Other)',
        'Project Name',
        'Overridden Dataset Name',
        'Sample Date',
        'Retrospective Data',
        'Retrospective Data Start Date',
        'Retrospective Data End Date',
        'Consent'
        'Comment',
        ]]

    def update_scanner(scanner):
        return '3T' if scanner == 'type1' else '7T'
 
    def update_familiarity(familiarity):
        if familiarity == '1':
            new_familiarity = 'Not familiar at all'
        elif familiarity == '2':
            new_familiarity = 'Have heard of it'
        elif familiarity == '3':
            new_familiarity = 'Have used it before'
        elif familiarity == '4':
            new_familiarity = 'Used it regularly'
        elif familiarity == '5':
            new_familiarity = 'I consider myself an expert'
        return new_familiarity
    
    def update_date(date):
        return date.date() if date is not None else date
    
    def update_bool(bool):
        return 'Yes' if bool == '1' else 'No'

    for r in response_list:

        csv_list.append([
            r.submitter.name,
            r.submitter.email,
            r.status.capitalize(),
            update_scanner(r.scanner),
            r.scan_number,
            update_bool(r.study_type),
            update_familiarity(r.familiarity_bids),
            update_familiarity(r.familiarity_bidsapp),
            update_familiarity(r.familiarity_python),
            update_familiarity(r.familiarity_linux),
            update_familiarity(r.familiarity_bash),
            update_familiarity(r.familiarity_hpc),
            update_familiarity(r.familiarity_openneuro),
            update_familiarity(r.familiarity_cbrain),
            r.principal,
            r.principal_other,
            r.project_name,
            r.dataset_name,
            update_date(r.sample),
            update_bool(r.retrospective_data),
            update_date(r.retrospective_start),
            update_date(r.retrospective_end),
            update_bool(r.consent),
            r.comment,
            ])
    return excel.make_response_from_array(csv_list, 'csv', file_name=file_name)

@app.route('/results/user/dicom', methods=['GET', 'POST'])
@login_required
def dicom_verify():
    """ Obtains all DICOM results for a specific study.

    """
    button_id = list(request.form.keys())[0]
    submitter_answer = db.session.query(Answer).filter(Answer.submitter_id==button_id)[0]
    if submitter_answer.principal_other != '':
        study_info = f"{submitter_answer.principal_other}^{submitter_answer.project_name}"
    else:
        study_info = f"{submitter_answer.principal}^{submitter_answer.project_name}"
    # 'PatientName', 'SeriesDescription', 'SeriesNumber','RepetitionTime','EchoTime','ProtocolName','PatientID','SequenceName','PatientSex' 
    try:
        if list(request.form.values())[0] == 'Config':
            dicom_response = gen_utils().query_single_study(study_description=study_info, study_date=submitter_answer.sample.date(), output_fields=['00100010','0008103E','00200011','00180080','00180081','00181030','00100020','00180024','00100040'], retrieve_level='SERIES')
        elif list(request.form.values())[0] == 'Config-Study Date':
            dicom_response = gen_utils().query_single_study(study_description=None, study_date=submitter_answer.sample.date(), output_fields=['00100010','0008103E','00200011','00180080','00180081','00181030','00100020','00180024','00100040'], retrieve_level='SERIES')
        else:
            dicom_response = gen_utils().query_single_study(study_description=study_info, study_date=None, output_fields=['00100010','0008103E','00200011','00180080','00180081','00181030','00100020','00180024','00100040'], retrieve_level='SERIES')
        return render_template('dicom.html', title='Dicom Result', dicom_response=dicom_response, submitter_answer=submitter_answer)
    except Dcm4cheError as err:
        err_cause = err.__cause__.stderr
        return render_template('dicom_error.html', err=err, err_cause=err_cause, title='DICOM Result Not Found')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """ Logs out current user.

    """
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    logout_user()
    return redirect(url_for('index'))