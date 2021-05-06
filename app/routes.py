
from flask import render_template, flash, redirect, url_for, request 
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db 
from app.models import Answer
from app.forms import LoginForm, BidsForm, RegistrationForm
from app.models import User, Answer

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = BidsForm()
    if form.validate_on_submit():

        potential_user = User.query.filter(User.username==form.name.data).all()
        if len(potential_user) > 0:
            user = potential_user[0]
        else:
            user = User(username=form.name.data, email=form.email.data)
            db.session.add(user)
            db.session.commit()

        answer = Answer(
            status=form.status.data,
            scanner=form.scanner.data,
            scan_number=form.scan_number.data,
            study_type=form.study_type.data,
            familiarity=form.familiarity.data,
            principal=form.principal.data,
            project_name=form.project_name.data,
            dataset_name=form.dataset_name.data,
            retrospective_data=form.retrospective_data.data,
            retrospective_start=form.retrospective_start.data,
            retrospective_end=form.retrospective_end.data,
            consent=form.consent.data,
            comment=form.text_area.data,
            user=user
            )
        db.session.add(answer)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('survey.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)
    
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/results', methods=['GET', 'POST'])
def results():
    res = db.session.query(Answer).all()
    return render_template('results.html', title='Results', res=res)

# def check_for_admin(*args, **kw):
    #if request.path.startswith('/admin/'):
        #if not user.is_admin():
            #return redirect(url_for('login_form'))