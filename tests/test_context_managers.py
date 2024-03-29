"""Unittests for context_managers submodule."""
import unittest

from core.context_managers import modify_attribute


class TestModifyAttribute(unittest.TestCase):
    """Test the ModifyAttribute context manager."""

    class TestClass:
        def __init__(self, a: int, b: int, c: int):
            self.a = a
            self.b = b
            self.c = c

    def test_modify_single_attribute(self) -> None:
        """Test modify_attribute with single attribute."""
        obj = self.TestClass(a=1, b=2, c=3)
        orig_a = obj.a
        with modify_attribute(obj, "a", 10):
            self.assertEqual(obj.a, 10)

        self.assertEqual(obj.a, orig_a)

    def test_modify_multiple_attributes_one_target(self) -> None:
        """Test modify_attribute with multiple attributes of a single target."""
        obj = self.TestClass(a=1, b=2, c=3)
        orig_a, orig_b, orig_c = obj.a, obj.b, obj.c
        with modify_attribute(obj, ["a", "b", "c"], [10, 11, 12]):
            self.assertEqual(obj.a, 10)
            self.assertEqual(obj.b, 11)
            self.assertEqual(obj.c, 12)

        self.assertEqual(obj.a, orig_a)
        self.assertEqual(obj.b, orig_b)
        self.assertEqual(obj.c, orig_c)

    def test_modify_multiple_attributes_multiple_targets(self) -> None:
        """Test modify_attribute with multiple attributes of multiple targets."""
        obj_1 = self.TestClass(a=1, b=2, c=3)
        obj_2 = self.TestClass(a=1, b=2, c=3)
        orig_a_1, orig_c_2 = obj_1.a, obj_2.c

        with modify_attribute([obj_1, obj_2], ["a", "c"], [10, 11]):
            self.assertEqual(obj_1.a, 10)
            self.assertEqual(obj_1.c, 3)
            self.assertEqual(obj_2.a, 1)
            self.assertEqual(obj_2.c, 11)

        self.assertEqual(obj_1.a, orig_a_1)
        self.assertEqual(obj_2.c, orig_c_2)

    def test_bad_arguments(self) -> None:
        """Test modify_attribute catches bad arguments."""
        obj_1 = self.TestClass(a=1, b=2, c=3)
        obj_2 = self.TestClass(a=1, b=2, c=3)

        # Different length attribute and target
        with self.assertRaises(ValueError):
            with modify_attribute(obj_1, ["a", "b"], 10):
                pass

        with self.assertRaises(ValueError):
            with modify_attribute([obj_1, obj_2], "a", [10, 11]):
                pass


if __name__ == "__main__":
    unittest.main()
