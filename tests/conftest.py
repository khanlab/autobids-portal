"""Test fixtures."""

from dataclasses import dataclass
import tempfile
import pathlib

import pytest

from autobidsportal import create_app
from autobidsportal.models import db, User, Principal


@dataclass
class TestConfig:
    """Minimal config class with variables needed for testing."""

    SECRET_KEY = "test_secret"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = False

    REDIS_URL = "redis://localhost:6379"

    DICOM_PI_BLACKLIST = []

    MAIL_ENABLED = False

    TESTING = True


@pytest.fixture()
def test_client():
    """Make an app with the test config and yield a test client."""

    with tempfile.NamedTemporaryFile() as db_file:
        with tempfile.TemporaryDirectory() as heuristic_dir_base:
            heuristic_dir = pathlib.Path(heuristic_dir_base) / "heuristics"
            heuristic_dir.mkdir()

            app = create_app(
                config_object=TestConfig(),
                override_dict={
                    "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file.name}",
                    "HEURISTIC_REPO_PATH": str(heuristic_dir_base),
                    "HEURISTIC_DIR_PATH": "heuristics",
                },
            )
            with app.test_client() as testing_client:
                with app.app_context():
                    yield testing_client


@pytest.fixture()
def new_user():
    """Make a user that can be added to the db."""
    user = User(email="johnsmith@gmail.com")
    user.set_password(password="Password123")
    return user


@pytest.fixture()
def init_database(test_client):
    """Create a test database and populate it with some users."""
    db.create_all()
    user1 = User(email="johnsmith@gmail.com", admin=False)
    user1.set_password(password="Password123")
    user2 = User(email="janedoe@gmail.com", admin=True)
    user2.set_password(password="Password1234-")
    db.session.add(user1)
    db.session.add(user2)
    principal = Principal(principal_name="Apple")
    db.session.add(principal)
    db.session.commit()
    yield
    db.drop_all()


@pytest.fixture()
def login_normal_user(test_client, init_database):
    """Log the default user in."""
    test_client.post(
        "/login",
        data={"email": "johnsmith@gmail.com", "password": "Password123"},
        follow_redirects=True,
    )
    yield
    test_client.get("/logout", follow_redirects=True)


@pytest.fixture()
def login_admin(test_client, init_database):
    """Log an admin in."""
    test_client.post(
        "/login",
        data={"email": "janedoe@gmail.com", "password": "Password1234-"},
        follow_redirects=True,
    )
    yield
    test_client.get("/logout", follow_redirects=True)
