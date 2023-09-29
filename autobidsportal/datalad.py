"""Handle interaction with datalad datasets.

Dev note: datalad does not ship with type information, causing pyright to fail
This is actively being on (see: https://github.com/datalad/datalad/issues/6884)
"""

import os
import shutil
import tempfile
from pathlib import Path

from datalad import api as datalad_api
from datalad.support.annexrepo import AnnexRepo
from flask import current_app

from autobidsportal.models import DataladDataset, DatasetType, Study, db


class RiaDataset:
    """Context manager to clone/create a local RIA dataset."""

    def __init__(self, parent: str, alias: str, ria_url: str | None = None):
        """Set up attrs for the dataset.

        Parameters
        ----------
        parent
            Parent directory to store the dataset in

        alias
            Study alias in the RIA

        ria_url
            Path to RIA store
        """
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

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: type[BaseException] | None,
    ):
        """Clean up the finalized dataset.

        Note: Arguments provided for exception handling, but not used
        """
        remove_finalized_dataset(self.path_dataset)


def get_alias(study_id: int, dataset_type: DatasetType):
    """Generate an alias for a study in the RIA.

    Parameters
    ----------
    study_id
        ID of the study

    dataset_type
        "tar2bids" or "cfmm2tar"
    """
    text = dataset_type.to_bids_str()

    return f"study-{study_id}_{text}"


def ensure_dataset_exists(study_id: int, dataset_type: DatasetType):
    """Check whether a dataset is in the RIA store, and create it if not.

    Parameters
    ----------
    study_id
        ID of the study

    dataset_type
        "tar2bids" or "cfmm2tar"
    """
    # Get study by ID
    study = Study.query.get(study_id)

    # Grab dataset
    dataset = DataladDataset.query.filter_by(
        study_id=study_id,
        dataset_type=dataset_type,
    ).one_or_none()

    # If it does not exist, create it
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

        # Add dataset to db
        db.session.add(dataset)  # pyright: ignore
        db.session.commit()  # pyright: ignore

    return dataset


def create_ria_dataset(path: str, alias: str, ria_url: str | None = None):
    """Create a dataset in the configured RIA store.

    Parameters
    ----------
    path
        Path where dataset will be created

    alias
        Study alias in the RIA

    ria_url
        Path to RIA store
    """
    datalad_api.create(path, cfg_proc="text2git")  # pyright: ignore
    datalad_api.create_sibling_ria(  # pyright: ignore
        ria_url
        if ria_url is not None
        else current_app.config["DATALAD_RIA_URL"],
        "origin",
        dataset=path,
        alias=alias,
        new_store_ok=True,
    )
    push_dataset(str(path))


def clone_ria_dataset(path: str, alias: str, ria_url: str | None = None):
    """Clone the configures tar files dataset to a given location.

    Parameters
    ----------
    path
        Path where dataset will be created

    alias
        Study alias in the RIA

    ria_url
        Path to RIA
    """
    current_app.logger.info(f"Cloning tar files dataset to {path}")
    datalad_api.clone(  # pyright: ignore
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


def delete_tar_file(study_id: int, tar_file: str):
    """Delete a tar file from the configured tar files dataset.

    Parameters
    ----------
    study_id
        ID of the study

    tar_file
        Name of tar file to be deleted
    """
    # Query for study dataset to be deleted
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
        datalad_api.remove(  # pyright: ignore
            path=to_delete,
            dataset=str(path_dataset),
            message=f"Remove {Path(to_delete).name}",
        )
        push_dataset(str(path_dataset))


def rename_tar_file(
    study_id: int,
    tar_file: str,
    new_name: os.PathLike[str] | str,
):
    """Rename a single tar file and push the results.

    Parameters
    ----------
    study_id
        ID of the study

    tar_file
        Name of tar file to be renamed

    new_name
        New name to be given to dataset
    """
    # Query for study dataset
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


def delete_all_content(path_dataset: Path):
    """Delete everything in a dataset and save.

    Parameters
    ----------
    path_dataset
        Path of dataset to be deleted

    """
    for entry in os.scandir(path_dataset):
        # Only remove non-git / datalad metadata files
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


def get_tar_file_from_dataset(tar_file: str, path_dataset: str):
    """Get a tar file from a dataset.

    Parameters
    ----------
    path_dataset
        Path to associated dataset

    tar_file
        Name of tar file to be deleted
    """
    full_path = str(Path(path_dataset) / tar_file)
    datalad_api.get(  # pyright: ignore
        path=full_path,
        dataset=str(path_dataset),
    )

    return full_path


def get_all_dataset_content(path_dataset: str):
    """Get all files (non-recursively) in a datalad dataset.

    Parameters
    ----------
    path_dataset
        Path of datalad dataset
    """
    datalad_api.get(dataset=path_dataset)  # pyright: ignore


def archive_dataset(
    path_dataset: os.PathLike[str] | str,
    path_out: os.PathLike[str] | str,
):
    """Archive a dataset to a given path.

    Parameters
    ----------
    path_dataset
        Path of datalad dataset

    path_out
        Path where archive is to be saved
    """
    get_all_dataset_content(str(path_dataset))
    datalad_api.export_archive(  # pyright: ignore
        filename=str(path_out),
        dataset=str(path_dataset),
        archivetype="zip",
    )


def finalize_dataset_changes(path: os.PathLike[str] | str, message: str):
    """Save a dataset's changes and push them back to the origin sibling.

    path
        Path of datalad dataset

    message
        Commit message when saving changes
    """
    datalad_api.save(dataset=str(path), message=message)  # pyright: ignore
    push_dataset(str(path))


def push_dataset(path_dataset: os.PathLike[str] | str):
    """Declare a dataset dead and push it to its origin sibling.

    Parameters
    ----------
    path_dataset
        Path to dataset
    """
    current_app.logger.info("Marking tar file dataset dead.")
    AnnexRepo(str(path_dataset)).set_remote_dead("here")

    current_app.logger.info("Pushing tar file dataset to RIA store.")
    datalad_api.push(  # pyright: ignore
        dataset=str(path_dataset),
        data="anything",
        to="origin",
    )


def remove_finalized_dataset(path: os.PathLike[str] | str | None):
    """Remove a dataset from the filesystem.

    Parameters
    ----------
    path
        Path to dataset
    """
    datalad_api.remove(  # pyright: ignore
        dataset=str(path),
        reckless="modification",
    )
