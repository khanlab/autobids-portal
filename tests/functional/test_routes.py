import datetime

def test_login_page(test_client):
    response = test_client.get('/login')
    assert response.status_code == 200
    assert b'Email' in response.data
    assert b'Password' in response.data

def test_valid_login_logout(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', password='Password123'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'New study request: autobids-cfmm' in response.data
    assert b'Results' in response.data

    response = test_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Results' not in response.data

def test_invalid_login(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', password='Password12345'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Click to Register!' in response.data
    assert b'Results' not in response.data


def test_login_already_logged_in(test_client, init_database, login_default_user):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', password='Password123'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Click to Register!' not in response.data
    assert b'Results' in response.data

def test_valid_registration(test_client, init_database):
    response = test_client.post('/register',
                                data=dict(email='johndoe@yahoo.com',
                                          password='Password123',
                                          confirm='Password123'),
                                follow_redirects=True)
    assert response.status_code == 200
    print(response.data)
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Results' not in response.data

def test_invalid_registration(test_client, init_database):
    response = test_client.post('/register',
                                data=dict(email='johnsmith@hotmail.com',
                                          password='Password123',
                                          password2='Password1234'),   
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'[This field is required.]' not in response.data
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Register' in response.data
    assert b'Results' not in response.data

def test_duplicate_registration(test_client, init_database):
    test_client.post('/register',
                     data=dict(email='johnappleseed@gmail.com',
                               password='Password1234',
                               confirm='Password1234'),
                     follow_redirects=True)
    
    response = test_client.post('/register',
                                data=dict(email='johnappleseed@gmail.com',
                                    password='Password12345',
                                    confirm='Password12345'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Register' in response.data
    assert b'Results' not in response.data

def test_valid_login_complete_survey_logout(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', password='Password123'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'New study request: autobids-cfmm' in response.data
    assert b'Results' in response.data

    response = test_client.post('/index',
                                data=dict(name = 'John',
                                    email = 'johnsmith@gmail.com',
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
                                    submission_date = datetime.datetime(2021, 1, 1, 10, 10, 10, 100000)),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'New study request: autobids-cfmm' in response.data
    assert b'Results' in response.data

    response = test_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Results' not in response.data

def test_valid_survey(test_client, init_database):
    response = test_client.post('/index',
                                data=dict(name = 'John',
                                    email = 'johnsmith@gmail.com',
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
                                    submission_date = datetime.datetime(2021, 1, 1, 10, 10, 10, 100000)),
                                follow_redirects=True)
    print(response.data)
    assert response.status_code == 400
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'New study request: autobids-cfmm' in response.data
    assert b'Results' not in response.data

def test_invalid_survey(test_client, init_database):
    response = test_client.post('/index',
                                data=dict(name = '',
                                    email = 'johnsmith@gmail.com',
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
                                    submission_date = datetime.datetime(2021, 1, 1, 10, 10, 10, 100000)),
                                follow_redirects=True)
    print(response.data)
    assert response.status_code == 500
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'New study request: autobids-cfmm' in response.data
    assert b'Results' not in response.data