"""Test server for interacting with Cfmm2tar"""

import pathlib
from collections import OrderedDict
import re

from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.filewriter import write_file_meta_info
from pynetdicom import (
    AE,
    debug_logger,
    evt,
    AllStoragePresentationContexts,
    ALL_TRANSFER_SYNTAXES,
)
from pynetdicom.sop_class import (
    StudyRootQueryRetrieveInformationModelGet,
    StudyRootQueryRetrieveInformationModelFind,
)

debug_logger()


_STUDY_ROOT_ATTRIBUTES = OrderedDict(
    {
        "STUDY": [
            "StudyInstanceUID",
            "StudyDate",
            "StudyTime",
            "StudyDescription",
            "AccessionNumber",
            "StudyID",
            "PatientID",
            "PatientName",
            "PatientSex",
        ],
        "SERIES": [
            "SeriesInstanceUID",
            "Modality",
            "SeriesNumber",
            "SequenceName",
            "RepetitionTime",
            "EchoTime",
            "ProtocolName",
            "SeriesDescription",
        ],
        "IMAGE": ["SOPInstanceUID", "InstanceNumber"],
    }
)


def handle_store(event, storage_dir):
    """Handle EVT_C_STORE events."""
    storage_dir_path = pathlib.Path(storage_dir)
    if not storage_dir_path.exists():
        storage_dir_path.mkdir(parents=True)

    fname = storage_dir_path / event.request.AffectedSOPInstanceUID
    with open(fname, "wb") as out_file:
        out_file.write(b"\x00" * 128)
        out_file.write(b"DICM")
        write_file_meta_info(out_file, event.file_meta)
        out_file.write(event.request.DataSet.getvalue())

    return 0x0000


def find_instances(dataset, storage_dir):
    """Find all instances matching a search string."""
    storage_dir_path = pathlib.Path(storage_dir)
    matching = [dcmread(file_path) for file_path in storage_dir_path.iterdir()]

    for level, keywords in _STUDY_ROOT_ATTRIBUTES.items():
        keywords = [keyword for keyword in keywords if keyword in dataset]
        print(f"Keywords: {keywords}")

        for keyword in keywords:
            all_search = getattr(dataset, keyword)
            if not isinstance(all_search, list):
                all_search = [all_search]
            print(f"{keyword}: {all_search}")
            for search in all_search:
                if search is None:
                    pass
                elif str(search) in ["", "*"]:
                    pass
                else:
                    matching = [inst for inst in matching if keyword in inst]
                    search = (
                        re.escape(str(search))
                        .replace("\\?", ".")
                        .replace("\\*", ".*")
                    )
                    matching = [
                        inst
                        for inst in matching
                        if re.fullmatch(search, str(getattr(inst, keyword)))
                        is not None
                    ]

        if level == dataset.QueryRetrieveLevel:
            break

    return matching


def handle_find(event, storage_dir):
    """Handle a C-FIND request event."""
    dataset = event.identifier

    if "QueryRetrieveLevel" not in dataset:
        yield 0xC000, None
        return

    matching = find_instances(dataset, storage_dir)
    print(f"Matching: {matching}")

    for instance in matching:
        if event.is_cancelled:
            yield (0xFE00, None)
            return
        all_keywords = []
        for level, keywords in _STUDY_ROOT_ATTRIBUTES.items():
            all_keywords.extend(keywords)
            if level == dataset.QueryRetrieveLevel:
                break

        identifier = Dataset()
        for keyword in [
            keyword for keyword in all_keywords if keyword in dataset
        ]:
            print(f"Setting {keyword}")
            if keyword in instance:
                setattr(identifier, keyword, getattr(instance, keyword))
            else:
                setattr(identifier, keyword, None)
        identifier.QueryRetrieveLevel = dataset.QueryRetrieveLevel

        yield (0xFF00, identifier)


def handle_get(event, storage_dir):
    """Handle a C-GET request event."""
    dataset = event.identifier

    if "QueryRetrieveLevel" not in dataset:
        yield 0xC000, None
        return

    matching = find_instances(dataset, storage_dir)

    yield len(matching)

    for instance in matching:
        if event.is_cancelled:
            yield (0xFE00, None)
            return
        yield (0xFF00, instance)


def gen_application_entity(storage_dir):
    """Generate an application entity for Q/R SCPs.

    Returns
    -------
    AE
        The pynetdicom application entity.
    list of tuple
        The handlers to be associated with the application entity.
    """
    handlers = [
        (evt.EVT_C_STORE, handle_store, [storage_dir]),
        (evt.EVT_C_FIND, handle_find, [storage_dir]),
        (evt.EVT_C_GET, handle_get, [storage_dir]),
    ]

    application_entity = AE()
    storage_sop_classes = [
        cx.abstract_syntax for cx in AllStoragePresentationContexts
    ]
    for uid in storage_sop_classes:
        application_entity.add_supported_context(uid, ALL_TRANSFER_SYNTAXES)
    for context in application_entity.supported_contexts:
        context.scp_role = True
        context.scu_role = False
    application_entity.add_supported_context(
        StudyRootQueryRetrieveInformationModelGet
    )
    application_entity.add_supported_context(
        StudyRootQueryRetrieveInformationModelFind
    )

    return application_entity, handlers
