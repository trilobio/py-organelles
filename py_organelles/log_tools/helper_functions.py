"""Functions to assist in configuring multiple loggers."""

import logging
import pathlib
import sys
import tempfile

from pythonjsonlogger import jsonlogger

from .constants import DEFAULT_FORMAT_STR
from .filters import MaxLevelFilter
from .formatters import ColorFormatter
from .utilities import (
    LoggerList,
    has_similar_handler,
    normalize_logger_list,
)


def basic_logging_config(
    logger_list: LoggerList,
    stream_log_level: int = logging.INFO,
    log_filepath: pathlib.Path | None = None,
    format_str: str = DEFAULT_FORMAT_STR,
) -> None:
    """Attach stream_log_level streamhandler and DEBUG filehandler to each named logger.

    Note: If your handlers aren't showing up, check that the handlers aren't being
    removed by the has_similar_handler() function. The function compares the log level,
    name, and format_str of the desired handler to the handlers already attached to the logger
    and its parents. If the handler matches all of these criteria, it will not be attached.

    :param logger_list: logger(s) or name(s) of loggers to configure
    :param stream_log_level: logging level for StreamHandler, defaults to logging.INFO
    :param log_filepath: Passed to logging.FileHandler, defaults to NamedTemporaryFile created in /tmp/logs
    :param format_str: format string passed to all formatters, defaults to "%(name)s.%(levelname)s: %(message)s"
    """
    loggers = normalize_logger_list(logger_list)
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

    for logger in loggers:
        logger.setLevel(logging.DEBUG)
        if not has_similar_handler(logger, stream_handler):
            logger.addHandler(stream_handler)
        if not has_similar_handler(logger, file_handler):
            logger.addHandler(file_handler)
            logger.info("Diagnostic logs saved to %s", log_filepath)


def setup_structured_loggers(
    loggers: list[str | logging.Logger],
) -> None:
    """Convenience wrapper for setup_journald_loggers tuned for logging structured json data.

    :param loggers: loggers to set up, as Logger object or name of logger
    """
    setup_journald_loggers(
        loggers=loggers,
        formatter_type=jsonlogger.JsonFormatter,
        fmt="%(RPC)s %(start_time)s %(end_time)s",
    )


def setup_debug_loggers(
    loggers: LoggerList,
    log_level: int = 0,
) -> None:
    """Convenience wrapper for setup_journald_loggers tuned for logging unstructured
        diagnostic logs.

    :param loggers: loggers to set up, as Logger object or name of logger
    :param log_level: level above which logs are handled. Defaults to logging everything above 0.
        Prevents un-handled logs from being stored, and as such not recommended unless you are
        diagnosing performance issues.
    """
    setup_journald_loggers(
        loggers=loggers,
        formatter_type=ColorFormatter,
        fmt="%(asctime)s %(levelname)-7s - %(message)s",
        log_level=log_level,
    )


def setup_journald_loggers(
    loggers: LoggerList | None = None,
    # Default value relies on journald to manage timestamp and severity
    formatter_type: type[logging.Formatter] = logging.Formatter,
    fmt: str = "%(name)s: %(message)s",
    log_level: int = 0,
) -> None:
    """Set up provided loggers to log to systemd's journald in a standardized manner.

    Does the following:
    - Adds StreamHandler logging <WARNING to stdout
    - Adds StreamHandler logging >=WARNING to stderr

    :param loggers: loggers to set up, as Logger object or name of logger. If None given,
        sets up the root logger only.
    :param formatter_type: formatter class used for stdout & stderr handlers. If not provided,
        uses the standard logging.Formatter.
    :param fmt: format string used for stdout & stderr handlers. If not provided,
        uses a default string that mostly relies on journald to log metadata.
    :param log_level: level above which logs are handled. Defaults to logging everything above 0.
        Prevents un-handled logs from being stored, and as such not recommended unless you are
        diagnosing performance issues.
    """
    loggers = loggers or [logging.getLogger()]
    loggers = normalize_logger_list(loggers)

    formatter = formatter_type(fmt)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(max(log_level, 0))
    stdout_handler.addFilter(MaxLevelFilter(logging.WARNING))
    stdout_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(max(log_level, logging.WARNING))
    stderr_handler.setFormatter(formatter)

    for logger in loggers:
        logger.setLevel(logging.DEBUG)
        if not has_similar_handler(logger, stdout_handler):
            logger.addHandler(stdout_handler)
        if not has_similar_handler(logger, stderr_handler):
            logger.addHandler(stderr_handler)
