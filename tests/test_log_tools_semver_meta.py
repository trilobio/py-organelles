import logging
import unittest
from unittest import mock

from py_organelles.log_tools import modify_log_level, semver_meta


class TestGetSemverMeta(unittest.TestCase):
    """Unittests for py_organelles.log_tools.get_semver_meta() function."""

    @mock.patch("py_organelles.log_tools.semver_meta.importlib.metadata.version")
    @mock.patch("py_organelles.log_tools.semver_meta._run")
    def test_get_semver_meta_normal_op(self, mock_run, mock_version) -> None:
        """Test that get_semver_meta() returns expected SemverMeta object."""
        # Setup mocks
        mock_version.return_value = "1.2.3"
        mock_run.side_effect = ["abc123", ""]  # git hash and clean status

        # Call the function
        meta = semver_meta.get_semver_meta("dummy-package")

        # Assert expected results
        self.assertEqual(meta.package_name, "dummy-package")
        self.assertEqual(meta.version, "1.2.3")
        self.assertEqual(meta.git_hash, "abc123")
        self.assertFalse(meta.git_dirty)

    @mock.patch("py_organelles.log_tools.semver_meta.importlib.metadata.version")
    @mock.patch("py_organelles.log_tools.semver_meta._run")
    def test_get_semver_meta_git_dirty(self, mock_run, mock_version) -> None:
        """Test that get_semver_meta() correctly identifies dirty git status."""
        # Setup mocks
        mock_version.return_value = "1.2.3"
        mock_run.side_effect = ["abc123", " M modified_file.py"]  # git hash and dirty status

        # Call the function
        meta = semver_meta.get_semver_meta("dummy-package")

        # Assert expected results
        self.assertEqual(meta.package_name, "dummy-package")
        self.assertEqual(meta.version, "1.2.3")
        self.assertEqual(meta.git_hash, "abc123")
        self.assertTrue(meta.git_dirty)

    @mock.patch("py_organelles.log_tools.semver_meta.importlib.metadata.version")
    @mock.patch("py_organelles.log_tools.semver_meta._run")
    def test_get_semver_meta_package_not_found(self, mock_run, mock_version) -> None:
        """Test that get_semver_meta() handles package not found error."""
        mock_version.side_effect = semver_meta.importlib.metadata.PackageNotFoundError(
            "nonexistent-package",
        )
        mock_run.side_effect = ["abc123", ""]

        # Call the function
        with modify_log_level(semver_meta._logger, logging.FATAL):
            meta = semver_meta.get_semver_meta("nonexistent-package")

        # Assert expected results
        self.assertEqual(meta.package_name, "nonexistent-package")
        self.assertEqual(meta.version, "unknown")
        self.assertEqual(meta.git_hash, "abc123")
        self.assertFalse(meta.git_dirty)

    @mock.patch("py_organelles.log_tools.semver_meta.importlib.metadata.version")
    @mock.patch("py_organelles.log_tools.semver_meta.subprocess.run")
    def test_get_semver_meta_git_command_failure(self, mock_subprocess_run, mock_version) -> None:
        """Test that get_semver_meta() handles git command failure."""
        # Setup mocks
        mock_version.return_value = "1.2.3"
        mock_subprocess_run.side_effect = Exception("Git command failed")

        # Call the function
        with modify_log_level(semver_meta._logger, logging.FATAL):
            meta = semver_meta.get_semver_meta("dummy-package")

        # Assert expected results
        self.assertEqual(meta.package_name, "dummy-package")
        self.assertEqual(meta.version, "1.2.3")
        self.assertEqual(meta.git_hash, "unknown")
        self.assertEqual(meta.git_dirty, None)
