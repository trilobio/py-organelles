"""Unittests for logging decorators."""

import json
import logging
import time

from py_organelles.log_tools import log_enter_exit_factory, log_timer_factory

from .base import CleanUpLoggersHandlersTestCase

_logger_name = "unittest_logger"


class TestDecorators(CleanUpLoggersHandlersTestCase):
    """Test that decorators log appropriately."""

    def test_log_enter_exit_factory(self) -> None:
        """Test the log_enter_exit_factory decorator."""
        logger = logging.getLogger(_logger_name)

        @log_enter_exit_factory(logger)
        def add_two_ints(a: int, b: int) -> int:
            """Add two integers."""
            return a + b

        with self.assertLogs(_logger_name, level="DEBUG") as cm:
            add_two_ints(1, 2)

        self.assertIn("add_two_ints", cm.output[0])
        self.assertIn("a=1", cm.output[0])
        self.assertIn("b=2", cm.output[0])

        self.assertIn("return", cm.output[1])
        self.assertIn("3", cm.output[1])

        self.assertEqual(add_two_ints.__doc__, "Add two integers.")

    def test_log_timer_factory(self) -> None:
        """Test the log_timer_factory decorator."""
        logger = logging.getLogger(_logger_name)

        @log_timer_factory(logger)
        def sleep_func(dur: float) -> None:
            """Sleep for dur seconds."""
            time.sleep(dur)

        with self.assertLogs(_logger_name, level="DEBUG") as cm:
            sleep_func(0.0005)

        data = json.loads(cm.records[0].message)
        self.assertIn("sleep_func", data["log_duration_data"]["func_name"])
        self.assertTrue(data["log_duration_data"]["delta"] >= 0.0005)

        self.assertEqual(sleep_func.__doc__, "Sleep for dur seconds.")
