"""Miscellaneous helpful logging tools."""

import functools
import inspect
import logging
import pathlib
import tempfile
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Callable, List, Optional, Union

from pythonjsonlogger import jsonlogger

from log_tools.formatters import ColorFormatter, DurationFormatter  # noqa: F401
from log_tools.ui import log_level_annotation  # noqa: F401
from log_tools.utilities import has_similar_handler


def log_timer_factory(logger: logging.Logger) -> Callable:
    def log_enter_exit(func: Callable) -> Callable:
        """Decorator to log start time, end time, and duration"""

        @functools.wraps(func)
        def dec(*args, **kwargs):
            start = datetime.now()
            retval = func(*args, **kwargs)
            end = datetime.now()
            delta = end - start
            logger.info(f"{func.__qualname__}")
            logger.info(f"Time taken: {delta}")
            logger.info(f"Time start: {start}")
            logger.info(f"Time end:   {end}")
            return retval

        return dec

    return log_enter_exit


def log_enter_exit_factory(logger: logging.Logger) -> Callable:
    """Creates a decorator that logs to a provided logger."""

    # Copied with modifications from aceta/can_bus/can_bus/client.py
    def log_enter_exit(func: Callable) -> Callable:
        """Decorator to log function arguments and return values for debugging purposes."""

        @functools.wraps(func)
        def dec(*args, **kwargs):
            func_args = inspect.signature(func).bind(*args, **kwargs).arguments
            # Unpack function arguments into DEBUG log message
            logger.debug(
                "%s(%s)",
                func.__qualname__,
                ", ".join(
                    map(
                        "{0[0]}={0[1]!r}".format,  # pylint: disable=consider-using-f-string
                        [(k, v) for k, v in func_args.items() if k != "self"],
                    )
                ),
            )

            try:
                retval = func(*args, **kwargs)
            except Exception as err:
                logger.error(err)
                logger.debug(err, exc_info=True)
                raise

            # log return values
            retval_tuple = (retval,) if not isinstance(retval, tuple) else retval
            logger.debug(
                "%s(...) returned %s",
                func.__qualname__,
                ", ".join(repr(value) for value in retval_tuple),
            )

            return retval

        return dec

    return log_enter_exit


@contextmanager
def modify_log_level(logger: Union[logging.Logger, List[logging.Logger]], level: int) -> None:
    """Temporarily modify the log level of one or more loggers.

    Args:
        logger (logging.Logger or List[logging.Logger]): logger(s) to modify
        level (int): new log level
    """
    if isinstance(logger, logging.Logger):
        loggers = [logger]
    else:
        loggers = logger

    original_values = [logger.level for logger in loggers]

    try:
        for logger in loggers:
            logger.setLevel(level)
        yield

    finally:
        for logger, original_value in zip(loggers, original_values):
            logger.setLevel(original_value)


def basic_logging_config(
    logger_names: List[str],
    stream_log_level: int = logging.INFO,
    log_filepath: Optional[pathlib.Path] = None,
    format_str: str = "%(name)s.%(levelname)s: %(message)s",
) -> None:
    """For each logger name, Attach INFO streamhandler, DEBUG filehandler.

    Note: If your handlers aren't showing up, check that the handlers aren't being
    removed by the has_similar_handler() function. The function compares the log level,
    name, and format_str of the desired handler to the handlers already attached to the logger
    and its parents. If the handler matches all of these criteria, it will not be attached.

    Args:
        logger_names (List[str): list of names of loggers to configure.
        stream_log_level (optional, int): logging level of StreamHandler.
            Defaults to INFO.
        log_filepath (optional, pathlib.Path): text log filepath.
            Defaults to a new file in /tmp.
        format_str (optional, str): format string passed to all formatters.
            Defaults to "%(name)s.%(levelname)s: %(message)s"
    """
    stream_formatter = ColorFormatter(format_str)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_log_level)
    stream_handler.setFormatter(stream_formatter)

    if log_filepath is None:
        folder = pathlib.Path("/tmp/logs")
        folder.mkdir(exist_ok=True)
        temp_file = tempfile.NamedTemporaryFile(suffix=".log", delete=False, dir=folder)
        log_filepath = temp_file.name

    file_formatter = logging.Formatter(format_str)
    file_handler = logging.FileHandler(log_filepath)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        if not has_similar_handler(logger, stream_handler):
            logger.addHandler(stream_handler)
        if not has_similar_handler(logger, file_handler):
            logger.addHandler(file_handler)
            logger.info("Diagnostic logs saved to %s", log_filepath)


def setup_structured_loggers(
    loggers: List[Union[str, logging.Logger]],
    filepath: pathlib.Path,
) -> None:
    """Set up provided loggers to save json-structured debug logs to a rotating file.

    Args:
        loggers (List[Union[str, logging.Logger]]): loggers to set up
            can be logger or name of logger
        filepath (pathlib.Path): file to save structured logs to
            parent dirs are created in the function if they don't exist
    """
    # Set up json formatting
    formatter = jsonlogger.JsonFormatter(
        "%(RPC)s %(start_time)s %(end_time)s",
    )

    # Set up rotating file handler
    # save up to 1 GB of logs that rotate every 200 MB
    filepath.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(filepath, maxBytes=200e6, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Attach handlers to loggers
    for logger in loggers:
        logger = logging.getLogger(logger) if isinstance(logger, str) else logger
        logger.addHandler(file_handler)


def setup_debug_loggers(
    loggers: List[Union[str, logging.Logger]],
    filepath: pathlib.Path,
    log_level: int = logging.INFO,
) -> None:
    """Set up provided loggers to save debug logs to a file and stream info logs.
    Attached to a rotating file handler.

    Args:
        loggers (List[Union[str, logging.Logger]]): list of loggers to set up
            can be logger or name of logger
        filepath (pathlib.Path): file to save structured logs to
            parent dirs are created in the function if they don't exist
        log_level (int): logging level for StreamHandler, defaults to logging.INFO
    """
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s - %(message)s")

    # Set up rotating file handler
    # save up to 1 GB of logs that rotate every 200 MB
    filepath.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(filepath, maxBytes=200e6, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Set up stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    # Attach handlers to loggers
    for logger in loggers:
        logger = logging.getLogger(logger) if isinstance(logger, str) else logger
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
