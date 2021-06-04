import pytest
from flask import Flask, flash
from config import Config_test
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
import flask_excel as excel

from autobidsportal import app, db
from autobidsportal.models import User, Answer, Submitter

@pytest.fixture(scope='module')
def new_user():
    user = User(email = 'johnsmith@gmail.com')
    user.set_password(password = 'Password123')
    return user

@pytest.fixture(scope='module')
def test_client():
    autobidsportal.config.from_object("config.Config_test")
    with autobidsportal.test_client() as testing_client:
        with autobidsportal.app_context():
            yield testing_client 

@pytest.fixture(scope='module')
def init_database(test_client):
    db.create_all()
    user1 = User(email = 'johnsmith@gmail.com')
    user1.set_password(password = 'Password123')
    user2 = User(email = 'janedoe@gmail.com')
    user2.set_password(password = 'Password1234-')
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()
    yield
    db.drop_all()

@pytest.fixture(scope='function')
def login_default_user(test_client):
    test_client.post(
        '/login',
        data=dict(email='johnsmith@gmail.com', password='Password123'),
        follow_redirects=True
        )
    yield
    test_client.get('/logout', follow_redirects=True)