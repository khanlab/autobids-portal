"""Initialize flask and all its plugins"""

import os

from flask import Flask
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
import flask_excel as excel
from redis import Redis
import rq

from autobidsportal.routes import portal_blueprint, mail
from autobidsportal.models import db, login
from autobidsportal.errors import not_found_error, internal_error


def create_app(config_object=None):
    app = Flask(__name__)
    if config_object is None:
        app.config.from_object(os.environ["AUTOBIDSPORTAL_CONFIG"])
    else:
        app.config.from_object(config_object)
    app.register_blueprint(portal_blueprint, url_prefix="/")
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(500, internal_error)
    db.init_app(app)
    excel.init_excel(app)
    convention = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
    metadata = MetaData(naming_convention=convention)
    app.redis = Redis.from_url(app.config["REDIS_URL"])
    app.task_queue = rq.Queue(connection=app.redis)
    migrate = Migrate(app, db, render_as_batch=True, compare_type=True)
    login.init_app(app)
    login.login_view = "login"
    mail.init_app(app)
    bootstrap = Bootstrap(app)

    return app
