#!/usr/bin/env python
'''
Define a (limited) Dcm4cheUtils class, which can query a DICOM server for
specified information. Adapted from YingLi Lu's class in the cfmm2tar
project.

For this to work, the machine must have dcm4che installed in some way (i.e.
natively or in a container).
'''

import subprocess
import logging
import re

# for quote python strings for safe use in posix shells
import pipes

from autobidsportal import app


def _get_stdout_stderr_returncode(cmd):
    """
    Execute the external command and get its stdout, stderr and return code
    """
    proc = subprocess.run(
        cmd,
        capture_output=True,
        check=True,
        shell=True  # This is kind of unsafe in a webapp, should rethink
    )

    return proc.stdout, proc.stderr, proc.returncode


class Dcm4cheUtils():
    '''
    dcm4che utils
    '''

    def __init__(self, connect, username, password, dcm4che_path=''):
        self.logger = logging.getLogger(__name__)
        self.connect = connect
        self.username = username
        self.password = password
        self.dcm4che_path = dcm4che_path

        self._findscu_str = \
            '''{} findscu'''.format(self.dcm4che_path) +\
            ' --bind  DEFAULT' +\
            ' --connect {}'.format(self.connect) +\
            ' --accept-timeout 10000 ' +\
            ''' --tls-aes --user {} '''.format(pipes.quote(self.username)) +\
            ''' --user-pass {} '''.format(pipes.quote(self.password))

        self._getscu_str = \
            '''{} getscu'''.format(self.dcm4che_path) +\
            ' --bind  DEFAULT ' +\
            ' --connect {} '.format(self.connect) +\
            ' --accept-timeout 10000 ' +\
            ''' --tls-aes --user {} '''.format(pipes.quote(self.username)) +\
            ''' --user-pass {} '''.format(pipes.quote(self.password))

    def get_all_pi_names(self):
        """Find all PIs the user has access to (by StudyDescription).

        Specifically, find all StudyDescriptions, take the portion before
        the caret, and return each unique value."""
        cmd = self._findscu_str + " -r StudyDescription "

        try:
            out, err, _ = _get_stdout_stderr_returncode(cmd)
        except subprocess.CalledProcessError as error:
            raise Dcm4cheError(
                "Non-zero exit status from findscu."
            ) from error
        if err and err != "Picked up _JAVA_OPTIONS: -Xmx2048m\n":
            self.logger.error(err)

        dcm4che_out = str(out, encoding="utf-8").splitlines()
        study_descriptions = [
            line for line in dcm4che_out if "StudyDescription" in line
        ]
        pi_matches = [
            re.match(r".*\[([\w ]+)\^[\w ]+\].*", line)
            for line in study_descriptions
        ]
        pis = [match.group(1) for match in pi_matches if match is not None]

        all_pis = list(
            set(pis) - set(app.config["DICOM_PI_BLACKLIST"])
        )

        if len(all_pis) < 1:
            raise Dcm4cheError("No PIs accessible.")

        return all_pis

    def query_single_study(
        self,
        output_fields,
        study_description=None,
        study_date=None,
        retrieve_level="STUDY"
    ):
        """Queries a DICOM server for specified tags from one study.

        Parameters
        ----------
        output_fields : list of str
            A list of DICOM tags to query (e.g. PatientName). Passed to
            `findscu -r {}`.
        study_description : str, optional
            The StudyDescription to query. Passed to `findscu -m {}`.
        study_date : date, optional
            The date of the study to query. Converted to "YYYYMMDD" format and
            queries the "StudyDate" tag.
        retrieve_level : str
            Level at which to retrieve records. Defaults to "STUDY", but can
            also be "PATIENT", "SERIES", or "IMAGE".

        Returns
        -------
        list of list of dict
            A list containing one value for each result, where each result
            contains a list of dicts, where each dict contains the code, name,
            and value of each requested tag.
        """
        if study_description is None and study_date is None:
            raise Dcm4cheError(
                "You must specify at least one of study_description and "
                "study_date"
            )

        cmd = self._findscu_str

        if study_description is not None:
            cmd = "{} -m StudyDescription=\"{}\"".format(
                cmd,
                study_description
            )
        if study_date is not None:
            cmd = "{} -m StudyDate=\"{}\"".format(
                cmd,
                study_date.strftime("%Y%m%d")
            )

        cmd = " ".join(
            [cmd] + ["-r {}".format(field) for field in output_fields]
        )
        cmd = "{} -L {}".format(cmd, retrieve_level)

        try:
            out, err, _ = _get_stdout_stderr_returncode(cmd)
        except subprocess.CalledProcessError as error:
            raise Dcm4cheError(
                "Non-zero exit status from findscu."
            ) from error

        if err and err != "Picked up _JAVA_OPTIONS: -Xmx2048m\n":
            self.logger.error(err)

        output_fields = [
           "{},{}".format(field[0:4], field[4:8]).upper()
           if re.fullmatch(r"[\dabcdefABCDEF]{8}", field)
           else field for field in output_fields
        ]

        output_re = (
            r"(\([\dABCDEF]{4},[\dABCDEF]{4}\)) [A-Z]{2} \[(.*)\] (\w+)"
        )

        # Idea: Discard everything before:
        # C-FIND Request done in

        out = str(out, encoding="utf-8")
        out = out[out.find("C-FIND Request done in"):]
        out = out.split("DEBUG - Dataset")[1:]

        grouped_dicts = []
        for dataset in out:
            out_dicts = []
            for line in dataset.splitlines():
                if not any(field in line for field in output_fields):
                    continue
                match = re.match(output_re, line)
                if match is None:
                    continue
                out_dicts.append(
                    {
                        "tag_code": match.group(1),
                        "tag_name": match.group(3),
                        "tag_value": match.group(2)
                    }
                )
            if len(out_dicts) != len(output_fields):
                raise Dcm4cheError(
                    "Missing output fields in dataset {}".format(out_dicts)
                )
            grouped_dicts.append(out_dicts)

        return grouped_dicts


def gen_utils():
    """Generate a Dcm4cheUtils with values from the app config."""
    return Dcm4cheUtils(
        app.config["DICOM_SERVER_URL"],
        app.config["DICOM_SERVER_USERNAME"],
        app.config["DICOM_SERVER_PASSWORD"],
        app.config["DCM4CHE_PREFIX"]
    )


class Dcm4cheError(Exception):
    """Exception raised when something goes wrong with a dcm4che process."""
    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message
