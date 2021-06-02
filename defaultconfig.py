import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DICOM_SERVER_URL = "0.0.0.0:11112"
    DICOM_SERVER_USERNAME = "username"
    DICOM_SERVER_PASSWORD = "password"
    DCM4CHE_PREFIX = ""
    DICOM_PI_BLACKLIST = []
