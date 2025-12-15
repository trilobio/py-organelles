"""Test py_organelles public API."""

import unittest
from importlib import import_module


class TestAPIs(unittest.TestCase):
    """Sanity checks of the __all__ attributes of py_organelles and it's submodules."""

    def _test_import_api(self, module_path: str) -> None:
        """Test importing all components in py_organelles.__all__."""
        target_module = import_module(module_path)
        for obj_name in target_module.__all__:
            with self.subTest(obj_name=obj_name):
                self.assertTrue(
                    hasattr(target_module, obj_name),
                    f"Module '{module_path}' is missing '{obj_name}' in its __all__.",
                )

    def test_py_organelles_api(self) -> None:
        """Test importing all components in py_organelles.__all__."""
        self._test_import_api("py_organelles")

    def test_log_tools_api(self) -> None:
        """Test importing all components in py_organelles.log_tools.__all__."""
        self._test_import_api("py_organelles.log_tools")
