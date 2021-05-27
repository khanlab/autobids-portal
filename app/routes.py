from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db 
from app.models import User, Submitter, Answer
from app.forms import LoginForm, BidsForm, RegistrationForm
from datetime import datetime
import flask_excel as excel

@app.route('/', methods=['GET', 'POST'])

@app.route('/index', methods=['GET', 'POST'])
def index():
    """ Adds submitter information and their answer to the database
    
    """
    form = BidsForm()
    if form.validate_on_submit():
        
        submitter = Submitter(
            name=form.name.data,
            email=form.email.data
            )
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
        return redirect(url_for('index'))
    return render_template('survey.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ Validates that user inputed correct email and password. If so, user is redirected to index.

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
    """ Validates that user is using a valid email and password when registering. After the user is registered, they are redirected to index.

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
        return redirect(url_for('index'))
    return render_template('register.html', title='Register', form=form)

@app.route('/results', methods=['GET', 'POST'])
@login_required
def results():
    """ Obtains all the responses from the database as well as the date and time the current user last logged in

    """
    last = db.session.query(User).filter(User.id==1)[0]
    res = db.session.query(Answer).order_by(Answer.submission_date.desc()).all()
    return render_template('results.html', title='Responses', res=res, last=last)

@app.route('/results/user', methods=['GET', 'POST'])
@login_required
def answer_info():
    """ Obtains complete survey response based on the submission id

    """
    if request.method == 'POST':
        button_id = list(request.form.keys())[0]
        print(button_id)
        submitter_answer = db.session.query(Answer).filter(Answer.submitter_id==button_id)[0]
    return render_template('answer_info.html', title='Response', submitter_answer=submitter_answer)

@app.route("/results/download", methods=['GET'])
@login_required

def download():
    """ Downloads csv containing all the survey response

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
        'Project Name',
        'Override',
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

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """ Logs out current user

    """
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    logout_user()
    return redirect(url_for('index'))