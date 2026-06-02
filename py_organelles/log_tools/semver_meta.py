"""Tools for collecting and logging semantic version and git-related metadata of python tools."""

import importlib.metadata
import logging
import subprocess
from dataclasses import dataclass

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SemverMeta:
    """Metadata about a python package."""

    package_name: str
    version: str
    git_hash: str
    git_dirty: bool | None  # None means "couldn't determine"


def _run(cmd: list[str]) -> str | None:
    """Run a command and return its output, or 'unknown' if it fails."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        result.check_returncode()
        return result.stdout.strip()
    except Exception as err:
        _logger.error(f"Error running command '{' '.join(cmd)}': {err}")
        return None


def get_semver_meta(package_name: str) -> SemverMeta:
    """Generate SemverMeta data for a target package."""
    # Semantic Version
    try:
        version = importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
        _logger.error("Error determining package version: package not found")

    # Git metadata
    git_hash = _run(["git", "rev-parse", "HEAD"]) or "unknown"

    # Determine if git repo is dirty
    retval = _run(["git", "status", "--porcelain"])
    git_dirty = None if retval is None else len(retval) > 0

    return SemverMeta(
        package_name=package_name,
        version=version,
        git_hash=git_hash,
        git_dirty=git_dirty,
    )
