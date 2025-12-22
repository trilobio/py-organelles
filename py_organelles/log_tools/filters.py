"""Custom python logging filters."""

import logging


class MaxLevelFilter(logging.Filter):
    """Logging filter to allow only log records with level less than max_level.

    :note: This filter is NOT inclusive. For example, if max_level is logging.WARNING,
        only log records with level less than WARNING (i.e., INFO, DEBUG) will pass
        through the filter.

    :param max_level: Maximum logging level (exclusive) for log records to pass the filter.
    """

    def __init__(self, max_level: int, name: str = "") -> None:
        super().__init__(name)
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < self.max_level
