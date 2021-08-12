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

    # String to be inserted before dcm4che utilities are invoked.
    # e.g. "singularity exec dcm4che.simg"
    DCM4CHE_PREFIX = ""
    TAR2BIDS_PREFIX= ""

    # List of PIs accessible on the DICOM server that shouldn't be presented
    # as options in the study form.
    DICOM_PI_BLACKLIST = []

    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_RECIPIENTS = "email_recipients"
    MAIL_USERNAME = "email"
    MAIL_PASSWORD = "password"

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'

    CFMM2TAR_DOWNLOAD_DIR = "/home/debian/cfmm2tar-download"
    TAR2BIDS_DOWNLOAD_DIR = "/home/debian/tar2bids-download"

class Config_test(object):
    TESTING = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    WTF_CSRF_ENABLED = False
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app_test.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DICOM_SERVER_URL = "0.0.0.0:11112"
    DICOM_SERVER_USERNAME = "username"
    DICOM_SERVER_PASSWORD = "password"

    # String to be inserted before dcm4che utilities are invoked.
    # e.g. "singularity exec dcm4che.simg"
    DCM4CHE_PREFIX = ""

    # List of PIs accessible on the DICOM server that shouldn't be presented
    # as options in the study form.
    DICOM_PI_BLACKLIST = []

    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_RECIPIENTS = "email_recipients"
    MAIL_USERNAME = "email"
    MAIL_PASSWORD = "password"

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'

    CFMM2TAR_DOWNLOAD_DIR = "/home/debian/cfmm2tar-download"
    TAR2BIDS_DOWNLOAD_DIR = "/home/debian/tar2bids-download"