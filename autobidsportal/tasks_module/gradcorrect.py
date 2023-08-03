"""Tasks for running gradcorrect on BIDS datasets."""

import tempfile
from collections.abc import Iterable
from os import PathLike

from autobidsportal.apptainer import apptainer_exec
from autobidsportal.datalad import (
    RiaDataset,
    ensure_dataset_exists,
    finalize_dataset_changes,
    get_tar_file_from_dataset,
)
from autobidsportal.models import DatasetType
from autobidsportal.tasks import app


def run_gradcorrect(
    path_dataset_raw: PathLike[str] | str,
    path_out: PathLike[str] | str,
    subject_ids: Iterable[str] | None,
) -> None:
    """Run gradcorrect on a BIDS dataset, optionally on a subset of subjects."""
    participant_label = (
        ["--participant_label", *subject_ids] if subject_ids else []
    )
    apptainer_exec(
        [
            "gradcorrect",
            str(path_dataset_raw),
            str(path_out),
            *participant_label,
        ],
        app.config["GRADCORRECT_PATH"],
        app.config["GRADCORRECT_BINDS"],
    )


def gradcorrect_study(study_id: int, subject_labels: Iterable[str]) -> None:
    """Run gradcorrect on a set of subjects in a study."""
    dataset_bids = ensure_dataset_exists(study_id, DatasetType.RAW_DATA)
    dataset_derivatives = ensure_dataset_exists(
        study_id,
        DatasetType.DERIVED_DATA,
    )
    with tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as bids_dir, tempfile.TemporaryDirectory(
        dir=app.config["TAR2BIDS_DOWNLOAD_DIR"],
    ) as derivatives_dir, RiaDataset(
        derivatives_dir,
        dataset_derivatives.ria_alias,
        ria_url=dataset_derivatives.custom_ria_url,
    ) as path_dataset_derivatives:
        with RiaDataset(
            bids_dir,
            dataset_bids.ria_alias,
            ria_url=dataset_bids.custom_ria_url,
        ) as path_dataset_bids:
            for subject_label in subject_labels:
                get_tar_file_from_dataset(
                    f"sub-{subject_label}",
                    path_dataset_bids,
                )
            run_gradcorrect(
                bids_dir,
                path_dataset_derivatives / "gradcorrect",
                subject_labels,
            )
        finalize_dataset_changes(
            str(path_dataset_derivatives),
            "Run gradcorrect on subjects {','.join(subject_labels}",
        )
