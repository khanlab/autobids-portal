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
        "files": [entry.name for entry in os.scandir(path) if entry.is_file()],
        "dirs": {
            entry.name: gen_dir_dict(entry.path)
            for entry in os.scandir(path)
            if entry.is_dir()
        },
    }
