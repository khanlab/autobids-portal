"""Utilities for processing the filesystem."""

import os

SPACE = "    "
BRANCH = "│   "
TEE = "├── "
LAST = "└── "


def gen_dir_dict(path, ignore=frozenset()):
    """Generate a dictionary representing a file tree.

    Parameters
    ----------
    path : str
        The root path of the file tree to convert to dict.
    ignore : Collection
        File/directory names to ignore.

    Returns
    -------
    dict
        A dict with two keys: "files" and "dirs". The value of "files" is a
        list of file names in "path", and the value of "dirs" is a directory
        where every key is the name of a directory in "path", and the
        corresponding value has the same structure as the overall returned
        dict.

        Example:
        {
            "files": ["file1.txt", "file2.txt"],
            "dirs": {
                "child_dir": {
                    "files": ["file3.txt"],
                    "dirs": {},
                },
            },
        }
    """
    return {
        "files": [
            entry.name
            for entry in os.scandir(path)
            if (entry.is_file() or entry.is_symlink())
            and entry.name not in ignore
        ],
        "dirs": {
            entry.name: gen_dir_dict(entry.path, ignore)
            for entry in os.scandir(path)
            if entry.is_dir() and entry.name not in ignore
        },
    }


def render_dir_dict(dir_dict, prefix=""):
    """Render a dir_dict in the style of UNIX tree.

    Returns
    -------
    list of str:
        Strings that when joined by newlines will render the dir_dict.
    """
    all_contents = dir_dict["files"] + list(dir_dict["dirs"].keys())
    pointers = [TEE for _ in range(len(all_contents) - 1)] + [LAST]
    lines = []
    for pointer, file_ in zip(
        pointers[: len(dir_dict["files"])],
        dir_dict["files"],
    ):
        lines.append(f"{prefix}{pointer}{file_}")
    for pointer, (key, val) in zip(
        pointers[len(dir_dict["files"]) :],
        dir_dict["dirs"].items(),
    ):
        lines.append(f"{prefix}{pointer}{key}")
        extension = BRANCH if pointer == TEE else SPACE
        lines.extend(render_dir_dict(val, prefix=f"{prefix}{extension}"))
    return lines
