"""unittests for kind.base submodule."""

import enum
import unittest

from py_organelles import KindBase


class TestKindBase(unittest.TestCase):
    """unittest class for KindBase class."""

    @enum.unique
    class TestKind(KindBase):
        """Test KindBase class."""

        A = enum.auto()
        B = enum.auto()
        C = enum.auto()

    def test_from_str(self) -> None:
        """unittests KindBase.from_str method."""
        self.assertEqual(self.TestKind.from_str("A"), self.TestKind.A)
        self.assertEqual(self.TestKind.from_str("b"), self.TestKind.B)
        self.assertEqual(self.TestKind.from_str("_c"), self.TestKind.C)
        with self.assertRaises(KeyError):
            self.TestKind.from_str("_d")


if __name__ == "__main__":
    unittest.main()
