"""Utilities for processing the filesystem."""

import os
import pathlib


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

    child_dirs = {}
    for root, dirs, files in os.walk(pathlib.Path(path), topdown=False):
        dir_dict = {"files": files, "dirs": {}}
        path_root = pathlib.Path(root)
        for dir_child in dirs:
            dir_path = str(path_root / dir_child)
            if dir_path in child_dirs:
                dir_dict["dirs"][dir_path] = child_dirs[dir_path]
                del child_dirs[dir_path]
        child_dirs[str(path_root)] = dir_dict
    return child_dirs
