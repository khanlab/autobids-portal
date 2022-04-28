"""Handle interaction with datalad datasets."""

import os
from pathlib import Path
import shutil
import tempfile

from datalad import api as datalad_api
from datalad.support.annexrepo import AnnexRepo
from flask import current_app

from autobidsportal.models import (
    db,
    DatasetType,
    DataladDataset,
    SiblingHost,
    ExternalSibling,
)


class RiaDataset:
    """Context manager to clone/create a local RIA dataset."""

    def __init__(self, parent, alias):
        self.parent = parent
        self.alias = alias
        self.path_dataset = None

    def __enter__(self):
        self.path_dataset = Path(self.parent) / self.alias
        clone_ria_dataset(str(self.path_dataset), self.alias)
        return self.path_dataset

    def __exit__(self, exc_type, exc_value, traceback):
        remove_finalized_dataset(self.path_dataset)


def get_alias(study_id, dataset_type):
    """Generate an alias for a study in the RIA.

    Parameters
    ----------
    study_id : int
        ID of the study.
    dataset_type: DatasetType
        "tar2bids" or "cfmm2tar".
    """
    if dataset_type is DatasetType.SOURCE_DATA:
        text = "sourcedata"
    elif dataset_type is DatasetType.RAW_DATA:
        text = "rawdata"
    elif dataset_type is DatasetType.DERIVED_DATA:
        text = "deriveddata"
    else:
        raise TypeError()
    return f"study-{study_id}_{text}"


def ensure_dataset_exists(study_id, dataset_type):
    """Check whether a dataset is in the RIA store, and create it if not."""
    dataset = DataladDataset.query.filter_by(
        study_id=study_id, dataset_type=dataset_type
    ).one_or_none()
    if dataset is None:
        alias = get_alias(study_id, dataset_type)
        with tempfile.TemporaryDirectory(
            dir=current_app.config["CFMM2TAR_DOWNLOAD_DIR"]
        ) as dir_temp:
            create_ria_dataset(str(Path(dir_temp) / alias), alias)
        dataset = DataladDataset(
            study_id=study_id, dataset_type=dataset_type, ria_alias=alias
        )
        db.session.add(dataset)
        db.session.commit()
    return dataset


def ensure_siblings_exist(dataset):
    generated_siblings = set()
    if (current_app.config["AUTOBIDS_GITHUB_ACTIVE"]) and not any(
        sibling.host is SiblingHost.GITHUB
        for sibling in dataset.external_siblings
    ):
        with tempfile.TemporaryDirectory(
            dir=current_app.config["CFMM2TAR_DOWNLOAD_DIR"]
        ) as dir_temp, RiaDataset(dir_temp, dataset.ria_alias) as dataset_ria:
            url = create_sibling_github(
                dataset_ria.path_dataset, dataset.ria_alias, exists_ok=False
            )
            datalad_api.push(dataset=dataset_ria.path_dataset, to="github")
            sibling = ExternalSibling(
                dataset_id=dataset.id, url=url, host=SiblingHost.GITHUB
            )
            db.session.add(sibling)
            db.session.commit()
        generated_siblings.add(sibling)


#    if current_app.config["AUTOBIDS_GITLAB_ACTIVE"] and not any(
#        current_app.config["AUTOBIDS_GITLAB_URL"] in sibling.url
#        for sibling in dataset.external_siblings
#    ):
#        with tempfile.TemporaryDirectory(
#            dir=current_app.config["CFMM2TAR_DOWNLOAD_DIR"]
#        ) as dir_temp, RiaDataset(dir_temp, dataset.ria_alias) as dataset_ria:
#            url = create_sibling_gitlab(
#                dataset_ria.path_dataset, dataset.ria_alias
#            )
#            datalad_api.push(dataset=dataset_ria.path_dataset, to="gitlab")
#            db.session.add(ExternalSibling(dataset_id=dataset.id, url=url))
#
#
def push_to_siblings(path, dataset):
    for sibling in dataset.external_siblings:
        if sibling.host is SiblingHost.GITHUB:
            create_sibling_github(
                path, sibling.dataladdataset.ria_alias, exists_ok=True
            )
            datalad_api.push(dataset=path, to="github")


#       elif sibling.host == "GitLab":
#           create_sibling_gitlab(
#               path, sibling.dataladdataset.ria_atlas, exists_ok=True
#           )
#           datalad_api.push(dataset=path, to="gitlab")


def create_ria_dataset(path, alias):
    """Create a dataset in the configured RIA store."""
    datalad_api.create(path, cfg_proc="text2git")
    datalad_api.create_sibling_ria(
        current_app.config["DATALAD_RIA_URL"],
        "origin",
        dataset=path,
        alias=alias,
        new_store_ok=True,
    )
    push_dataset(str(path))


def create_sibling_github(path, name, exists_ok=False):
    """Create a github sibling for a dataset.

    Parameters
    ----------
    path : str
        Path at which the dataset exists.
    name : str
        Name for the dataset on Github (can contain an organization)
    """
    return datalad_api.create_sibling_github(
        name,
        dataset=path,
        api=current_app.config["AUTOBIDS_GITHUB_API"],
        credential=current_app.config["AUTOBIDS_GITHUB_CREDENTIAL"],
        existing="reconfigure" if exists_ok else "error",
    )[0]["clone_url"]


# def create_sibling_gitlab(path, alias, exists_ok=False):
#    return datalad_api.create_sibling_gitlab(
#        project=alias,
#        dataset=path,
#        existing="reconfigure" if exists_ok else "error",
#    )[0]["clone_url"]


def clone_ria_dataset(path, alias):
    """Clone the configures tar files dataset to a given location."""
    current_app.logger.info("Cloning tar files dataset to %s", path)
    datalad_api.clone(
        "".join(
            [
                current_app.config["DATALAD_RIA_URL"],
                "#~",
                alias,
            ]
        ),
        path=str(path),
    )


def delete_tar_file(study_id, tar_file):
    """Delete a tar file from the configured tar files dataset."""
    dataset = DataladDataset.query.filter_by(
        study_id=study_id, dataset_type=DatasetType.SOURCE_DATA
    ).first_or_404()
    with tempfile.TemporaryDirectory(
        dir=current_app.config["CFMM2TAR_DOWNLOAD_DIR"]
    ) as download_dir, RiaDataset(
        download_dir, dataset.ria_alias
    ) as path_dataset:
        to_delete = str(path_dataset / tar_file)
        current_app.logger.info("Removing %s", to_delete)
        datalad_api.remove(
            path=to_delete,
            dataset=str(path_dataset),
            message=f"Remove {Path(to_delete).name}",
        )
        push_dataset(str(path_dataset))


def delete_all_content(path_dataset):
    """Delete everything in a dataset and save."""
    for entry in os.scandir(path_dataset):
        if entry.name not in {".git", ".datalad", ".dataladattributes"}:
            if entry.is_file():
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
