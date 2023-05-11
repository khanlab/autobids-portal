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
    override_dict=None,
):
    """Application factory for the Autobids Portal.

    Parameters
    ----------
    config_object : str or object or None
        Reference to an object with config vars to update. If no
        config_object is provided, the environment variable
        AUTOBIDSPORTAL_CONFIG is used.
    override_dict : dict or None
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
    app.register_blueprint(portal_blueprint, url_prefix="/")
    app.register_error_handler(400, bad_request)
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(500, internal_error)

    db.init_app(app)
    excel.init_excel(app)
    app.redis = Redis.from_url(app.config["REDIS_URL"], decode_responses=True)
    app.task_queue = rq.Queue(connection=app.redis)
    Migrate(
        app,
        db,
        render_as_batch=True,
        compare_type=True,
        directory="autobidsportal_migrations",
    )
    login.init_app(app)
    login.login_view = "login"
    mail.init_app(app)

    return app
