"""Test fixtures."""

from dataclasses import dataclass
import tempfile
import pathlib
import datetime

import pytest

# import pydicom

from autobidsportal import create_app
from autobidsportal.models import db, User, Principal, Study

# import testdicomserver


@dataclass
class TestConfig:
    """Minimal config class with variables needed for testing."""

    SECRET_KEY = "test_secret"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = False

    REDIS_URL = "redis://localhost:6379"

    LOG_LEVEL = "DEBUG"

    DICOM_SERVER_URL = "PYNETDICOM@127.0.0.1:11112"
    DICOM_SERVER_USERNAME = "username"
    DICOM_SERVER_PASSWORD = "password"
    DICOM_SERVER_TLS = False
    DICOM_PI_BLACKLIST = []

    DCM4CHE_PREFIX = "singularity exec -B /tmp:/tmp /home/tk/Code/western_ossd/singularity_containers/khanlab_cfmm2tar_v0.0.3.sif"
    TAR2BIDS_PREFIX = ""
    TAR2BIDS_DEFAULT_IMAGE = "tar2bids.sif"
    TAR2BIDS_IMAGE_DIR = "/tmp"

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
                    "TAR2BIDS_DOWNLOAD_DIR": str(heuristic_dir_base),
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
def example_study(init_database):
    study = Study(
        submitter_name="Test",
        submitter_email="test@test.com",
        status="staff",
        scanner="type1",
        scan_number=1,
        study_type=False,
        familiarity_bids="1",
        familiarity_bidsapp="1",
        familiarity_python="1",
        familiarity_linux="1",
        familiarity_bash="1",
        familiarity_hpc="1",
        familiarity_openneuro="1",
        familiarity_cbrain="1",
        principal="TestPi",
        project_name="MyStudy",
        dataset_name="MyStudy",
        sample=datetime.datetime(2004, 8, 26),
        retrospective_data=False,
        consent=True,
        submission_date=datetime.datetime(2021, 11, 12),
    )
    db.session.add(study)
    db.session.commit()


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


@pytest.fixture()
def dicom_server():
    """Run a DICOM server for cfmm2tar to interact with."""
    with tempfile.TemporaryDirectory() as temp_dir:
        application_entity, handlers = testdicomserver.gen_application_entity(
            temp_dir
        )
        mr_file = pathlib.Path(pydicom.data.get_testdata_file("MR_small.dcm"))
        with pydicom.dcmread(mr_file) as dcm_file:
            dcm_file.StudyDescription = "TestPi^MyStudy"
            dcm_file.save_as(pathlib.Path(temp_dir) / mr_file.name)
        instance = application_entity.start_server(
            ("", 11112), evt_handlers=handlers, block=False
        )
        yield
    instance.shutdown()
