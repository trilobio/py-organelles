"""logging submodule with helpful user interface components."""
import logging
from typing import Union

import plac

def log_level_factory(log_level: Union[str, int]) -> int:
    """Given log level name or integer representation, returns int."""
    if isinstance(log_level, str):
        # Step 1. is it a str representation of an int?
        try:
            log_level = int(log_level)

        except ValueError:
            # Step 2: is it a log level name?
            try:
                log_level = getattr(logging, log_level.upper())

            except AttributeError:
                raise ValueError(
                    f"Invalid log level: {log_level}."
                    f"Valid levels are: {logging._nameToLevel.keys()}"
                )

    if isinstance(log_level, int):
        return log_level

    else:
        raise TypeError(
            f"Expected log level to be str or int, got {type(log_level)}")


log_level_annotation = plac.Annotation(
    help="console stream logging level (ex: info | DEBUG | 30)",
    kind="option",
    abbrev="ll",
    type=log_level_factory,
)
