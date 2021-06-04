from autobidsportal.models import User, Submitter, Answer
import datetime

def test_new_user():
    user = User(email = 'johnsmith@gmail.com')
    user.set_password(password = 'Password123')
    assert user.email == 'johnsmith@gmail.com'
    assert user.password_hash != 'Password123'
    assert user.__repr__() == "<User ('johnsmith@gmail.com', None)>"

def test_new_user_with_fixture(new_user):
    assert new_user.email == 'johnsmith@gmail.com'
    assert new_user.password_hash != 'Password123'

def test_new_submitter():
    submitter = Submitter(email = 'johnsmith@gmail.com', name = 'John')
    assert submitter.email == 'johnsmith@gmail.com'
    assert submitter.name == 'John'
    assert submitter.__repr__() == "<Submitter ('John', 'johnsmith@gmail.com')>"

def test_new_answer():
    answer = Answer(
        status = 'undergraduate',
        scanner = 'type2',
        scan_number = 4,
        study_type = True,
        familiarity_bids = '1',
        familiarity_bidsapp = '1',
        familiarity_python = '1',
        familiarity_linux = '1',
        familiarity_bash = '1',
        familiarity_hpc = '1',
        familiarity_openneuro = '1',
        familiarity_cbrain = '1',
        principal = 'Khan',
        project_name = 'Autobids',
        dataset_name = '',
        sample = datetime.datetime(2021, 1, 10, 0, 0),
        retrospective_data = True,
        retrospective_start = datetime.datetime(2021, 1, 1, 0, 0),
        retrospective_end = datetime.datetime(2021, 1, 5, 0, 0),
        consent = True,
        comment = '',
        submission_date = datetime.datetime(2021, 1, 1, 10, 10, 10, 100000))
        
    assert answer.status == 'undergraduate'
    assert answer.scanner == 'type2'
    assert answer.scan_number == 4
    assert answer.study_type == True
    assert answer.familiarity_bids == '1'
    assert answer.familiarity_bidsapp == '1'
    assert answer.familiarity_python == '1'
    assert answer.familiarity_linux == '1'
    assert answer.familiarity_bash == '1'
    assert answer.familiarity_hpc == '1'
    assert answer.familiarity_openneuro == '1'
    assert answer.familiarity_cbrain == '1'
    assert answer.principal == 'Khan'
    assert answer.project_name == 'Autobids'
    assert answer.dataset_name == ''
    assert answer.sample == datetime.datetime(2021, 1, 10, 0, 0)
    assert answer.retrospective_data == True
    assert answer.retrospective_start == datetime.datetime(2021, 1, 1, 0, 0)
    assert answer.retrospective_end == datetime.datetime(2021, 1, 5, 0, 0)
    assert answer.consent == True
    assert answer.comment == ''
    assert answer.submission_date == datetime.datetime(2021, 1, 1, 10, 10, 10, 100000)
    assert answer.__repr__() == "<Answer ('undergraduate', 'type2', 4, True, '1', '1', '1', '1', '1', '1', '1', '1', 'Khan', 'Autobids', '', datetime.datetime(2021, 1, 10, 0, 0), True, datetime.datetime(2021, 1, 1, 0, 0), datetime.datetime(2021, 1, 5, 0, 0), True, '', datetime.datetime(2021, 1, 1, 10, 10, 10, 100000))>"