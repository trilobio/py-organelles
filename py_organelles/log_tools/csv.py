"""Utility functions for working with .csv data files."""
import csv
import pathlib
from typing import Any, List, Union

import numpy as np


def csv_append_row(
    file_path: pathlib.Path,
    row: Union[np.ndarray, List[Any], List[List[Any]]],
) -> None:
    """Append row to given csv."""
    if isinstance(row, list):
        if isinstance(row[0], list):
            rows = row
        else:
            rows = [row]

    elif isinstance(row, np.ndarray):
        if len(row.shape) == 1:
            rows = [row.tolist()]
        else:
            rows = [row[i].tolist() for i in range(row.shape[0])]

    else:
        raise TypeError(f"Expected row to be a list or np.ndarray, got {type(row)}")

    with file_path.open("a") as io_obj:
        writer = csv.writer(io_obj)
        for r in rows:
            writer.writerow(r)


def set_up_csv(
    file_path: pathlib.Path,
    header: List[str],
    overwrite: bool = False,
    append: bool = False,
) -> None:
    """Create or clean data file, dependent on flags."""
    if overwrite and append:
        raise ValueError("Cannot provide both overwrite and append")

    if file_path.is_file():
        if not overwrite and not append:
            raise FileExistsError(
                f"{file_path.resolve()} already exists, but {overwrite=} and {append=}"
            )

        elif overwrite:
            file_path.unlink()

    if not file_path.is_file():
        file_path.touch()
        csv_append_row(file_path, header)
