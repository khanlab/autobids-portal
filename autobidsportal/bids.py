"""Utilities for handling BIDS datasets."""

import csv
import os
from pathlib import Path
import shutil


def _check_existing(path_incoming, path_existing, dir_incoming, contents):
    ignore = []
    for file_incoming in contents:
        path_relative = (Path(dir_incoming) / file_incoming).relative_to(
            path_incoming
        )
        new_file = path_existing / path_relative
        if new_file.exists() and new_file.is_file():
            ignore.append(file_incoming)
    return ignore


def merge_datasets(path_incoming, path_existing):
    """Merge one BIDS dataset into another."""

    def _ignore(dir_incoming, contents):
        return _check_existing(
            path_incoming, path_existing, dir_incoming, contents
        )

    names_existing = {entry.name for entry in os.scandir(path_existing)}
    for entry in os.scandir(path_incoming):
        if entry.name == "code":
            continue
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
    if (path_incoming / "participants.tsv").exists():
        merge_participants_tsv(
            path_incoming / "participants.tsv",
            path_existing / "participants.tsv",
        )


def merge_participants_tsv(tsv_incoming, tsv_existing):
    """Merge an incoming participants.tsv file with an existing one."""
    with open(
        tsv_incoming, "r+", encoding="utf-8", newline=""
    ) as file_incoming, open(
        tsv_existing, "r+", encoding="utf-8", newline=""
    ) as file_existing:
        list_incoming = list(csv.reader(file_incoming, delimiter="\t"))
        list_existing = list(csv.reader(file_existing, delimiter="\t"))
    subjects_existing = {row[0] for row in list_existing}
    for line_incoming in list_incoming[1:]:
        subject_incoming = line_incoming[0]
        if subject_incoming in subjects_existing:
            continue
        list_existing.append(line_incoming)
        to_write = ["\t".join(row) + "\n" for row in list_existing]
        if not list_existing[0][0].startswith("participant_id"):
            to_write = ["participant_id\n"] + to_write
        with open(
            tsv_existing, "w", encoding="utf-8", newline=""
        ) as file_existing:
            file_existing.writelines(to_write)
