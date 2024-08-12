"""Unit tests for log_tools.utilities submodule."""
import logging
import unittest

from log_tools.utilities import (
    _get_handler_formatter_str,
    get_handlers,
    has_similar_handler,
)


class LoggerHandlerTestCase(unittest.TestCase):
    """Base TestCase class, cleans up loggers & handlers between tests."""

    def setUp(self) -> None:
        if len(logging.root.manager.loggerDict) > 0:
            assert False, f"loggers left over from last test: {logging.root.manager.loggerDict}"
        assert (
            len(logging.root.handlers) == 0
        ), "Root logger has handlers not cleaned up from last test"

    def tearDown(self) -> None:
        """Clean up any loggers created during test."""
        names = list(logging.root.manager.loggerDict.keys())
        for n in names:
            del logging.root.manager.loggerDict[n]

        logging.root.handlers.clear()


class TestGetHandlers(LoggerHandlerTestCase):
    """Unittests for get_handlers() function."""

    def test_no_handler(self) -> None:
        name = "test_no_handler"
        l = logging.getLogger(name)
        self.assertTrue(len(get_handlers(l)) == 0)

    def test_no_handler_parent(self) -> None:
        name = "test_no_handler_parent"
        l = logging.getLogger(f"{name}.child")
        self.assertTrue(len(get_handlers(l)) == 0)

    def test_has_handler(self) -> None:
        name = "test_has_handler"
        l = logging.getLogger(name)
        h = logging.StreamHandler()
        l.addHandler(h)
        self.assertTrue(len(get_handlers(l)) == 1)

    def test_parent_has_handler(self) -> None:
        name = "test_parent_has_handler"
        l_parent = logging.getLogger(name)
        h = logging.StreamHandler()
        l_parent.addHandler(h)

        l = logging.getLogger(f"{name}.child")
        self.assertTrue(len(get_handlers(l)) == 1)

    def test_root_has_handler(self) -> None:
        name = "test_root_has_handler"
        h = logging.StreamHandler()
        logging.root.addHandler(h)

        l = logging.getLogger(name)
        self.assertTrue(len(get_handlers(l)) == 1)

    def test_no_duplicate_handlers(self) -> None:
        name = "test_no_duplicate_handlers"
        l_parent = logging.getLogger(name)
        h = logging.StreamHandler()
        l_parent.addHandler(h)

        l = logging.getLogger(f"{name}.child")
        l.addHandler(h)  # Duplicate handler is added
        self.assertTrue(
            len(get_handlers(l)) == 1,
            f"found {len(get_handlers(l))} handlers, not 1",
        )

    def test_nonduplicate_handlers(self) -> None:
        name = "test_nonduplicate_handlers"
        l_parent = logging.getLogger(name)
        h_parent = logging.StreamHandler()
        l_parent.addHandler(h_parent)

        l = logging.getLogger(f"{name}.child")
        h = logging.StreamHandler()
        l.addHandler(h)
        self.assertTrue(len(get_handlers(l)) == 2)


class TestHasSimilarHandler(LoggerHandlerTestCase):
    """Unittests for has_similar_handler() function."""

    def test_no_handler(self) -> None:
        name = "test_no_handler"
        l = logging.getLogger(name)
        h = logging.StreamHandler()
        self.assertFalse(has_similar_handler(l, h))

    def test_identical_handler(self) -> None:
        name = "test_identical_handler"
        l = logging.getLogger(name)
        h = logging.StreamHandler()
        l.addHandler(h)

        self.assertTrue(has_similar_handler(l, h))

    def test_identital_parent_handler(self) -> None:
        name = "test_identical_parent_handler"
        l = logging.getLogger(name)
        h = logging.StreamHandler()
        logging.root.addHandler(h)

        self.assertTrue(has_similar_handler(l, h))

    def test_duplicate_handler(self) -> None:
        name = "test_duplicate_handler"
        l = logging.getLogger(name)
        h = logging.StreamHandler()
        l.addHandler(h)

        self.assertTrue(has_similar_handler(l, logging.StreamHandler()))

    def test_different_name(self) -> None:
        name = "test_different_name"
        l = logging.getLogger(name)
        h = logging.StreamHandler()
        h.name = name
        l.addHandler(h)

        self.assertFalse(has_similar_handler(l, logging.StreamHandler()))

    def test_different_level(self) -> None:
        name = "test_different_level"
        l = logging.getLogger(name)
        h = logging.StreamHandler()
        h.level = 9
        l.addHandler(h)

        self.assertFalse(has_similar_handler(l, logging.StreamHandler()))

    def test_different_format_str(self) -> None:
        name = "test_different_format_str"
        l = logging.getLogger(name)
        h = logging.StreamHandler()
        f = logging.Formatter()
        h.setFormatter(f)
        l.addHandler(h)

        self.assertFalse(has_similar_handler(l, logging.StreamHandler()))

    def test_different_class(self) -> None:
        """Handlers with identical criteria but different classes should not be similar."""
        name = "test_different_class"
        l = logging.getLogger(name)
        h1 = logging.StreamHandler()
        h2 = logging.NullHandler()

        f = logging.Formatter()
        h1.setFormatter(f)
        h2.setFormatter(f)

        l.addHandler(h1)

        self.assertEqual(h1.name, h2.name)
        self.assertEqual(h1.level, h2.level)
        self.assertEqual(_get_handler_formatter_str(h1), _get_handler_formatter_str(h2))

        self.assertFalse(has_similar_handler(l, h2))


if __name__ == "__main__":
    unittest.main()
