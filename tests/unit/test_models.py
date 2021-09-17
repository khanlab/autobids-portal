"""Unit tests of the database models."""

import datetime
from autobidsportal.models import User, Study


def test_new_user():
    """Generate a user and ensure their password gets hashed."""
    user = User(email="johnsmith@gmail.com")
    user.set_password(password="Password123")
    assert user.email == "johnsmith@gmail.com"
    assert user.password_hash != "Password123"


def test_new_user_with_fixture(new_user):
    """Ensure the fixture user's password gets hashed."""
    assert new_user.email == "johnsmith@gmail.com"
    assert new_user.password_hash != "Password123"


def test_new_study():
    """Test study columns."""
    study = Study(
        status="undergraduate",
        scanner="type2",
        scan_number=4,
        study_type=True,
        familiarity_bids="1",
        familiarity_bidsapp="1",
        familiarity_python="1",
        familiarity_linux="1",
        familiarity_bash="1",
        familiarity_hpc="1",
        familiarity_openneuro="1",
        familiarity_cbrain="1",
        principal="Khan",
        project_name="Autobids",
        dataset_name="",
        sample=datetime.datetime(2021, 1, 10, 0, 0),
        retrospective_data=True,
        retrospective_start=datetime.datetime(2021, 1, 1, 0, 0),
        retrospective_end=datetime.datetime(2021, 1, 5, 0, 0),
        consent=True,
        comment="",
        submission_date=datetime.datetime(2021, 1, 1, 10, 10, 10, 100000),
    )

    assert study.status == "undergraduate"
    assert study.scanner == "type2"
    assert study.scan_number == 4
    assert study.study_type
    assert study.familiarity_bids == "1"
    assert study.familiarity_bidsapp == "1"
    assert study.familiarity_python == "1"
    assert study.familiarity_linux == "1"
    assert study.familiarity_bash == "1"
    assert study.familiarity_hpc == "1"
    assert study.familiarity_openneuro == "1"
    assert study.familiarity_cbrain == "1"
    assert study.principal == "Khan"
    assert study.project_name == "Autobids"
    assert study.dataset_name == ""
    assert study.sample == datetime.datetime(2021, 1, 10, 0, 0)
    assert study.retrospective_data
    assert study.retrospective_start == datetime.datetime(2021, 1, 1, 0, 0)
    assert study.retrospective_end == datetime.datetime(2021, 1, 5, 0, 0)
    assert study.consent
    assert study.comment == ""
    assert study.submission_date == datetime.datetime(
        2021, 1, 1, 10, 10, 10, 100000
    )
    studys = (
        "undergraduate",
        "type2",
        4,
        True,
        "1",
        "1",
        "1",
        "1",
        "1",
        "1",
        "1",
        "1",
        "Khan",
        "Autobids",
        "",
        datetime.datetime(2021, 1, 10, 0, 0),
        True,
        datetime.datetime(2021, 1, 1, 0, 0),
        datetime.datetime(2021, 1, 5, 0, 0),
        True,
        "",
        datetime.datetime(2021, 1, 1, 10, 10, 10, 100000),
    )
    assert study.__repr__() == f"<Answer {studys}>"
