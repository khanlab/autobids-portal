from Dcm4cheUtils import Dcm4cheUtils

from autobidsportal import app

def gen_utils():
    return Dcm4cheUtils(
        app.config["DICOM_SERVER_URL"],
        app.config["DICOM_SERVER_USERNAME"],
        app.config["DICOM_SERVER_PASSWORD"],
        app.config["DCM4CHE_PREFIX"]
    )

def get_all_pi_names():
    utils = gen_utils()
    pi_list = utils.get_all_pi_names()

    if len(pi_list) < 1:
        raise Dcm4CheError("No PIs accessible")

    return list(set(pi_list) - set(app.config["DICOM_PI_BLACKLIST"]))

class Dcm4CheError(Exception):
    def __init__(self, message):
        self.message = message
