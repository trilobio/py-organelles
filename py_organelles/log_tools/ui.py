"""logging submodule with helpful user interface components."""

import logging
import pathlib

import plac  # type: ignore[import-untyped]


def log_level_factory(log_level: str | int) -> int:
    """Given log level name or integer representation, returns int."""
    if isinstance(log_level, str):
        # Step 1. is it a str representation of an int?
        try:
            return int(log_level)

        except ValueError:
            # Step 2: is it a log level name?
            try:
                return getattr(logging, log_level.upper())

            except AttributeError:
                raise ValueError(
                    f"Invalid log level: {log_level}."
                    f"Valid levels are: {logging._nameToLevel.keys()}"
                )

    if isinstance(log_level, int):
        return log_level

    else:
        raise TypeError(f"Expected log level to be str or int, got {type(log_level)}")


log_level_annotation = plac.Annotation(
    help="console stream logging level (ex: info | DEBUG | 30)",
    kind="option",
    abbrev="ll",
    type=log_level_factory,
)
overwrite_annotation = plac.Annotation(
    help="Overwrite existing file(s)",
    kind="flag",
)
append_annotation = plac.Annotation(
    help="Append to existing file(s)",
    kind="flag",
)
output_dir_annotation = plac.Annotation(
    help="Directory in which to save file(s)",
    kind="option",
    abbrev="od",
    type=pathlib.Path,
)
