"""Unittests for log_tools.ui submodule"""

import logging
import unittest

from log_tools.ui import log_level_factory


class TestGetLogLevel(unittest.TestCase):
    def test_get_log_level(self) -> None:
        self.assertEqual(log_level_factory("CRITICAL"), logging.CRITICAL)
        self.assertEqual(log_level_factory("debug"), logging.DEBUG)
        self.assertEqual(log_level_factory(26), 26)
        self.assertEqual(log_level_factory("006"), 6)

        with self.assertRaises(TypeError):
            log_level_factory(10.1)  # type: ignore [arg-type]

        with self.assertRaises(ValueError):
            log_level_factory("not a log level")


if __name__ == "__main__":
    unittest.main()
