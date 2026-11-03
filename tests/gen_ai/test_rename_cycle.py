"""Tests for the rename-cycle guard in schema migration.

Written by Claude.
"""

import threading
import unittest

from py_organelles.schema_versioning import (
    APIHistoryLog,
    CompatContext,
    MigrationRegistry,
    SchemaRegistry,
    migrate_data_to_latest,
)

# A broken guard loops forever, so migrate in a thread and fail rather than hang the suite.
TIMEOUT_S = 5.0


def _context(migrations: dict[str, dict[str, str | None]]) -> CompatContext:
    return CompatContext(
        migration_registry=MigrationRegistry(),
        schema_registry=SchemaRegistry(),
        api_history_log=APIHistoryLog(
            name="test_rename_cycle",
            increments={"v0.1.0": {"A": 1}},
            migrations=migrations,
        ),
    )


class TestRenameCycle(unittest.TestCase):
    """A schema renamed back to a name it already had raises, instead of looping forever."""

    def _assert_raises_promptly(self, context: CompatContext) -> None:
        errors: list[Exception] = []

        def migrate() -> None:
            try:
                migrate_data_to_latest({"type": "A", "schema_version": 1}, context=context)
            except Exception as err:
                errors.append(err)

        thread = threading.Thread(target=migrate, daemon=True)
        thread.start()
        thread.join(TIMEOUT_S)
        self.assertFalse(thread.is_alive(), "Migration didn't finish; infinite rename loop?")
        self.assertEqual([type(err) for err in errors], [RuntimeError])

    def test_self_rename(self) -> None:
        self._assert_raises_promptly(_context({"v0.2.0": {"A": "A"}}))

    def test_two_step_cycle(self) -> None:
        self._assert_raises_promptly(_context({"v0.2.0": {"A": "B"}, "v0.3.0": {"B": "A"}}))

    def test_three_step_cycle(self) -> None:
        self._assert_raises_promptly(
            _context({"v0.2.0": {"A": "B"}, "v0.3.0": {"B": "C"}, "v0.4.0": {"C": "A"}})
        )

    def test_rename_chain_is_not_a_cycle(self) -> None:
        context = _context({"v0.2.0": {"A": "B"}, "v0.3.0": {"B": "C"}})
        migrated = migrate_data_to_latest({"type": "A", "schema_version": 1}, context=context)
        self.assertEqual(migrated, {"type": "C", "schema_version": 1})
