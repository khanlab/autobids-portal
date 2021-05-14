from flask import render_template, flash, redirect, url_for, request 
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db 
from app.models import User, Submitter, Answer
from app.forms import LoginForm, BidsForm, RegistrationForm, EmptyForm
from datetime import datetime

@app.route('/', methods=['GET', 'POST'])

@app.route('/index', methods=['GET', 'POST'])
def index():
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
    last = db.session.query(User).filter(User.id==1)[0]
    res = db.session.query(Answer).order_by(Answer.submission_date.desc()).all()
    return render_template('results.html', title='Results', res=res, last=last)

@app.route('/results/config', methods=['GET', 'POST'])
@login_required
def config():
    form = EmptyForm()
    return render_template('config.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    logout_user()
    return redirect(url_for('index'))