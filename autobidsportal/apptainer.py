"""Manage apptainer invocations of other tools."""

from dataclasses import dataclass
from itertools import chain
from pathlib import Path
import subprocess
from typing import Union, Sequence


def apptainer_exec(cmd_list, container_path, binds, **kwargs):
    """Assemble a singularity subprocess with given args.

    Parameters
    ----------
    cmd_list : list of string
        Equivalent to "args" in subprocess.run. Passed to the singularity
        container.
    container_path : Path or str
        Path to the singularity container to be executed.
    binds : list of str
        List of bind strings of the form src[:dest[:opts]]
    kwargs
        keyword arguments to be passed to subprocess.run. "shell" will be
        overwritten to False and "check" will be overwritten to True, if
        present.
    """
    bind_list = list(chain(*[["-B", bind] for bind in binds]))
    kwargs["shell"] = False
    if "check" in kwargs:
        del kwargs["check"]
    return subprocess.run(
        [
            "apptainer",
            "exec",
        ]
        + bind_list
        + [str(container_path)]
        + cmd_list,
        check=True,
        **kwargs
    )


@dataclass
class ImageSpec:
    """A related image location and sequence of binds.

    Attributes
    ----------
    image_path : str or Path
        Path to the singularity container to be executed.
    binds : list of str
        List of bind strings of the form src[:dest[:opts]]
    """

    image_path: Union[str, Path]
    binds: Sequence[str]
