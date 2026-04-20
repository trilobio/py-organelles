"""Unit tests for log_tools.utilities submodule."""

import logging
import unittest

from py_organelles.log_tools import (
    LoggerList,
    get_handlers,
    has_similar_handler,
    normalize_logger_list,
)
from py_organelles.log_tools.utilities import _get_handler_formatter_str
from tests.base import CleanUpLoggersHandlersTestCase


class TestGetHandlers(CleanUpLoggersHandlersTestCase):
    """Unittests for get_handlers() function."""

    def test_no_handler(self) -> None:
        name = "test_no_handler"
        logger = logging.getLogger(name)
        self.assertTrue(len(get_handlers(logger)) == 0)

    def test_no_handler_parent(self) -> None:
        name = "test_no_handler_parent"
        logger = logging.getLogger(f"{name}.child")
        self.assertTrue(len(get_handlers(logger)) == 0)

    def test_has_handler(self) -> None:
        name = "test_has_handler"
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        self.assertTrue(len(get_handlers(logger)) == 1)

    def test_parent_has_handler(self) -> None:
        name = "test_parent_has_handler"
        l_parent = logging.getLogger(name)
        handler = logging.StreamHandler()
        l_parent.addHandler(handler)

        logger = logging.getLogger(f"{name}.child")
        self.assertTrue(len(get_handlers(logger)) == 1)

    def test_root_has_handler(self) -> None:
        name = "test_root_has_handler"
        handler = logging.StreamHandler()
        logging.root.addHandler(handler)

        logger = logging.getLogger(name)
        self.assertTrue(len(get_handlers(logger)) == 1)

    def test_no_duplicate_handlers(self) -> None:
        name = "test_no_duplicate_handlers"
        l_parent = logging.getLogger(name)
        handler = logging.StreamHandler()
        l_parent.addHandler(handler)

        logger = logging.getLogger(f"{name}.child")
        logger.addHandler(handler)  # Duplicate handler is added
        self.assertTrue(
            len(get_handlers(logger)) == 1,
            f"found {len(get_handlers(logger))} handlers, not 1",
        )

    def test_nonduplicate_handlers(self) -> None:
        name = "test_nonduplicate_handlers"
        l_parent = logging.getLogger(name)
        h_parent = logging.StreamHandler()
        l_parent.addHandler(h_parent)

        logger = logging.getLogger(f"{name}.child")
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        self.assertTrue(len(get_handlers(logger)) == 2)


class TestHasSimilarHandler(CleanUpLoggersHandlersTestCase):
    """Unittests for has_similar_handler() function."""

    def test_no_handler(self) -> None:
        name = "test_no_handler"
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        self.assertFalse(has_similar_handler(logger, handler))

    def test_identical_handler(self) -> None:
        name = "test_identical_handler"
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        logger.addHandler(handler)

        self.assertTrue(has_similar_handler(logger, handler))

    def test_identital_parent_handler(self) -> None:
        name = "test_identical_parent_handler"
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        logging.root.addHandler(handler)

        self.assertTrue(has_similar_handler(logger, handler))

    def test_duplicate_handler(self) -> None:
        name = "test_duplicate_handler"
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        logger.addHandler(handler)

        self.assertTrue(has_similar_handler(logger, logging.StreamHandler()))

    def test_different_name(self) -> None:
        name = "test_different_name"
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.name = name
        logger.addHandler(handler)

        self.assertFalse(has_similar_handler(logger, logging.StreamHandler()))

    def test_different_level(self) -> None:
        name = "test_different_level"
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.level = 9
        logger.addHandler(handler)

        self.assertFalse(has_similar_handler(logger, logging.StreamHandler()))

    def test_different_format_str(self) -> None:
        name = "test_different_format_str"
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        f = logging.Formatter()
        handler.setFormatter(f)
        logger.addHandler(handler)

        self.assertFalse(has_similar_handler(logger, logging.StreamHandler()))

    def test_different_class(self) -> None:
        """Handlers with identical criteria but different classes should not be similar."""
        name = "test_different_class"
        logger = logging.getLogger(name)
        h1 = logging.StreamHandler()
        h2 = logging.NullHandler()

        f = logging.Formatter()
        h1.setFormatter(f)
        h2.setFormatter(f)

        logger.addHandler(h1)

        self.assertEqual(h1.name, h2.name)
        self.assertEqual(h1.level, h2.level)
        self.assertEqual(_get_handler_formatter_str(h1), _get_handler_formatter_str(h2))

        self.assertFalse(has_similar_handler(logger, h2))


class TestNormalizeLoggers(CleanUpLoggersHandlersTestCase):
    """Unittests for normalize_loggers() function."""

    def test_normalize_loggers(self) -> None:
        logger_list: LoggerList = []
        with self.subTest(logger_list=logger_list):
            self.assertEqual([], normalize_logger_list(logger_list))

        logger_list = ["test_logger"]
        with self.subTest(logger_list=logger_list):
            self.assertEqual([logging.getLogger("test_logger")], normalize_logger_list(logger_list))

        logger_list = "test_logger"
        with self.subTest(logger_list=logger_list):
            self.assertEqual([logging.getLogger("test_logger")], normalize_logger_list(logger_list))

        logger_list = [logging.getLogger("test_logger")]
        with self.subTest(logger_list=logger_list):
            self.assertEqual([logging.getLogger("test_logger")], normalize_logger_list(logger_list))

        logger_list = logging.getLogger("test_logger")
        with self.subTest(logger_list=logger_list):
            self.assertEqual([logging.getLogger("test_logger")], normalize_logger_list(logger_list))

        logger_list = ["test_logger", logging.getLogger("test_logger2")]
        with self.subTest(logger_list=logger_list):
            self.assertEqual(
                [logging.getLogger("test_logger"), logging.getLogger("test_logger2")],
                normalize_logger_list(logger_list),
            )


if __name__ == "__main__":
    unittest.main()
