"""Unit test base class that snapshots and restores logging state around each test."""

import logging
import logging.handlers
import unittest
from dataclasses import dataclass


@dataclass
class _LoggerSnapshot:
    level: int
    handlers: list[logging.Handler]
    disabled: bool
    propagate: bool


class CleanUpLoggersHandlersTestCase(unittest.TestCase):
    """TestCase base class that fully restores the logging subsystem after each test.

    ``setUp`` captures a snapshot of the current logging state (root logger and all
    named loggers).  ``tearDown`` restores that snapshot exactly: loggers added during
    the test are removed, loggers that existed before are restored to their original
    level/handlers/disabled/propagate values, and the root logger is restored in full.
    """

    _logging_snapshot: dict[str, _LoggerSnapshot]
    _root_snapshot: _LoggerSnapshot

    def setUp(self) -> None:
        """Snapshot the current logging state before the test runs."""
        self._root_snapshot = _LoggerSnapshot(
            level=logging.root.level,
            handlers=list(logging.root.handlers),
            disabled=logging.root.disabled,
            propagate=logging.root.propagate,
        )
        self._logging_snapshot = {}
        for name, obj in logging.root.manager.loggerDict.items():
            if isinstance(obj, logging.Logger):
                self._logging_snapshot[name] = _LoggerSnapshot(
                    level=obj.level,
                    handlers=list(obj.handlers),
                    disabled=obj.disabled,
                    propagate=obj.propagate,
                )
            else:
                # PlaceHolder — record presence so we can restore it if needed
                self._logging_snapshot[name] = _LoggerSnapshot(
                    level=logging.NOTSET,
                    handlers=[],
                    disabled=False,
                    propagate=True,
                )

    def tearDown(self) -> None:
        """Restore the logging state to exactly what it was before the test."""
        # Remove loggers that were added during the test.
        for name in list(logging.root.manager.loggerDict.keys()):
            if name not in self._logging_snapshot:
                del logging.root.manager.loggerDict[name]

        # Restore loggers that existed before the test.
        for name, snap in self._logging_snapshot.items():
            obj = logging.root.manager.loggerDict.get(name)
            if isinstance(obj, logging.Logger):
                obj.level = snap.level
                obj.handlers = list(snap.handlers)
                obj.disabled = snap.disabled
                obj.propagate = snap.propagate

        # Restore root logger.
        logging.root.level = self._root_snapshot.level
        logging.root.handlers = list(self._root_snapshot.handlers)
        logging.root.disabled = self._root_snapshot.disabled
        logging.root.propagate = self._root_snapshot.propagate
