"""Test fixtures."""

import pytest

from autobidsportal import create_app
from autobidsportal.models import db, User


@pytest.fixture(scope="module")
def new_user():
    """Make a user that can be added to the db."""
    user = User(email="johnsmith@gmail.com")
    user.set_password(password="Password123")
    return user


@pytest.fixture(scope="module")
def test_client():
    """Make an app with the test config and yield a test client."""
    app = create_app("config.Config_test")
    with app.test_client() as testing_client:
        with app.app_context():
            yield testing_client


@pytest.fixture(scope="module")
def init_database(test_client):
    """Create a test database and populate it with some users."""
    db.create_all()
    user1 = User(email="johnsmith@gmail.com")
    user1.set_password(password="Password123")
    user2 = User(email="janedoe@gmail.com")
    user2.set_password(password="Password1234-")
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()
    yield
    db.drop_all()


@pytest.fixture(scope="function")
def login_default_user(test_client):
    """Log the default user in."""
    test_client.post(
        "/login",
        data=dict(email="johnsmith@gmail.com", password="Password123"),
        follow_redirects=True,
    )
    yield
    test_client.get("/logout", follow_redirects=True)
