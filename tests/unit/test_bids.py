"""Unit tests of the BIDS functionality"""

import csv
from pathlib import Path

from autobidsportal.bids import (
    merge_participants_tsv,
    _check_existing,
    merge_datasets,
)


def test_merge_participants(tmp_path):
    """Test merge_participants where existing has a header."""
    tsv_incoming = "participant_id\n01\n02\n"
    tsv_existing = "participant_id\n02\n03\n"
    path_incoming = tmp_path / "incoming.tsv"
    path_existing = tmp_path / "existing.tsv"
    with open(
        path_incoming, "w", encoding="utf-8", newline=""
    ) as file_incoming:
        file_incoming.write(tsv_incoming)
    with open(
        path_existing, "w", encoding="utf-8", newline=""
    ) as file_existing:
        file_existing.write(tsv_existing)
    merge_participants_tsv(path_incoming, path_existing)
    with open(
        path_existing, "r", encoding="utf-8", newline=""
    ) as file_existing:
        reader_existing = csv.reader(file_existing, delimiter="\t")
        assert list(reader_existing) == [
            ["participant_id"],
            ["02"],
            ["03"],
            ["01"],
        ]


def test_merge_participants_no_header(tmp_path):
    """Test merge_participants where existing has no header."""
    tsv_incoming = "participant_id\n01\n02\n"
    tsv_existing = "02\n03\n"
    path_incoming = tmp_path / "incoming.tsv"
    path_existing = tmp_path / "existing.tsv"
    with open(
        path_incoming, "w", encoding="utf-8", newline=""
    ) as file_incoming:
        file_incoming.write(tsv_incoming)
    with open(
        path_existing, "w", encoding="utf-8", newline=""
    ) as file_existing:
        file_existing.write(tsv_existing)
    merge_participants_tsv(path_incoming, path_existing)
    with open(
        path_existing, "r", encoding="utf-8", newline=""
    ) as file_existing:
        reader_existing = csv.reader(file_existing, delimiter="\t")
        assert list(reader_existing) == [
            ["participant_id"],
            ["02"],
            ["03"],
            ["01"],
        ]


def test_check_existing(tmp_path):
    """Test that the existence checking function works."""
    path_incoming = tmp_path / "incoming"
    path_existing = tmp_path / "existing"

    dir_incoming = path_incoming / "test-dir"
    dir_incoming.mkdir(parents=True)
    dir_existing = path_existing / "test-dir"
    dir_existing.mkdir(parents=True)

    for filename in ["1", "2", "3"]:
        (dir_incoming / filename).touch()

    for filename in ["1", "2"]:
        (dir_existing / filename).touch()

    assert _check_existing(
        path_incoming, path_existing, dir_incoming, ["1", "2", "3"]
    ) == ["1", "2"]


def test_merge_datasets(tmp_path):
    """Test that merging a whole dataset works."""
    path_existing = tmp_path / "existing"
    path_incoming = tmp_path / "incoming"

    path_sub_1 = Path("sub-1") / "anat"
    path_sub_2 = Path("sub-2") / "anat"
    path_sub_3 = Path("sub-3") / "anat"

    (path_existing / path_sub_1).mkdir(parents=True)
    (path_existing / path_sub_2).mkdir(parents=True)
    sub_1_existing = path_existing / path_sub_1 / "sub-1_t1w.nii.gz"
    with open(sub_1_existing, "w", encoding="utf-8") as file_sub_1_existing:
        file_sub_1_existing.write("existing")
    (path_existing / path_sub_2 / "sub-2_t1w.nii.gz").touch()
    participants_existing = path_existing / "participants.tsv"
    with open(
        participants_existing, "w", encoding="utf-8"
    ) as file_participants_existing:
        file_participants_existing.write("participant_id\nsub-1\nsub-2\n")

    (path_incoming / path_sub_1).mkdir(parents=True)
    (path_incoming / path_sub_3).mkdir(parents=True)
    sub_1_incoming = path_incoming / path_sub_1 / "sub-1_t1w.nii.gz"
    with open(sub_1_incoming, "w", encoding="utf-8") as file_sub_1_incoming:
        file_sub_1_incoming.write("incoming")
    (path_incoming / path_sub_3 / "sub-3_t1w.nii.gz").touch()
    participants_incoming = path_incoming / "participants.tsv"
    with open(
        participants_incoming, "w", encoding="utf-8"
    ) as file_participants_incoming:
        file_participants_incoming.write("participant_id\nsub-1\nsub-3\n")

    merge_datasets(path_incoming, path_existing)
    assert (path_existing / path_sub_3 / "sub-3_t1w.nii.gz").exists()
    with open(sub_1_existing, "r", encoding="utf-8") as file_sub_1_existing:
        assert file_sub_1_existing.read() == "existing"
    with open(
        participants_existing, "r", encoding="utf-8"
    ) as file_participants_existing:
        assert (
            file_participants_existing.read()
            == "participant_id\nsub-1\nsub-2\nsub-3\n"
        )
