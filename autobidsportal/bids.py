"""Utilities for handling BIDS datasets."""

import os
from pathlib import Path
import shutil


def merge_datasets(path_incoming, path_existing):
    """Merge one BIDS dataset into another."""

    def _check_existing(dir_incoming, contents):
        ignore = []
        for file_incoming in contents:
            path_relative = (Path(dir_incoming) / file_incoming).relative_to(
                path_incoming
            )
            new_file = path_existing / path_relative
            if new_file.exists() and new_file.is_file():
                ignore.append(file_incoming)

    names_existing = {entry.name for entry in os.scandir(path_existing)}
    for entry in os.scandir(path_incoming):
        if entry.name == "code":
            continue
        if entry.isdir():
            shutil.copytree(
                entry.path,
                path_existing,
                ignore=_check_existing,
                dirs_exist_ok=True,
            )
        elif entry.isfile() and (entry.name not in names_existing):
            shutil.copy2(entry.path, path_existing)
