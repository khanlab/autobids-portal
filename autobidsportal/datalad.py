"""Handle interaction with datalad datasets."""

import os
import shutil
import tempfile
from pathlib import Path

from datalad import api as datalad_api
from datalad.support.annexrepo import AnnexRepo
from flask import current_app

from autobidsportal.models import (
    DataladDataset,
    DatasetType,
    Study,
    db,
)


class RiaDataset:
    """Context manager to clone/create a local RIA dataset."""

    def __init__(self, parent, alias, ria_url=None) -> None:
        """Set up attrs for the dataset."""
        self.parent = parent
        self.alias = alias
        self.path_dataset = None
        self.ria_url = (
            ria_url
            if ria_url is not None
            else current_app.config["DATALAD_RIA_URL"]
        )

    def __enter__(self):
        """Clone the dataset and return its path."""
        self.path_dataset = Path(self.parent) / self.alias
        clone_ria_dataset(
            str(self.path_dataset),
            self.alias,
            ria_url=self.ria_url,
        )
        return self.path_dataset

    def __exit__(self, exc_type, exc_value, traceback):
        """Clean up the finalized dataset."""
        remove_finalized_dataset(self.path_dataset)


def get_alias(study_id, dataset_type):
    """Generate an alias for a study in the RIA.

    Parameters
    ----------
    study_id : int
        ID of the study.
    dataset_type: DatasetType
        "tar2bids" or "cfmm2tar".

    Raises
    ------
    TypeError
        If dataset_type is not DatasetType
    """
    if dataset_type is DatasetType.SOURCE_DATA:
        text = "sourcedata"
    elif dataset_type is DatasetType.RAW_DATA:
        text = "rawdata"
    elif dataset_type is DatasetType.DERIVED_DATA:
        text = "deriveddata"
    else:
        raise TypeError
    return f"study-{study_id}_{text}"


def ensure_dataset_exists(study_id, dataset_type):
    """Check whether a dataset is in the RIA store, and create it if not."""
    dataset = DataladDataset.query.filter_by(
        study_id=study_id,
        dataset_type=dataset_type,
    ).one_or_none()
    study = Study.query.get(study_id)
    if dataset is None:
        alias = get_alias(study_id, dataset_type)
        with tempfile.TemporaryDirectory(
            dir=current_app.config["CFMM2TAR_DOWNLOAD_DIR"],
        ) as dir_temp:
            create_ria_dataset(
                str(Path(dir_temp) / alias),
                alias,
                ria_url=study.custom_ria_url,
            )
        dataset = DataladDataset(
            study_id=study_id,
            dataset_type=dataset_type,
            ria_alias=alias,
            custom_ria_url=study.custom_ria_url,
        )
        db.session.add(dataset)
        db.session.commit()
    return dataset


def create_ria_dataset(path, alias, ria_url=None):
    """Create a dataset in the configured RIA store."""
    datalad_api.create(path, cfg_proc="text2git")
    datalad_api.create_sibling_ria(
        ria_url
        if ria_url is not None
        else current_app.config["DATALAD_RIA_URL"],
        "origin",
        dataset=path,
        alias=alias,
        new_store_ok=True,
    )
    push_dataset(str(path))


def clone_ria_dataset(path, alias, ria_url=None):
    """Clone the configures tar files dataset to a given location."""
    current_app.logger.info("Cloning tar files dataset to %s", path)
    datalad_api.clone(
        "".join(
            [
                ria_url
                if ria_url is not None
                else current_app.config["DATALAD_RIA_URL"],
                "#~",
                alias,
            ],
        ),
        path=str(path),
        reckless="ephemeral",
    )


def delete_tar_file(study_id, tar_file):
    """Delete a tar file from the configured tar files dataset."""
    dataset = DataladDataset.query.filter_by(
        study_id=study_id,
        dataset_type=DatasetType.SOURCE_DATA,
    ).first_or_404()
    with tempfile.TemporaryDirectory(
        dir=current_app.config["CFMM2TAR_DOWNLOAD_DIR"],
    ) as download_dir, RiaDataset(
        download_dir,
        dataset.ria_alias,
        ria_url=dataset.custom_ria_url,
    ) as path_dataset:
        to_delete = str(path_dataset / tar_file)
        current_app.logger.info("Removing %s", to_delete)
        datalad_api.remove(
            path=to_delete,
            dataset=str(path_dataset),
            message=f"Remove {Path(to_delete).name}",
        )
        push_dataset(str(path_dataset))


def rename_tar_file(study_id, tar_file, new_name):
    """Rename a single tar file and push the results."""
    dataset = DataladDataset.query.filter_by(
        study_id=study_id,
        dataset_type=DatasetType.SOURCE_DATA,
    ).first_or_404()
    with tempfile.TemporaryDirectory(
        dir=current_app.config["CFMM2TAR_DOWNLOAD_DIR"],
    ) as download_dir, RiaDataset(
        download_dir,
        dataset.ria_alias,
        ria_url=dataset.custom_ria_url,
    ) as path_dataset:
        to_rename = path_dataset / tar_file
        new_name = path_dataset / Path(new_name).name
        current_app.logger.info(
            "Renaming %s to %s",
            str(to_rename),
            str(new_name),
        )
        to_rename.rename(new_name)
        finalize_dataset_changes(
            str(path_dataset),
            f"Rename {to_rename} to {new_name}",
        )


def delete_all_content(path_dataset):
    """Delete everything in a dataset and save."""
    for entry in os.scandir(path_dataset):
        if entry.name not in {
            ".git",
            ".gitattributes",
            ".datalad",
            ".dataladattributes",
        }:
            if entry.is_file() or entry.is_symlink():
                Path(entry.path).unlink()
            elif entry.is_dir():
                shutil.rmtree(entry.path)
    finalize_dataset_changes(path_dataset, "Wipe dataset contents.")


def get_tar_file_from_dataset(tar_file, path_dataset):
    """Get a tar file from a dataset."""
    full_path = str(Path(path_dataset) / tar_file)
    datalad_api.get(path=full_path, dataset=str(path_dataset))
    return full_path


def get_all_dataset_content(path_dataset):
    """Get all files (non-recursively) in a datalad dataset."""
    datalad_api.get(dataset=path_dataset)


def archive_dataset(path_dataset, path_out):
    """Archive a dataset to a given path."""
    get_all_dataset_content(str(path_dataset))
    datalad_api.export_archive(
        filename=str(path_out),
        dataset=str(path_dataset),
        archivetype="zip",
    )


def finalize_dataset_changes(path, message):
    """Save a dataset's changes and push them back to the origin sibling."""
    datalad_api.save(dataset=str(path), message=message)
    push_dataset(str(path))


def push_dataset(path_dataset):
    """Declare a dataset dead and push it to its origin sibling."""
    current_app.logger.info("Marking tar file dataset dead.")
    AnnexRepo(str(path_dataset)).set_remote_dead("here")
    current_app.logger.info("Pushing tar file dataset to RIA store.")
    datalad_api.push(dataset=str(path_dataset), data="anything", to="origin")


def remove_finalized_dataset(path):
    """Remove a dataset from the filesystem."""
    datalad_api.remove(dataset=str(path), reckless="modification")
