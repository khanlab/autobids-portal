import datetime
import flask_excel as excel

def test_login_page(test_client):
    response = test_client.get('/login')
    assert response.status_code == 200
    assert b'Email' in response.data
    assert b'Password' in response.data

def test_valid_login_logout(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', 
                                password='Password123',
                                submit='Sign In'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'Results' in response.data
    assert b'Invalid email or password' not in response.data

    response = test_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Results' not in response.data

def test_invalid_login(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', 
                                password='Password12345',
                                submit='Sign In'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Click to Register!' in response.data
    assert b'Name' not in response.data
    assert b'Results' not in response.data
    assert b'Invalid email or password' in response.data


def test_login_already_logged_in(test_client, init_database, login_default_user):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', 
                                password='Password123',
                                submit='Sign In'),
                                follow_redirects=True)
    print(response.data)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Click to Register!' not in response.data
    assert b'Name' in response.data
    assert b'Results' in response.data

def test_valid_registration(test_client, init_database):
    response = test_client.post('/register',
                                data=dict(email='johndoe@yahoo.com',
                                    password='Password123',
                                    password2='Password123',
                                    submit='Register'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Click to Register!' in response.data
    assert b'Congratulations, you are now a registered user!' in response.data
    assert b'Name' not in response.data
    assert b'Results' not in response.data

def test_invalid_registration(test_client, init_database):
    response = test_client.post('/register',
                                data=dict(email='johnsmith@hotmail.com',
                                    password='Password123',
                                    password2='Password1234',
                                    submit='Register'),   
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Field must be equal to password.' in response.data
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Register' in response.data
    assert b'Congratulations, you are now a registered user!' not in response.data
    assert b'Results' not in response.data

def test_duplicate_registration(test_client, init_database):
    test_client.post('/register',
                     data=dict(email='johnappleseed@gmail.com',
                        password='Password1234',
                        password2='Password1234',
                        submit='Register'),
                     follow_redirects=True)
    
    response = test_client.post('/register',
                                data=dict(email='johnappleseed@gmail.com',
                                    password='Password12345',
                                    password2='Password12345',
                                    submit='Register'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'There is already an account using this email address. Please use a different email address.' in response.data
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Register' in response.data
    assert b'Results' not in response.data

def test_valid_login_complete_survey_logout(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', 
                                    password='Password123',
                                    submit='Sign In'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'Results' in response.data

    response = test_client.post('/index',
                                data=dict(name = 'John',
                                    email = 'johnsmith@gmail.com',
                                    status = 'undergraduate',
                                    scanner = 'type2',
                                    scan_number = '4',
                                    study_type = 'y',
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
                                    sample = '2021-01-10',
                                    retrospective_data = True,
                                    retrospective_start = '2021-01-01',
                                    retrospective_end = '2021-01-05',
                                    consent = 'y',
                                    comment = '',
                                    submit = 'Submit'), 
                                    follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'johnsmith@gmail.com' not in response.data
    assert b'Thanks, the survey has been submitted!' in response.data
    assert b'Results' in response.data

    response = test_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Name' in response.data
    assert b'Results' not in response.data

def test_valid_survey(test_client, init_database):
    response = test_client.post('/index',
                                data=dict(name = 'John',
                                    email = 'johnsmith@gmail.com',
                                    status = 'undergraduate',
                                    scanner = 'type2',
                                    scan_number = '4',
                                    study_type = 'y',
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
                                    sample = '2021-01-10',
                                    retrospective_data = True,
                                    retrospective_start = '2021-01-01',
                                    retrospective_end = '2021-01-05',
                                    consent = 'y',
                                    comment = '',
                                    submit = 'Submit'), 
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Name' in response.data
    assert b'johnsmith@gmail.com' not in response.data
    assert b'Thanks, the survey has been submitted!' in response.data
    assert b'Results' not in response.data
    
def test_invalid_survey(test_client, init_database):
    response = test_client.post('/index',
                                data=dict(name = '',
                                    email = 'johnsmith@gmail.com',
                                    status = 'undergraduate',
                                    scanner = 'type2',
                                    scan_number = '4',
                                    study_type = 'y',
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
                                    sample = '2021-01-10',
                                    retrospective_data = True,
                                    retrospective_start = '2021-01-01',
                                    retrospective_end = '2021-01-05',
                                    consent = 'y',
                                    comment = '',
                                    submit = 'Submit'), 
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Name' in response.data
    assert b'johnsmith@gmail.com' in response.data
    assert b'Thanks, the survey has been submitted!' not in response.data
    assert b'Results' not in response.data

def test_valid_login_access_results(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', 
                                    password='Password123',
                                    submit='Sign In'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'Results' in response.data

    response = test_client.post('/results', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'Results' in response.data

def test_valid_login_access_results_download(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', 
                                    password='Password123',
                                    submit='Sign In'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'Results' in response.data

    response = test_client.post('/results', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'Results' in response.data

    response = test_client.get('/results/download', follow_redirects=True)
    assert response.status_code == 200

def test_valid_login_complete_survey_access_results_view_more(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', 
                                    password='Password123',
                                    submit='Sign In'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'Results' in response.data

    response = test_client.post('/index',
                                data=dict(name = 'John',
                                    email = 'johnsmith@gmail.com',
                                    status = 'undergraduate',
                                    scanner = 'type2',
                                    scan_number = '4',
                                    study_type = 'y',
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
                                    sample = '2021-01-10',
                                    retrospective_data = True,
                                    retrospective_start = '2021-01-01',
                                    retrospective_end = '2021-01-05',
                                    consent = 'y',
                                    comment = '',
                                    submit = 'Submit'), 
                                    follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'johnsmith@gmail.com' not in response.data
    assert b'Thanks, the survey has been submitted!' in response.data
    assert b'Results' in response.data

    response = test_client.post('/results', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'Results' in response.data

    response = test_client.post('/results/user', data={"1": 'View+more'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Name' in response.data
    assert b'Familiarity' in response.data
    assert b'Results' in response.data