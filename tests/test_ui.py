"""core.ui submodule unittests."""

import enum
import unittest
from typing import Any

import plac  # type: ignore [import-untyped]

from core.ui import create_annotation_from_enum


class Color(enum.Enum):
    """RGB color enumeration."""

    RED = enum.auto()
    GREEN = enum.auto()
    BLUE = enum.auto()


@plac.annotations(
    color=create_annotation_from_enum(Color),
)
def main(color: Color) -> Color:
    """Main function for use with plac.Interpreter unittests."""
    return color


class TestCreateAnnotationFromEnum(unittest.TestCase):
    """Test create_annotation_from_enum function."""

    def test_basic_usage(self) -> None:
        """Test basic usage."""
        annotation = create_annotation_from_enum(Color)
        self.assertIsInstance(annotation, plac.Annotation)
        self.assertEqual(annotation.help, "one of ['RED', 'GREEN', 'BLUE']")

        self.assertEqual(annotation.type("RED"), Color.RED)

    def _catch_system_exit_on_plac_call(self, args) -> Any:
        try:
            return plac.call(main, args)
        except SystemExit as e:
            raise AssertionError(f"plac.call(main, {args}) raised SystemExit: {e}")

    def test_kind_argument(self) -> None:
        """Test 'kind' argument."""
        annotation = create_annotation_from_enum(Color, kind="option")
        self.assertEqual(annotation.kind, "option")

        annotation = create_annotation_from_enum(Color, kind="flag")
        self.assertEqual(annotation.kind, "flag")

    def test_invalid_args(self) -> None:
        """Test invalid arguments to create_annotation_from_enum and it's created annotation."""
        with self.assertRaises(AssertionError):
            create_annotation_from_enum(Color, kind="fake_kind")

        annotation = create_annotation_from_enum(Color)

        # Try to pass invalid value to annotation.type
        with self.assertRaises(KeyError):
            annotation.type("INVALID")

    def test_plac_interpreter(self) -> None:
        """Test plac interface directly with plac.Interpreter."""
        self.assertEqual(self._catch_system_exit_on_plac_call(["RED"]), Color.RED)
        self.assertEqual(self._catch_system_exit_on_plac_call(["BLUE"]), Color.BLUE)
        self.assertRaises(KeyError, self._catch_system_exit_on_plac_call, ["INVALID"])


if __name__ == "__main__":
    unittest.main()
