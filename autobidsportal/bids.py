"""Utilities for handling BIDS datasets."""
from __future__ import annotations

import csv
import os
import shutil
from collections.abc import Sequence
from pathlib import Path


def _check_existing(
    path_incoming: Path,
    path_existing: Path,
    dir_incoming: str,
    contents: Sequence[os.PathLike[str] | str],
) -> list[str]:
    """Check if file already exists.

    Parameters
    ----------
    path_incoming
        Directory containing "new", incoming files

    path_existing
        Path containing existing files

    dir_incoming
        Sub-directory of path_incoming to be copied

    contents
        List of files to check

    Returns
    -------
    list[str]
        List of paths to ignore as file already exists
    """
    # Files that already exists and should be ignored
    ignore = []

    for file_incoming in contents:
        # Determine relative path
        path_relative = (Path(dir_incoming) / file_incoming).relative_to(
            path_incoming,
        )
        new_file = path_existing / path_relative

        # Add to ignore list if new file already exists or is a symlink
        if (new_file.exists() and new_file.is_file()) or new_file.is_symlink():
            ignore.append(file_incoming)

    return ignore


def merge_datasets(path_incoming: Path, path_existing: Path):
    """Merge one BIDS dataset into another.

    Parameters
    ----------
    path_incoming
        Path to incoming "new" BIDS dataset

    path_existing
        Path to existing BIDS dataset
    """

    def _ignore(
        dir_incoming: str,
        contents: Sequence[os.PathLike[str] | str],
    ) -> list[str]:
        """Check existance of existing entries (internal function).

        Parameters
        ----------
        dir_incoming
            Directory of incoming BIDS dataset

        contents
            List of files to check

        Returns
        -------
        List[str]
            List of existing files to ignore when merging
        """
        return _check_existing(
            path_incoming,
            path_existing,
            dir_incoming,
            contents,
        )

    # Get names of items in existing dataset
    names_existing = {entry.name for entry in os.scandir(path_existing)}

    # Loop through each item found in incoming dataset, acting only on
    # directories and files
    for entry in os.scandir(path_incoming):
        if entry.name == "code":
            continue

        # Copy entries to existing dataset and remove from source
        if entry.is_dir():
            shutil.copytree(
                entry.path,
                path_existing / entry.name,
                ignore=_ignore,
                dirs_exist_ok=True,
            )
            shutil.rmtree(entry.path)
        elif entry.is_file() and (entry.name not in names_existing):
            shutil.copy2(entry.path, path_existing)
            Path(entry.path).unlink()

    # Merge existing participants.tsv files
    if (path_incoming / "participants.tsv").exists():
        merge_participants_tsv(
            path_incoming / "participants.tsv",
            path_existing / "participants.tsv",
        )


def merge_participants_tsv(
    tsv_incoming: os.PathLike[str] | str,
    tsv_existing: os.PathLike[str] | str,
):
    """Merge an incoming participants.tsv file with an existing one.

    Parameters
    ----------
    tsv_incoming
        tsv file containing "new" participants of a dataset

    tsv_existing
        tsv file containing existing participants of a dataset
    """
    # Read incoming and existing participants into two separate lists
    with open(
        tsv_incoming,
        "r+",
        encoding="utf-8",
        newline="",
    ) as file_incoming, open(
        tsv_existing,
        "r+",
        encoding="utf-8",
        newline="",
    ) as file_existing:
        list_incoming = list(csv.reader(file_incoming, delimiter="\t"))
        list_existing = list(csv.reader(file_existing, delimiter="\t"))

    # Grab existing participant ids
    subjects_existing = {row[0] for row in list_existing}

    # Grab incoming participant ids (skipping header row)
    for line_incoming in list_incoming[1:]:
        # If participant id already exists, skip
        if line_incoming[0] in subjects_existing:
            continue
        list_existing.append(line_incoming)

    # Format lines and add header if necessary
    to_write = ["\t".join(row) + "\n" for row in list_existing]
    if not list_existing[0][0].startswith("participant_id"):
        to_write = ["participant_id\n", *to_write]

    # Write to file
    with open(
        tsv_existing,
        "w",
        encoding="utf-8",
        newline="",
    ) as file_existing:
        file_existing.writelines(to_write)
