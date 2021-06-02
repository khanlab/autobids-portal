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
    assert b'Register' not in response.data

    response = test_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Register' in response.data

def test_invalid_login(test_client, init_database):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', password='Password12345'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Register' in response.data


def test_login_already_logged_in(test_client, init_database, login_default_user):
    response = test_client.post('/login',
                                data=dict(email='johnsmith@gmail.com', password='Password123'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Register' not in response.data

def test_valid_registration(test_client, init_database):
    response = test_client.post('/register',
                                data=dict(email='johndoe@yahoo.com',
                                          password='Password123',
                                          confirm='Password123'),
                                follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Register' not in response.data

    response = test_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Logout' not in response.data
    assert b'Login' in response.data
    assert b'Register' in response.data

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
    assert b'Logout' in response.data
    assert b'Login' not in response.data
    assert b'Register' not in response.data


