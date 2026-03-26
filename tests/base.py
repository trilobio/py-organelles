"""Unit test base class to ensure loggers and handlers are cleaned up between tests."""

import logging
import unittest

_EXPECTED_LOGGERS: tuple[str, ...] = (
    "py_organelles",
    "py_organelles.core",
    "py_organelles.core.factory",
    "py_organelles.core.wrapping",
)


class CleanUpLoggersHandlersTestCase(unittest.TestCase):
    """TestCase class that cleans up loggers & handlers between tests."""

    def setUp(self) -> None:
        """Ensure logging state is fully reset from last test."""

        leftover_loggers: list[str] = []
        if len(logging.root.manager.loggerDict) > 0:
            for logger_name in logging.root.manager.loggerDict:
                if logger_name not in _EXPECTED_LOGGERS:
                    leftover_loggers.append(logger_name)

        assert (
            len(leftover_loggers) == 0
        ), f"loggers left over from last test: {[(k, v) for k, v in logging.root.manager.loggerDict.items() if k in leftover_loggers]}"

        assert (
            len(logging.root.handlers) == 0
        ), "Root logger has handlers not cleaned up from last test"

    def tearDown(self) -> None:
        """Clean up any loggers created during test."""
        names = list(logging.root.manager.loggerDict.keys())
        for n in names:
            del logging.root.manager.loggerDict[n]

        logging.root.handlers.clear()
