"""Unit test base class to ensure loggers and handlers are cleaned up between tests."""

import dataclasses
import logging
import unittest
from typing import TypeAlias

LogLevel: TypeAlias = int
LoggerName: TypeAlias = str


@dataclasses.dataclass
class LoggerState:
    level: LogLevel
    propagate: bool
    disabled: bool
    handlers: list[tuple[logging.Handler, LogLevel]]


class LoggingIsolatedTestCase(unittest.TestCase):
    """Test case that snapshots and restores the complete logging state around each test,
    so logger/handler mutations never leak between tests.

    :warning: Claude generated this
    """

    def setUp(self) -> None:
        self._logging_snapshot = self._capture_logging_state()

    def tearDown(self) -> None:
        self._restore_logging_state(self._logging_snapshot)

    def _capture_logging_state(self) -> dict[LoggerName, LoggerState]:
        """
        Walk every logger currently known to the logging manager and record
        its level, propagate flag, disabled flag, and the identity + level of
        every attached handler.  The root logger is included under the empty
        string key "".
        """
        snapshot = {}

        # Root logger
        root = logging.root
        snapshot[""] = self._capture_single_logger(root)

        # All named loggers that have been instantiated so far
        manager = logging.Logger.manager
        for name, logger_or_placeholder in manager.loggerDict.items():
            if isinstance(logger_or_placeholder, logging.Logger):
                snapshot[name] = self._capture_single_logger(logger_or_placeholder)

        return snapshot

    def _capture_single_logger(self, logger: logging.Logger) -> LoggerState:
        return LoggerState(
            level=logger.level,
            propagate=logger.propagate,
            disabled=logger.disabled,
            # Store handler objects paired with their level at snapshot time.
            # We restore the handler list and each handler's level, but we do
            # NOT deep-copy handlers — the same handler objects are reattached,
            # which is the right behaviour for things like StreamHandlers that
            # wrap live file descriptors.
            handlers=[(h, h.level) for h in logger.handlers],
        )

    def _restore_logging_state(self, snapshot: dict[LoggerName, LoggerState]) -> None:
        """
        1. Remove every logger that did not exist before the test.
        2. Restore the attributes of every logger that did exist.
        3. Leave the logging.Manager itself intact so the framework stays usable.
        """
        manager = logging.Logger.manager

        # --- Remove loggers created during the test ---
        extra_names = set(
            name
            for name, obj in manager.loggerDict.items()
            if isinstance(obj, logging.Logger) and name not in snapshot
        )
        for name in extra_names:
            del manager.loggerDict[name]

        # --- Restore pre-existing loggers ---
        for name, state in snapshot.items():
            if name == "":
                logger: logging.Logger = logging.root
            else:
                # Use getLogger so placeholders are promoted if needed, but
                # at this point the logger should already exist in the dict.
                logger = logging.getLogger(name)

            self._restore_single_logger(logger, state)

    def _restore_single_logger(self, logger: logging.Logger, state: LoggerState) -> None:
        logger.setLevel(state.level)
        logger.propagate = state.propagate
        logger.disabled = state.disabled

        # Detach all current handlers without closing them — the test owns
        # any handlers it created; we just want them off this logger.
        logger.handlers.clear()

        # Re-attach the original handlers and restore their levels.
        for handler, level in state.handlers:
            handler.setLevel(level)
            logger.addHandler(handler)
