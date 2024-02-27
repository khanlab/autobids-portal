"""Test route responses with the test client."""


def _assert_splash(data):
    assert b"Welcome to Autobids!" in data


def test_login_page(test_client):
    """Test that the login page loads."""
    response = test_client.get("/login")
    assert response.status_code == 200
    assert b"Email" in response.data
    assert b"Password" in response.data


def test_valid_login_logout(test_client, init_database):
    """Test that a login and logout with valid credentials works."""
    response = test_client.post(
        "/login",
        data=dict(
            email="johnsmith@gmail.com",
            password="Password123",
            submit="Sign In",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    _assert_splash(response.data)
    assert b"Studies" in response.data
    assert b"Invalid email or password" not in response.data

    response = test_client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Logout" not in response.data
    assert b"Login" in response.data
    assert b"Studies" not in response.data


def test_invalid_login(test_client, init_database):
    """Test that an invalid login fails."""
    response = test_client.post(
        "/login",
        data=dict(
            email="johnsmith@gmail.com",
            password="Password12345",
            submit="Sign In",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logout" not in response.data
    assert b"Login" in response.data
    assert b"Click to Register!" in response.data
    assert b"Name" not in response.data
    assert b"Invalid email or password" in response.data


def test_login_already_logged_in(
    test_client, init_database, login_normal_user
):
    """Test that a login fails when a user is already logs in."""
    response = test_client.post(
        "/login",
        data=dict(
            email="johnsmith@gmail.com",
            password="Password123",
            submit="Sign In",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    assert b"Click to Register!" not in response.data
    _assert_splash(response.data)
    assert b"Studies" in response.data


def test_valid_registration(test_client, init_database):
    """Test that a valid registration succeeds."""
    response = test_client.post(
        "/register",
        data=dict(
            email="johndoe@yahoo.com",
            password="Password123",
            password2="Password123",
            submit="Register",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logout" not in response.data
    assert b"Login" in response.data
    assert b"Click to Register!" in response.data
    assert b"Congratulations, you are now a registered user!" in response.data
    assert b"Studies" not in response.data


def test_invalid_registration(test_client, init_database):
    """Test that an invalid registration fails."""
    response = test_client.post(
        "/register",
        data=dict(
            email="johnsmith@hotmail.com",
            password="Password123",
            password2="Password1234",
            submit="Register",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Field must be equal to password." in response.data
    assert b"Logout" not in response.data
    assert b"Login" in response.data
    assert b"Register" in response.data
    assert (
        b"Congratulations, you are now a registered user!" not in response.data
    )
    assert b"Studies" not in response.data


def test_duplicate_registration(test_client, init_database):
    """Test that a duplicate registration fails."""
    test_client.post(
        "/register",
        data=dict(
            email="johnappleseed@gmail.com",
            password="Password1234",
            password2="Password1234",
            submit="Register",
        ),
        follow_redirects=True,
    )

    response = test_client.post(
        "/register",
        data=dict(
            email="johnappleseed@gmail.com",
            password="Password12345",
            password2="Password12345",
            submit="Register",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert (
        b"There is already an account using this email address. "
        + b"Please use a different email address."
        in response.data
    )
    assert b"Logout" not in response.data
    assert b"Login" in response.data
    assert b"Register" in response.data
    assert b"Studies" not in response.data


def test_valid_login_complete_survey_logout(test_client, init_database):
    """Test an example session with login, logout, and form fill."""
    response = test_client.post(
        "/login",
        data=dict(
            email="johnsmith@gmail.com",
            password="Password123",
            submit="Sign In",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    _assert_splash(response.data)
    assert b"Studies" in response.data

    response = test_client.post(
        "/new",
        data=dict(
            name="John",
            email="johnsmith@gmail.com",
            status="undergraduate",
            scanner="type2",
            scan_number="4",
            study_type="y",
            familiarity_bids="1",
            familiarity_bidsapp="1",
            familiarity_python="1",
            familiarity_linux="1",
            familiarity_bash="1",
            familiarity_hpc="1",
            familiarity_openneuro="1",
            familiarity_cbrain="1",
            principal="Apple",
            project_name="Autobids",
            dataset_name="",
            sample="2021-01-10",
            retrospective_data=True,
            retrospective_start="2021-01-01",
            retrospective_end="2021-01-05",
            consent="y",
            comment="",
            submit="Submit",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Thanks, the survey has been submitted!" in response.data
    assert b"Name" in response.data
    assert b"johnsmith@gmail.com" not in response.data
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    assert b"Studies" in response.data

    response = test_client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Logout" not in response.data
    assert b"Login" in response.data
    _assert_splash(response.data)
    assert b"Studies" not in response.data


def test_valid_survey(test_client, init_database):
    """Test that a valid survey successfully submits."""
    response = test_client.post(
        "/new",
        data=dict(
            name="John",
            email="johnsmith@gmail.com",
            status="undergraduate",
            scanner="type2",
            scan_number="4",
            study_type="y",
            familiarity_bids="1",
            familiarity_bidsapp="1",
            familiarity_python="1",
            familiarity_linux="1",
            familiarity_bash="1",
            familiarity_hpc="1",
            familiarity_openneuro="1",
            familiarity_cbrain="1",
            principal="Apple",
            project_name="Autobids",
            dataset_name="",
            sample="2021-01-10",
            retrospective_data=True,
            retrospective_start="2021-01-01",
            retrospective_end="2021-01-05",
            consent="y",
            comment="",
            submit="Submit",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logout" not in response.data
    assert b"Login" in response.data
    assert b"Name" in response.data
    assert b"johnsmith@gmail.com" not in response.data
    assert b"Thanks, the survey has been submitted!" in response.data
    assert b"Studies" not in response.data


def test_invalid_survey(test_client, init_database):
    """Test that an invalid survey fails."""
    response = test_client.post(
        "/new",
        data=dict(
            name="",
            email="johnsmith@gmail.com",
            status="undergraduate",
            scanner="type2",
            scan_number="4",
            study_type="y",
            familiarity_bids="1",
            familiarity_bidsapp="1",
            familiarity_python="1",
            familiarity_linux="1",
            familiarity_bash="1",
            familiarity_hpc="1",
            familiarity_openneuro="1",
            familiarity_cbrain="1",
            principal="Apple",
            project_name="Autobids",
            dataset_name="",
            sample="2021-01-10",
            retrospective_data=True,
            retrospective_start="2021-01-01",
            retrospective_end="2021-01-05",
            consent="y",
            comment="",
            submit="Submit",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logout" not in response.data
    assert b"Login" in response.data
    assert b"Name" in response.data
    assert b"johnsmith@gmail.com" in response.data
    assert b"Thanks, the survey has been submitted!" not in response.data
    assert b"Studies" not in response.data


def test_results_page(test_client, login_normal_user):
    """Test that results can be accessed."""
    response = test_client.get("/results", follow_redirects=True)
    assert response.status_code == 200
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    assert b"Studies" in response.data


def test_results_download(test_client, init_database, login_normal_user):
    """Test that results can be downloaded."""
    response = test_client.get("/results/download", follow_redirects=True)
    assert response.status_code == 200


def test_complete_survey_access_study_info(test_client, login_admin):
    """Test that a survey's results are viewable."""
    response = test_client.post(
        "/new",
        data=dict(
            name="John",
            email="johnsmith@gmail.com",
            status="undergraduate",
            scanner="type2",
            scan_number="4",
            study_type="y",
            familiarity_bids="1",
            familiarity_bidsapp="1",
            familiarity_python="1",
            familiarity_linux="1",
            familiarity_bash="1",
            familiarity_hpc="1",
            familiarity_openneuro="1",
            familiarity_cbrain="1",
            principal="Apple",
            project_name="Autobids",
            dataset_name="",
            sample="2021-01-10",
            retrospective_data=True,
            retrospective_start="2021-01-01",
            retrospective_end="2021-01-05",
            consent="y",
            comment="",
            submit="Submit",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    assert b"Name" in response.data
    assert b"johnsmith@gmail.com" not in response.data
    assert b"Thanks, the survey has been submitted!" in response.data
    assert b"Studies" in response.data

    response = test_client.get("/results/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    assert b"Studies" in response.data

    response = test_client.get(
        "/results/1/demographics", follow_redirects=True
    )
    assert b"Familiarity" in response.data
    assert b"John" in response.data
    assert b"johnsmith@gmail.com" in response.data

    response = test_client.get("results/1/config", follow_redirects=True)
    assert response.status_code == 200
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    assert b"Study Config: Apple^Autobids" in response.data
    assert b"*_{subject}" in response.data


def test_admin_index(test_client, login_admin):
    """Test that the admin index lists users."""
    response = test_client.get("/admin")
    assert response.status_code == 200
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    assert b"Admin" in response.data
    assert b"johnsmith@gmail.com" in response.data
    assert b"janedoe@gmail.com" in response.data


def test_admin_user(test_client, login_admin):
    """Test that the detailed user page works."""
    response = test_client.get("/admin/1")
    assert response.status_code == 200
    assert b"Logout" in response.data
    assert b"Login" not in response.data
    assert b"Admin" in response.data
    assert b"Administrator" in response.data
    assert b"Access to which studies?" in response.data
    assert b"johnsmith@gmail.com" in response.data
    assert b"janedoe@gmail.com" not in response.data


# This fails because there's no test version of dcm4che
# I'll eventually use mocks to test this functionality, but I'll keep this
# test around in case I find a way around the issue.
# def test_dicom(test_client, login_admin, example_study, dicom_server):
#    """Test that querying the DICOM server works."""
#
#    response = test_client.get("/results/1/dicom/date")
#    assert response.status_code == 200
#    print(response.data)
#    assert b"4MR1" in response.data
#    assert b"CompressedSamples^MR1" in response.data
#
#    response = test_client.get("/results/1/dicom/description")
#    assert response.status_code == 200
#    assert b"4MR1" in response.data
#    assert b"CompressedSamples^MR1" in response.data
#
#    response = test_client.get("/results/1/dicom/description")
#    assert response.status_code == 200
#    assert b"4MR1" in response.data
#    assert b"CompressedSamples^MR1" in response.data
