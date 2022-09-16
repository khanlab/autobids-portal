"""Initialize flask and all its plugins"""

import os

from flask import Flask
from flask_migrate import Migrate
import flask_excel as excel
from redis import Redis
import rq

from autobidsportal.routes import portal_blueprint
from autobidsportal.models import (
    db,
    login,
    User,
    Study,
    Principal,
    Notification,
    Task,
    Cfmm2tarOutput,
    Tar2bidsOutput,
    ExplicitPatient,
)
from autobidsportal.errors import bad_request, not_found_error, internal_error
from autobidsportal.email import mail
# This will register the CLI commands
import autobidsportal.cli  # pylint: disable=unused-import


def create_app(config_object=None, override_dict=None):
    """Application factory for the Autobids Portal.

    Parameters
    ----------
    config_object : str or object reference
        Reference to an object with config vars to update. If no
        config_object is provided, the environment variable
        AUTOBIDSPORTAL_CONFIG is used.
    override_dict : dict
        Dictionary of config vars to update.
    """
    app = Flask(__name__)
    if config_object is None:
        app.config.from_prefixed_env(prefix="AUTOBIDS")
        app.config["REDIS_URL"] = os.environ["REDIS_URL"]
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ[
            "SQLALCHEMY_DATABASE_URI"
        ]
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.environ[
            "SQLALCHEMY_TRACK_MODIFICATIONS"
        ]

    else:
        app.config.from_object(config_object)
    if override_dict is not None:
        app.config.update(override_dict)
    app.logger.setLevel(app.config["LOG_LEVEL"])
    app.register_blueprint(portal_blueprint, url_prefix="/", cli_group=None)
    app.register_error_handler(400, bad_request)
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(500, internal_error)

    db.init_app(app)
    excel.init_excel(app)
    app.redis = Redis.from_url(app.config["REDIS_URL"], decode_responses=True)
    app.task_queue = rq.Queue(connection=app.redis)
    Migrate(app, db, render_as_batch=True, compare_type=True)
    login.init_app(app)
    login.login_view = "login"
    mail.init_app(app)

    @app.shell_context_processor
    def make_shell_context():
        """Add useful variables into the shell context."""
        return {
            "db": db,
            "User": User,
            "Study": Study,
            "Principal": Principal,
            "Notification": Notification,
            "Task": Task,
            "Cfmm2tarOutput": Cfmm2tarOutput,
            "Tar2bidsOutput": Tar2bidsOutput,
            "ExplicitPatient": ExplicitPatient,
        }


    return app
