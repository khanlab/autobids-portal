"""Initialize flask and all its plugins"""

import os

from flask import Flask
from flask_migrate import Migrate
import flask_excel as excel
from redis import Redis
import rq

from autobidsportal.routes import portal_blueprint, mail
from autobidsportal.models import db, login
from autobidsportal.errors import bad_request, not_found_error, internal_error


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
        app.config.from_object(os.environ["AUTOBIDSPORTAL_CONFIG"])
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
    app.redis = Redis.from_url(app.config["REDIS_URL"])
    app.task_queue = rq.Queue(connection=app.redis)
    Migrate(app, db, render_as_batch=True, compare_type=True)
    login.init_app(app)
    login.login_view = "login"
    mail.init_app(app)

    return app
