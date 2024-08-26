"""Miscellaneous utility functions used across the Trilobio codebase."""

import os
import pathlib
from difflib import get_close_matches


def get_aceta_root() -> pathlib.Path:
    """Check for $ACETA_ROOT environment variable, return as Path if exists."""
    ACETA_ROOT = "ACETA_ROOT"
    if ACETA_ROOT not in os.environ:
        raise EnvironmentError(
            f'Could not find environment variable "{ACETA_ROOT}".'
            f'Add the path to the aceta repository as an environment variable called "{ACETA_ROOT}"'
        )
    return pathlib.Path(os.environ[ACETA_ROOT])


def check_for_file(file_path: pathlib.Path) -> None:
    """Raises better FileNotFoundError if file_path does not exist.

    Args:
        file_path (Path): path to file to check for existence

    Raises:
        FileNotFoundError: if file_path does not exist
    """
    file_path = file_path.resolve()
    if not file_path.is_file():
        matches = get_close_matches(file_path.name, [f.name for f in file_path.parent.iterdir()])
        closest_file = None if len(matches) == 0 else file_path.parent / matches[0]
        raise FileNotFoundError({"missing_file": file_path, "closest_file_name": closest_file})
