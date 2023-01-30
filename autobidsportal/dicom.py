"""Handle qureyng DICOM server for records related to specific studies."""

import re

from autobidsportal.dcm4cheutils import gen_utils, DicomQueryAttributes


ATTRIBUTES_QUERIED = [
    "0020000D",  # StudyInstanceUID
    "00100010",  # PatientName
    "0008103E",  # SeriesDescription
    "00200011",  # SeriesNumber
    "00200010",  # StudyID
    "00100020",  # PatientID
    "00100040",  # PatientSex
]


def get_inclusion_records(uids_included):
    """Get DICOM records from a list of StudyInstanceUIDs.

    Parameters
    ----------
    uids_included : list of str
        A list of StudyInstanceUIDs corresponding to records to grab from
        the DICOM server.

    Returns
    -------
    list of dict
        A list of dictionaries with patient-level attributes and a
        list of sub-dictionaries with study-level attributes.
    """
    if not uids_included:
        return []
    responses_flat = rearrange_response(
        gen_utils().query_single_study(
            ATTRIBUTES_QUERIED,
            DicomQueryAttributes(study_instance_uids=uids_included),
            retrieve_level="SERIES",
        )
    )
    patient_info = {
        (
            response["PatientID"],
            response["PatientName"],
            response["PatientSex"],
            response["StudyID"],
            response["StudyInstanceUID"],
        )
        for response in responses_flat
    }
    return organize_flat_responses(responses_flat, patient_info)


def get_description_records(study, date=None, description=None):
    """Get DICOM records from a study's query parameters.

    Parameters
    ----------
    study : Study
        Study to take parameters from.
    date : date, optional
        Date to grab studies from.
    description : str, optional
        "{PI Name}^{Study Name}", StudyDescription to query.

    Returns
    -------
    list of dict
        A list of dictionaries with patient-level attributes and a
        list of sub-dictionaries with study-level attributes.
    """
    uids_excluded = [
        explicit_patient.study_instance_uid
        for explicit_patient in study.explicit_patients
        if not explicit_patient.included
    ]
    if (date is None) and study.retrospective_data:
        start = study.retrospective_start
        end = study.retrospective_end
    else:
        start = None
        end = None
    responses_description = rearrange_response(
        gen_utils().query_single_study(
            ATTRIBUTES_QUERIED,
            DicomQueryAttributes(
                study_description=description,
                study_date=date,
                date_range_start=start,
                date_range_end=end,
                patient_name=study.patient_str,
            ),
            retrieve_level="SERIES",
        )
    )
    patient_info_description = {
        (
            response["PatientID"],
            response["PatientName"],
            response["PatientSex"],
            response["StudyID"],
            response["StudyInstanceUID"],
        )
        for response in responses_description
        if re.fullmatch(
            (
                study.patient_name_re
                if study.patient_name_re is not None
                else ".*"
            ),
            response["PatientName"],
        )
        and (response["StudyInstanceUID"] not in uids_excluded)
    }
    return organize_flat_responses(
        responses_description, patient_info_description
    )


def get_study_records(study, date=None, description=None):
    """Get all records related to a study.

    This includes studies explicitly included by StudyInstanceUID and studies
    discovered by the search parameters.

    Parameters
    ----------
    study : Study
        Study to draw included UIDs and search params from.
    date : date
        Date to narrow down the search.
    description : str
        "{PI Name}^{Study Name}", study description to narrow down the search.


    Returns
    -------
    list of dict
        A list of dictionaries with patient-level attributes and a
        list of sub-dictionaries with study-level attributes.
    """
    uids_included = {
        explicit_patient.study_instance_uid
        for explicit_patient in study.explicit_patients
        if explicit_patient.included
    }
    inclusion_records = get_inclusion_records(list(uids_included))
    description_records = get_description_records(study, date, description)
    return inclusion_records + [
        record
        for record in description_records
        if record["StudyInstanceUID"] not in uids_included
    ]


def rearrange_response(dicom_response):
    """Rearrange a list of lists of dicts from dcm4cheutils.

    Parameters
    ----------
    dicom_response : list of list of dicts
        DICOM query response from dcm4cheutils.

    Returns
    -------
    list of dicts
        Rearranged DICOM query response where each dict's key is an attribute
        and its corresponding value is the value of that attribute.
    """
    return [
        {
            attribute["tag_name"]: attribute["tag_value"]
            for attribute in response
        }
        for response in dicom_response
    ]


def organize_flat_responses(responses, patient_info):
    """Organize a flat list of DICOM responses to a hierarchical structure.

    Parameters
    ----------
    responses : list of dict
        Flat responses corresponding to every series
    patient_info : set of tuple
        Tuple of patient info for every StudyInstanceUID in the response.

    Returns
    -------
    list of dict
        A list of dictionaries with patient-level attributes and a
        list of sub-dictionaries with study-level attributes.
    """
    return [
        {
            "PatientName": patient_name,
            "PatientID": patient_id,
            "PatientSex": patient_sex,
            "StudyID": study_id,
            "StudyInstanceUID": study_uid,
            "series": sorted(
                [
                    {
                        "SeriesNumber": response["SeriesNumber"],
                        "SeriesDescription": response["SeriesDescription"],
                    }
                    for response in responses
                    if response["StudyInstanceUID"] == study_uid
                ],
                key=lambda series_dict: f'{int(series_dict["SeriesNumber"]):03d}',
            ),
        }
        for (
            patient_id,
            patient_name,
            patient_sex,
            study_id,
            study_uid,
        ) in patient_info
    ]
