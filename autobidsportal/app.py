"""Initialize flask and all its plugins."""
from __future__ import annotations

import os

import flask_excel as excel
import rq
from flask import Flask
from flask_migrate import Migrate
from redis import Redis

from autobidsportal.email import mail
from autobidsportal.errors import bad_request, internal_error, not_found_error
from autobidsportal.models import db, login
from autobidsportal.routes import portal_blueprint


def create_app(
    config_object: str | object | None = None,
    override_dict: dict[str, str] | None = None,
):
    """Application factory for the Autobids Portal.

    Parameters
    ----------
    config_object
        Reference to an object with config vars to update. If no
        config_object is provided, the environment variable
        AUTOBIDSPORTAL_CONFIG is used.

    override_dict
        Dictionary of config vars to update.

    Returns
    -------
    Flask
        Flask-application with extensions and options configured
    """
    app = Flask(__name__)
    # Instantiate a config object
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

    # Overwrite config
    if override_dict is not None:
        app.config.update(override_dict)

    # Set app options, update routes and errors
    app.logger.setLevel(app.config["LOG_LEVEL"])
    app.register_blueprint(portal_blueprint, url_prefix="/")
    app.register_error_handler(400, bad_request)
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(500, internal_error)

    db.init_app(app)  # Init SQLAlchemy instance
    excel.init_excel(app)  # Init flask-excel extension

    # Setup Redis connection + handling of tasks via queue and db operations
    # (Note: These are specific to this application - not Flask)
    app.redis = Redis.from_url(  # pyright: ignore
        app.config["REDIS_URL"],
        decode_responses=True,
    )
    app.task_queue = rq.Queue(connection=app.redis)  # pyright: ignore
    Migrate(
        app,
        db,
        render_as_batch=True,
        compare_type=True,
        directory="autobidsportal_migrations",
    )

    # Init login manager and set default view if login needed
    login.init_app(app)
    login.login_view = "login"  # pyright: ignore

    # Init flask-mail extension
    mail.init_app(app)

    return app
