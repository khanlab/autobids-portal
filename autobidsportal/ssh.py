"""Handle interacting with a remote filesystem over ssh."""

from __future__ import annotations

import subprocess

from flask import current_app


def run_ssh_command(url: str, command: list[str]):
    """Run a command on the archive server using ssh.

    Parameters
    ----------
    url
        Address of archive server

    command
        List of commands to perform (following ssh connection)
    """
    subprocess.run(
        [
            "ssh",
            "-p",
            str(current_app.config["ARCHIVE_SSH_PORT"]),
            "-i",
            str(current_app.config["ARCHIVE_SSH_KEY"]),
            url,
            *command,
        ],
        check=True,
    )


def make_remote_dir(url: str, dir_path: str):
    """Make a directory on the archive filesystem.

    Parameters
    ----------
    url
        Address of archive server

    dir_path
        Directory to create on archive server
    """
    run_ssh_command(url, ["mkdir", "-p", dir_path])


def remove_zip_files(url: str, remote_dir: str):
    """Remove all zip files in a directory on the archive filesystem.

    Parameters
    ----------
    url
        Address of archive server

    remote_dir
        Directory on archive server to remove zip files from

    """
    run_ssh_command(url, ["rm", "-f", f"{remote_dir}/*.zip"])


def copy_file(url: str, local_path: str, remote_path: str):
    """Copy a file to the archive filesystem.

    Parameters
    ----------
    url
        Address of archive server

    local_path
        Local directory to copy files to

    remote_path
        Directory on archive server to copy files from
    """
    subprocess.run(
        [
            "scp",
            "-P",
            str(current_app.config["ARCHIVE_SSH_PORT"]),
            "-i",
            str(current_app.config["ARCHIVE_SSH_KEY"]),
            local_path,
            url + remote_path,
        ],
        check=True,
    )
