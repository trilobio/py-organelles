"""Logging-specific context managers."""

import logging
from contextlib import contextmanager
from typing import Iterator

from py_organelles.log_tools.formatters import ColorFormatter
from py_organelles.log_tools.utilities import LoggerList, normalize_logger_list


@contextmanager
def modify_log_level(logger_list: LoggerList, level: int) -> Iterator[None]:
    """Temporarily modify the log level of one or more loggers.

    :param logger: logger(s) to modify
    :param level: new log level
    """
    loggers = normalize_logger_list(logger_list)
    original_levels = [logger.level for logger in loggers]

    try:
        for logger in loggers:
            logger.setLevel(level)
        yield

    finally:
        for logger, original_level in zip(loggers, original_levels):
            logger.setLevel(original_level)


@contextmanager
def stream_logs(
    logger_list: LoggerList,
    level: int = logging.INFO,
    format_str="%(name)s.%(levelname)s: %(message)s",
) -> Iterator[None]:
    """Temporarily attach StreamHandlers with given log level to one or more loggers.

    :param logger: logger(s) to stream to console
    :param level: new log level, defaults to logging.INFO
    :param format_str: format string for the log messages, defaults to "%(name)s.%(levelname)s: %(message)s"
    """
    loggers = normalize_logger_list(logger_list)
    original_levels = [logger.level for logger in loggers]

    try:
        formatter = ColorFormatter(format_str)
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(formatter)
        for logger in loggers:
            logger.addHandler(handler)
            if logger.level > level or logger.level == logging.NOTSET:
                logger.setLevel(level)
        yield

    finally:
        for logger, original_level in zip(loggers, original_levels):
            logger.removeHandler(handler)
            logger.setLevel(original_level)
