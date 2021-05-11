import os
import tempfile

import pytest

from app import app.models, app.routes, ap.forms
from app import db, login


# @pytest.fixture
# def client():
#     db_fd, flaskr.app.config['DATABASE'] = tempfile.mkstemp()
#     flaskr.app.config['TESTING'] = True

#     with flaskr.app.test_client() as client:
#         with flaskr.app.app_context():
#             flaskr.init_db()
#         yield client

#     os.close(db_fd)
#     os.unlink(flaskr.app.config['DATABASE'])