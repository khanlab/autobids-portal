#!/usr/bin/env python
"""
Define a (limited) Dcm4cheUtils class, which can query a DICOM server for
specified information. Adapted from YingLi Lu's class in the cfmm2tar
project.
For this to work, the machine must have dcm4che installed in some way (i.e.
natively or in a container).
"""

import subprocess
import logging
import re
import tempfile

# for quote python strings for safe use in posix shells
import pipes
from flask import current_app


def _get_stdout_stderr_returncode(cmd):
    """
    Execute the external command and get its stdout, stderr and return code
    """
    proc = subprocess.run(
        cmd,
        capture_output=True,
        check=True,
        shell=True,  # This is kind of unsafe in a webcurrent_app, should rethink
    )

    return proc.stdout, proc.stderr, proc.returncode


class Dcm4cheUtils:
    """
    dcm4che utils
    """

    def __init__(
        self,
        connect,
        username,
        password,
        dcm4che_path="",
        tar2bids_path="",
        use_tls=True,
    ):
        self.logger = logging.getLogger(__name__)
        self.connect = connect
        self.username = username
        self.password = password
        self.dcm4che_path = dcm4che_path

        self._findscu_str = (
            """{} findscu""".format(self.dcm4che_path)
            + " --bind  DEFAULT"
            + " --connect {}".format(self.connect)
            + " --accept-timeout 10000 "
            + """ --user {} """.format(pipes.quote(self.username))
            + """ --user-pass {} """.format(pipes.quote(self.password))
        )
        if use_tls:
            self._findscu_str += " --tls-aes "
        self._tar2bids_list = f"{tar2bids_path}tar2bids".split()

    def get_all_pi_names(self):
        """Find all PIs the user has access to (by StudyDescription).
        Specifically, find all StudyDescriptions, take the portion before
        the caret, and return each unique value."""
        cmd = self._findscu_str + " -r StudyDescription "

        try:
            out, err, _ = _get_stdout_stderr_returncode(cmd)
        except subprocess.CalledProcessError as error:
            raise Dcm4cheError("Non-zero exit status from findscu.") from error
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
            set(pis) - set(current_app.config["DICOM_PI_BLACKLIST"])
        )

        if len(all_pis) < 1:
            raise Dcm4cheError("No PIs accessible.")

        return all_pis

    def query_single_study(
        self,
        output_fields,
        study_description=None,
        study_date=None,
        patient_name=None,
        retrieve_level="STUDY",
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
        patient_name : str, optional
            Search string for the patient names to retrieve.
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
            cmd = '{} -m StudyDescription="{}"'.format(cmd, study_description)
        if study_date is not None:
            cmd = '{} -m StudyDate="{}"'.format(
                cmd, study_date.strftime("%Y%m%d")
            )
        if patient_name is not None:
            cmd = '{} -m PatientName="{}"'.format(cmd, patient_name)

        cmd = " ".join(
            [cmd] + ["-r {}".format(field) for field in output_fields]
        )
        cmd = "{} -L {}".format(cmd, retrieve_level)

        try:
            out, err, _ = _get_stdout_stderr_returncode(cmd)
        except subprocess.CalledProcessError as error:
            raise Dcm4cheError("Non-zero exit status from findscu.") from error

        if err and err != "Picked up _JAVA_OPTIONS: -Xmx2048m\n":
            self.logger.error(err)

        output_fields = [
            "{},{}".format(field[0:4], field[4:8]).upper()
            if re.fullmatch(r"[\dabcdefABCDEF]{8}", field)
            else field
            for field in output_fields
        ]

        # Idea: Discard everything before:
        # C-FIND Request done in

        out = str(out, encoding="utf-8")
        out = out[out.find("C-FIND Request done in") :]
        out = out.split("DEBUG - Dataset")[1:]

        grouped_dicts = []
        for dataset in out:
            out_dicts = []
            for line in dataset.splitlines():
                if not any(field in line for field in output_fields):
                    continue
                match = re.match(
                    r"(\([\dABCDEF]{4},[\dABCDEF]{4}\)) "
                    + r"[A-Z]{2} \[(.*)\] (\w+)",
                    line,
                )
                if match is None:
                    continue
                out_dicts.append(
                    {
                        "tag_code": match.group(1),
                        "tag_name": match.group(3),
                        "tag_value": match.group(2),
                    }
                )
            if len(out_dicts) != len(output_fields):
                raise Dcm4cheError(
                    "Missing output fields in dataset {}".format(out_dicts)
                )
            grouped_dicts.append(out_dicts)

        return grouped_dicts

    def run_cfmm2tar(
        self, out_dir, date_str=None, patient_name=None, project=None
    ):
        """Run cfmm2tar with the given options.
        At least one of the optional search arguments must be provided.
        Arguments
        ---------
        out_dir : str
            Directory to which to download tar files.
        date_str : str, optional
            String specifying the date(s) to download. Can include up to two
            dates and a "-" to indicate an open or closed interval of dates.
        patient_name : str, optional
            PatientName string.
        project : str, optional
            "Principal^Project" to search for.
        """
        if all(arg is None for arg in [date_str, patient_name, project]):
            raise Cfmm2tarError(
                "At least one search argument must be provided."
            )
        date_query = ["-d", date_str] if date_str is not None else []
        name_query = ["-n", patient_name] if patient_name is not None else []
        project_query = ["-p", project] if project is not None else []

        with tempfile.NamedTemporaryFile(mode="w+", buffering=1) as cred_file:
            cred_file.write(self.username + "\n")
            cred_file.write(self.password + "\n")
            arg_list = (
                self.dcm4che_path.split()
                + ["cfmm2tar"]
                + ["-c", cred_file.name]
                + date_query
                + name_query
                + project_query
                + [out_dir]
            )

            try:
                out = subprocess.run(
                    arg_list,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as err:
                raise Cfmm2tarError(f"Cfmm2tar failed:\n{err.stderr}") from err

            all_out = out.stdout + out.stderr
            split_out = all_out.split("Retrieving #")[1:]

            return [
                [
                    line.split("created: ")[1]
                    for line in file_out.splitlines()
                    if any(
                        [
                            "tar file created" in line,
                            "uid file created" in line,
                        ]
                    )
                ]
                for file_out in split_out
            ]

    def run_tar2bids(
        self,
        tar_files,
        output_dir,
        patient_str=None,
        tar_str=None,
        num_cores=None,
        heuristic=None,
        temp_dir=None,
        heudiconv_options=None,
        copy_tarfiles=False,
        deface_t1w=False,
        no_heuristics=False,
    ):
        """Run tar2bids with the given arguments.
        Returns
        -------
        The given output_dir, if successful.
        """
        arg_list = (
            self._tar2bids_list
            + (["-P", patient_str] if patient_str is not None else [])
            + (["-T", tar_str] if tar_str is not None else [])
            + (["-o", output_dir])
            + (["-N", num_cores] if num_cores is not None else [])
            + (["-h", heuristic] if heuristic is not None else [])
            + (["-w", temp_dir] if temp_dir is not None else [])
            + (
                ["-o", f'"{heudiconv_options}"']
                if heudiconv_options is not None
                else []
            )
            + (["-C"] if copy_tarfiles else [])
            + (["-D"] if deface_t1w else [])
            + (["-x"] if no_heuristics else [])
            + tar_files
        )
        try:
            subprocess.run(arg_list, check=True)
        except subprocess.CalledProcessError as err:
            raise Tar2bidsError(f"Tar2bids failed:\n{err.stderr}") from err

        return output_dir


def gen_utils():
    """Generate a Dcm4cheUtils with values from the current_app config."""
    return Dcm4cheUtils(
        current_app.config["DICOM_SERVER_URL"],
        current_app.config["DICOM_SERVER_USERNAME"],
        current_app.config["DICOM_SERVER_PASSWORD"],
        current_app.config["DCM4CHE_PREFIX"],
        current_app.config["TAR2BIDS_PREFIX"],
        use_tls=current_app.config["DICOM_SERVER_TLS"],
    )


class Dcm4cheError(Exception):
    """Exception raised when something goes wrong with a dcm4che process."""

    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message


class Cfmm2tarError(Exception):
    """Exception raised when cfmm2tar fails."""

    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message


class Tar2bidsError(Exception):
    """Exception raised when tar2bids fails."""

    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message
