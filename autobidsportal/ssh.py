"""Handle interacting with a remote filesystem over ssh."""

from __future__ import annotations

import subprocess

from flask import current_app


def run_ssh_command(url: str, command: list[str]):
    """Run a command on the archive server using ssh."""
    subprocess.run(
        [
            "ssh",
            "-p",
            str(current_app.config["ARCHIVE_SSH_PORT"]),
            "-i",
            str(current_app.config["ARCHIVE_SSH_KEY"]),
            url,
        ]
        + command,
        check=True,
    )


def make_remote_dir(url: str, dir_path: str):
    """Make a directory on the archive filesystem."""
    run_ssh_command(url, ["mkdir", "-p", dir_path])


def remove_zip_files(url: str, remote_dir: str):
    """Remove all zip files in a directory on the archive filesystem."""
    run_ssh_command(url, ["rm", "-f", f"{remote_dir}/*.zip"])


def copy_file(url: str, local_path: str, remote_path: str):
    """Copy a file to the archive filesystem."""
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
