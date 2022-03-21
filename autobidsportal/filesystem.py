"""Utilities for processing the filesystem."""

import os


def gen_dir_dict(path):
    """Generate a dictionary representing a file tree.

    Parameters
    ----------
    path : str
        The root path of the file tree to convert to dict.

    Returns
    -------
    dict
        A dict with one key (the root directory name), where the value is a
        recursive series of dicts with keys "files" and "dirs", where "files"
        has a list of file names in the dict, and "dirs" has the directory
        names as keys and contents the same as the root dict.

        Example:
        {
            "root_dir": {
                "files": ["file1.txt", "file2.txt"],
                "dirs": {
                    "child_dir": {
                        "files": ["file3.txt"],
                        "dirs": {},
                    },
                },
            },
        }
    """

    return {
        "files": [entry.name for entry in os.scandir(path) if entry.is_file()],
        "dirs": {
            entry.name: gen_dir_dict(entry.path)
            for entry in os.scandir(path)
            if entry.is_dir()
        },
    }
