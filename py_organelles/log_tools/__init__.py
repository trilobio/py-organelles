"""Miscellaneous helpful logging tools."""

import logging
import pathlib
import tempfile
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from typing import Iterator

from log_tools.decorators import log_enter_exit_factory, log_timer_factory  # noqa: F401
from log_tools.formatters import ColorFormatter, DurationFormatter  # noqa: F401
from log_tools.ui import log_level_annotation  # noqa: F401
from log_tools.utilities import has_similar_handler
from pythonjsonlogger import jsonlogger


@contextmanager
def modify_log_level(logger: logging.Logger | list[logging.Logger], level: int) -> Iterator[None]:
    """Temporarily modify the log level of one or more loggers.

    :param logger: logger(s) to modify
    :type logger: logging.Logger | list[logging.Logger]
    :param level: new log level
    :type level: int
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
    logger_names: list[str],
    stream_log_level: int = logging.INFO,
    log_filepath: pathlib.Path | None = None,
    format_str: str = "%(name)s.%(levelname)s: %(message)s",
) -> None:
    """Attach stream_log_level streamhandler and DEBUG filehandler to each named logger.

    Note: If your handlers aren't showing up, check that the handlers aren't being
    removed by the has_similar_handler() function. The function compares the log level,
    name, and format_str of the desired handler to the handlers already attached to the logger
    and its parents. If the handler matches all of these criteria, it will not be attached.

    :param logger_names: names of loggers to set up
    :type loggers: list[str]
    :param stream_log_level: logging level for StreamHandler, defaults to logging.INFO
    :type stream_log_level: int
    :param log_filepath: Passed to logging.FileHandler, defaults to NamedTemporaryFile created in /tmp/logs
    :type log_filepath: pathlib.Path | None
    :param format_str: format string passed to all formatters, defaults to "%(name)s.%(levelname)s: %(message)s"
    :type format_str: str
    """
    stream_formatter = ColorFormatter(format_str)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_log_level)
    stream_handler.setFormatter(stream_formatter)

    if log_filepath is None:
        folder = pathlib.Path("/tmp/logs")
        folder.mkdir(exist_ok=True)
        temp_file = tempfile.NamedTemporaryFile(suffix=".log", delete=False, dir=folder)
        log_filepath = pathlib.Path(temp_file.name)

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
    loggers: list[str | logging.Logger],
    filepath: pathlib.Path,
    max_bytes: int = int(200e6),
    backup_count: int = 5,
) -> None:
    """Set up provided loggers to save json-structured debug logs to a rotating file.

    :param loggers: loggers to set up, as Logger object or name of logger
    :type loggers: list[str | logging.Logger]
    :param filepath: Passed to logging.RotatingFileHandler. Parent dirs are created if
        they don't exist
    :type filepath: pathlib.Path
    :param log_level: logging level for StreamHandler, defaults to logging.INFO
    :type log_level: int
    :param max_bytes: Passed to logging.RotatingFileHandler, default is 200 MB
    :type max_bytes: int
    :param backup_count: Passed to logging.RotatingFileHandler, default is 5
    :type backup_count: int
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
    file_handler = RotatingFileHandler(filepath, maxBytes=max_bytes, backupCount=backup_count)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Attach handlers to loggers
    for logger in loggers:
        logger = logging.getLogger(logger) if isinstance(logger, str) else logger
        logger.addHandler(file_handler)


def setup_debug_loggers(
    loggers: list[str | logging.Logger],
    filepath: pathlib.Path,
    log_level: int = logging.INFO,
    max_bytes: int = int(200e6),
    backup_count: int = 5,
) -> None:
    """Set up provided loggers to save debug logs to a file and stream info logs.
    Attached to a rotating file handler.

    :param loggers: loggers to set up, as Logger object or name of logger
    :type loggers: list[str | logging.Logger]
    :param filepath: Passed to logging.RotatingFileHandler. Parent dirs are created if
        they don't exist
    :type filepath: pathlib.Path
    :param log_level: logging level for StreamHandler, defaults to logging.INFO
    :type log_level: int
    :param max_bytes: Passed to logging.RotatingFileHandler, default is 200 MB
    :type max_bytes: int
    :param backup_count: Passed to logging.RotatingFileHandler, default is 5
    :type backup_count: int
    """
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s - %(message)s")

    # Set up rotating file handler
    # save up to 1 GB of logs that rotate every 200 MB
    filepath.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(filepath, maxBytes=max_bytes, backupCount=backup_count)
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
