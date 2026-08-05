"""Test the log_tools helper functions."""

import io
import logging
import pathlib
import tempfile
import threading
import time
import unittest.mock

from py_organelles.log_tools import setup_debug_loggers
from tests.base import CleanUpLoggersHandlersTestCase


class TestSetupDebugLoggers(CleanUpLoggersHandlersTestCase):
    """Tests for the non-blocking setup_debug_loggers helper."""

    def setUp(self) -> None:
        super().setUp()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.log_fp = pathlib.Path(self.tmp_dir.name) / "logs" / "test.log"

    def _make_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        return logger

    def test_records_reach_file_after_stop(self) -> None:
        """Records logged through the queue are flushed to the file by listener.stop()."""
        logger = self._make_logger("test_helper_functions.flush")
        # Pass a bare logger (not a list) to exercise LoggerList normalization.
        listener = setup_debug_loggers(logger, self.log_fp)

        logger.debug("a debug message")
        logger.info("an info message")
        listener.stop()

        contents = self.log_fp.read_text()
        self.assertIn("a debug message", contents)
        self.assertIn("an info message", contents)

    def test_stop_is_idempotent(self) -> None:
        """A second stop() (e.g. the atexit hook after an explicit stop) must not raise."""
        logger = self._make_logger("test_helper_functions.idempotent")
        listener = setup_debug_loggers([logger], self.log_fp)

        listener.stop()
        listener.stop()

    def test_stream_handler_respects_log_level(self) -> None:
        """The stream handler only emits records at or above log_level."""
        logger = self._make_logger("test_helper_functions.stream")
        listener = setup_debug_loggers([logger], self.log_fp, log_level=logging.INFO)

        # Redirect the listener's stream handler to a buffer we can inspect.
        stream_handler = next(
            handler for handler in listener.handlers if type(handler) is logging.StreamHandler
        )
        buffer = io.StringIO()
        stream_handler.setStream(buffer)

        logger.debug("debug-only message")
        logger.info("info-level message")
        listener.stop()

        streamed = buffer.getvalue()
        self.assertIn("info-level message", streamed)
        self.assertNotIn("debug-only message", streamed)

        # The file handler still receives DEBUG records.
        contents = self.log_fp.read_text()
        self.assertIn("debug-only message", contents)

    def test_full_queue_drops_without_blocking(self) -> None:
        """When the queue is full, logging does not block and drops are reported."""
        logger = self._make_logger("test_helper_functions.overflow")
        listener = setup_debug_loggers([logger], self.log_fp, queue_size=2)

        file_handler = next(
            handler for handler in listener.handlers if isinstance(handler, logging.FileHandler)
        )

        # Stall the listener thread inside the file handler to simulate a
        # slow-disk write spike, so the queue can fill up.
        handling_started = threading.Event()
        release_writes = threading.Event()
        queue_drained = threading.Event()
        original_emit = file_handler.emit

        def stalled_emit(record: logging.LogRecord) -> None:
            handling_started.set()
            release_writes.wait(timeout=10)
            original_emit(record)
            # "message 2" leaving the queue means both buffered slots are free.
            if record.getMessage() == "message 2":
                queue_drained.set()

        emit_patcher = unittest.mock.patch.object(file_handler, "emit", stalled_emit)
        emit_patcher.start()
        self.addCleanup(emit_patcher.stop)

        logger.info("message 0")
        self.assertTrue(handling_started.wait(timeout=10))

        # Listener is stalled on "message 0"; these two fill the queue.
        logger.info("message 1")
        logger.info("message 2")

        # The queue is now full: these must be dropped without blocking.
        t_start = time.monotonic()
        logger.info("message 3")
        logger.info("message 4")
        elapsed = time.monotonic() - t_start
        self.assertLess(elapsed, 1.0)

        release_writes.set()
        # Wait for the listener to drain the queue so the next record is
        # guaranteed to fit alongside the overflow warning.
        self.assertTrue(queue_drained.wait(timeout=10))
        logger.info("message 5")
        listener.stop()

        contents = self.log_fp.read_text()
        self.assertIn("message 0", contents)
        self.assertIn("message 1", contents)
        self.assertIn("message 2", contents)
        self.assertNotIn("message 3", contents)
        self.assertNotIn("message 4", contents)
        self.assertIn("message 5", contents)
        self.assertIn("Log queue overflowed: 2 log record(s) dropped", contents)
