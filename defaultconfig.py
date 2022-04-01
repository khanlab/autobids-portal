import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    LOG_LEVEL = "WARNING"

    DICOM_SERVER_URL = "0.0.0.0:11112"
    DICOM_SERVER_USERNAME = "username"
    DICOM_SERVER_PASSWORD = "password"
    DICOM_SERVER_TLS = True

    # String to be inserted before dcm4che utilities are invoked.
    # e.g. "singularity exec dcm4che.simg"
    DCM4CHE_PREFIX = ""
    TAR2BIDS_PREFIX = ""
    TAR2BIDS_TEMP_DIR = "/tmp"
    TAR2BIDS_IMAGE_DIR = "/etc/images"
    TAR2BIDS_DEFAULT_IMAGE = "tar2bids.sif"

    # List of PIs accessible on the DICOM server that shouldn't be presented
    # as options in the study form.
    DICOM_PI_BLACKLIST = []

    # Feature flag for email (No email if false)
    MAIL_ENABLED = True

    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_RECIPIENTS = "email_recipients"
    MAIL_USERNAME = "email"
    MAIL_PASSWORD = "password"

    REDIS_URL = os.environ.get("REDIS_URL") or "redis://"

    # Directory, preferably local, into which to temporarily download tar files
    CFMM2TAR_DOWNLOAD_DIR = "/home/debian/cfmm2tar-download"
    # Directory, possibly remote, into which to move downloaded tar files
    CFMM2TAR_STORAGE_DIR = "/home/debian/cfmm2tar-storage"
    TAR2BIDS_DOWNLOAD_DIR = "/home/debian/tar2bids-download"

    # Git repo containing custom heuristic files
    HEURISTIC_GIT_URL = "git@github.com:example/heuristics.git"
    # Local path to which to clone from HEURISTIC_GIT_URL
    HEURISTIC_REPO_PATH = "/home/debian/custom-heuristics"
    # Path (relative to HEURISTIC_REPO_PATH) to directory containing custom
    # heuristic files.
    HEURISTIC_DIR_PATH = "heuristics"
