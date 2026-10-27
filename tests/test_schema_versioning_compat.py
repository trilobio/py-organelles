"""Unittests for the API migration and compatibility logic."""

import logging
import unittest
from typing import Literal, cast

from py_organelles.log_tools import modify_log_level
from py_organelles.schema_versioning import (
    APIHistoryLog,
    BaseSchemaVersionedModel,
    CompatContext,
    DeprecatedSchemaError,
    InvalidDataError,
    MigrationRegistry,
    RawData,
    SchemaRegistry,
    SchemaVersionMismatchError,
    TargetSchemaNotFoundError,
    load_api_object,
    migrate_data_to_latest,
    migrate_data_to_version,
    resolve_api_profile,
)

COMPAT_LOGGER = logging.getLogger("py_organelles.schema_versioning.compat")


class TestResolveAPIProfile(unittest.TestCase):
    """Tests for the ``resolve_api_profile`` function."""

    def _assert_dicts_equal(self, dict1: dict, dict2: dict) -> None:
        """Helper method to assert that two dicts are equal, ignoring order."""
        missing_keys = set(dict1.keys()) - set(dict2.keys())
        extra_keys = set(dict2.keys()) - set(dict1.keys())
        bad_values = {
            key: (dict1[key], dict2[key])
            for key in dict1
            if key in dict2 and dict1[key] != dict2[key]
        }
        if len(missing_keys) > 0 or len(extra_keys) > 0 or len(bad_values) > 0:
            error_message = ("Dicts are not equal:\n  Dict1: {dict1}\n  Dict2: {dict2}\n").format(
                dict1=dict1, dict2=dict2
            )
            if len(missing_keys) > 0:
                error_message += f"  dict2 missing keys: {missing_keys}\n"
            if len(extra_keys) > 0:
                error_message += f"  dict2 has extra keys: {extra_keys}\n"
            if len(bad_values) > 0:
                for key, (value1, value2) in bad_values.items():
                    error_message += (
                        f"  Key '{key}' has different values: dict1={value1}, dict2={value2}\n"
                    )
            self.fail(error_message)

    def test_replacement_without_increments(self) -> None:
        """Test that a version that had a replacement without any increments still resolves correctly."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(),
            api_history_log=APIHistoryLog(
                name="",
                increments={
                    "v0.1.0": {"A": 1, "B": 1, "C": 1},
                    "v0.2.0": {"A": 2, "C": 2},
                },
                migrations={
                    "v0.1.1": {"B": "A"},
                },
            ),
        )

        self._assert_dicts_equal({"A": 2, "C": 2}, resolve_api_profile("v0.2.0", context))

    def test_rename_without_increment(self) -> None:
        """A version with a rename and no increment should resolve correctly."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(),
            api_history_log=APIHistoryLog(
                name="test_rename_without_increment",
                increments={
                    "v0.1.0": {"A": 1, "B": 1, "C": 1},
                    "v0.2.0": {"A": 2, "C": 2},
                },
                migrations={
                    "v0.1.1": {"B": "D"},
                },
            ),
        )

        self._assert_dicts_equal({"A": 2, "C": 2, "D": 1}, resolve_api_profile("v0.2.0", context))

    def test_increment_after_rename(self) -> None:
        """A schema renamed in a prior version should increment from the pre-renamed version."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(),
            api_history_log=APIHistoryLog(
                name="test_increment_after_rename",
                increments={
                    "v0.1.0": {"A": 1, "B": 1, "C": 1},
                    "v0.2.0": {"A": 2, "C": 2},
                    "v0.3.0": {"D": 2},
                },
                migrations={
                    "v0.2.0": {"B": "D"},
                },
            ),
        )

        self._assert_dicts_equal({"A": 2, "C": 2, "D": 2}, resolve_api_profile("v0.3.0", context))

    def test_increment_and_rename(self) -> None:
        """A schema that is incremented and renamed in a single version should show the increment with the new name."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(),
            api_history_log=APIHistoryLog(
                name="test_increment_after_rename",
                increments={
                    "v0.1.0": {"A": 1, "B": 1, "C": 1},
                    "v0.2.0": {"A": 2, "B": 2, "C": 2},
                },
                migrations={
                    "v0.2.0": {"B": "D"},
                },
            ),
        )

        self._assert_dicts_equal({"A": 2, "D": 2, "C": 2}, resolve_api_profile("v0.2.0", context))

    def test_rename_nonexistent(self) -> None:
        """A rename with a non-existent target raises an error."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(),
            api_history_log=APIHistoryLog(
                name="test_increment_after_rename",
                increments={
                    "v0.1.0": {"A": 1, "B": 1, "C": 1},
                    "v0.2.0": {"A": 2, "B": 2, "C": 2},
                },
                migrations={
                    "v0.2.0": {"D": "E"},
                },
            ),
        )

        with self.assertRaises(TargetSchemaNotFoundError):
            resolve_api_profile("v0.2.0", context)

    def test_too_early_version(self) -> None:
        """Requesting a version before the first increment should return an empty profile."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(),
            api_history_log=APIHistoryLog(
                name="test_too_early_version",
                increments={
                    "v0.1.0": {"A": 1, "B": 1, "C": 1},
                },
            ),
        )
        self._assert_dicts_equal(
            {},
            resolve_api_profile("v0.0.1", context),
        )

    def test_implied_version(self) -> None:
        """Requesting a version that doesn't exist should resolve to the latest version before it."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(),
            api_history_log=APIHistoryLog(
                name="test_nonexistent_version",
                increments={
                    "v0.1.0": {"A": 1, "B": 1, "C": 1},
                    "v0.2.0": {"A": 2, "C": 2},
                },
            ),
        )
        self._assert_dicts_equal(
            {"A": 1, "B": 1, "C": 1},
            resolve_api_profile("v0.1.5", context),
        )
        self._assert_dicts_equal(
            {"A": 2, "B": 1, "C": 2},
            resolve_api_profile("v0.2.5", context),
        )

    def test_invalid_version(self) -> None:
        """Test that an error is raised when an invalid version string is specified."""
        bad_versions = ["invalid_version", "version_0.1.0"]
        for bad_version in bad_versions:
            with self.subTest(bad_version=bad_version), self.assertRaises(ValueError):
                resolve_api_profile(
                    bad_version,
                    CompatContext(
                        migration_registry=MigrationRegistry(),
                        schema_registry=SchemaRegistry(),
                        api_history_log=APIHistoryLog(name="test_invalid_version"),
                    ),
                )

    def test_deprecated_version(self) -> None:
        """Test that a version that is deprecated does not show in the final profile."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(),
            api_history_log=APIHistoryLog(
                name="test_deprecated_version",
                increments={
                    "v0.1.0": {"A": 1, "B": 1, "C": 1},
                },
                migrations={
                    "v0.2.0": {"A": None},
                },
            ),
        )
        resolve_api_profile("v0.2.0", context)
        self._assert_dicts_equal(
            {"B": 1, "C": 1},
            resolve_api_profile("v0.2.0", context),
        )


class TeacupV1(BaseSchemaVersionedModel):
    """A test schema for testing the load_api_object function."""

    type: Literal["Teacup"] = "Teacup"
    schema_version: Literal[1] = 1


class TeacupV2(BaseSchemaVersionedModel):
    """A test schema for testing the load_api_object function."""

    type: Literal["Teacup"] = "Teacup"
    schema_version: Literal[2] = 2
    was_migrated: bool = False


class TeacupV3(BaseSchemaVersionedModel):
    """A test schema for testing the load_api_object function."""

    type: Literal["Teacup"] = "Teacup"
    schema_version: Literal[3] = 3
    was_migrated: bool = False


class TeacupV4(BaseSchemaVersionedModel):
    """A test schema for testing the load_api_object function."""

    type: Literal["Teacup"] = "Teacup"
    schema_version: Literal[4] = 4
    was_migrated: bool = False


class CupV1(BaseSchemaVersionedModel):
    """A test schema for testing the load_api_object function."""

    type: Literal["Cup"] = "Cup"
    schema_version: Literal[3] = 3
    was_migrated: bool = False


def migrate_teacup_v1_to_teacup_v2(data: RawData) -> RawData:
    """A simple migration function to migrate from TeacupV1 to TeacupV2."""
    return {
        "type": "Teacup",
        "schema_version": 2,
        "was_migrated": True,
    }


def migrate_teacup_v2_to_teacup_v3(data: RawData) -> RawData:
    """A simple migration function to migrate from TeacupV2 to TeacupV3()."""
    return {
        "type": "Teacup",
        "schema_version": 3,
        "was_migrated": True,
    }


def migrate_teacup_v2_to_teacup_v4(data: RawData) -> RawData:
    """A simple migration function to migrate from TeacupV2 to TeacupV4()."""
    return {
        "type": "Teacup",
        "schema_version": 4,
        "was_migrated": True,
    }


def migrate_teacup_v2_to_cup_v1(data: RawData) -> RawData:
    """A simple migration function to migrate from TeacupV2 to CupV1."""
    return {
        "type": "Cup",
        "schema_version": 3,
        "was_migrated": data.get("was_migrated", False),
    }


class TestLoadAPIObject(unittest.TestCase):
    """Tests for the ``load_api_object`` function."""

    def test_mismatched_schema_versions(self) -> None:
        """Test that an error is raised when the schema version targeted but the api_version doesn't
        match the schema_version in the data packet.
        """
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(
                {
                    "Teacup": TeacupV1,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_mismatched_schema_versions",
                increments={
                    "v0.1.0": {"Teacup": 1},
                    "v0.2.0": {"Teacup": 2},
                },
            ),
        )
        with (
            self.subTest(msg="schema_version is behind"),
            self.assertRaises(SchemaVersionMismatchError),
        ):
            load_api_object(
                data={"type": "Teacup", "schema_version": 1},
                api_version="v0.2.0",
                context=context,
            )

        with (
            self.subTest(msg="schema_version is ahead"),
            self.assertRaises(SchemaVersionMismatchError),
        ):
            load_api_object(
                data={"type": "Teacup", "schema_version": 2},
                api_version="v0.1.0",
                context=context,
            )

    def test_bad_schema_type(self) -> None:
        """Test that an error is raised when the data packet references a 'type' that isn't
        supported in the target API version.
        """
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(
                {
                    "Teacup": TeacupV1,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_bad_schema_type",
                increments={
                    "v0.1.0": {"Teacup": 1},
                },
            ),
        )
        with self.assertRaises(TargetSchemaNotFoundError):
            load_api_object(
                data={"type": "Saucer", "schema_version": "v0.1.0"},
                api_version="v0.2.0",
                context=context,
            )

    def test_missing_schema_type(self) -> None:
        """Test that an error is raised when the data packet doesn't include a 'type' field."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(
                {
                    "Teacup": TeacupV1,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_missing_schema_type",
                increments={
                    "v0.1.0": {"Teacup": 1},
                },
            ),
        )
        with self.assertRaises(InvalidDataError):
            load_api_object(
                data={"schema_version": "v0.1.0"},
                api_version="v0.2.0",
                context=context,
            )

    def test_determine_schema_version_from_api_version(self) -> None:
        """Test that if the data packet doesn't include a 'schema_version' field, the function
        determines the correct schema version based on the API version and the API history log.
        """
        context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={"Teacup": {2: migrate_teacup_v1_to_teacup_v2}},
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV2,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_determine_schema_version_from_api_version",
                increments={
                    "v0.1.0": {"Teacup": 1},
                    "v0.2.0": {"Teacup": 2},
                },
            ),
        )
        # This call should succeed and migrate the data from TeacupV1 to TeacupV2, even though the input data
        # doesn't specify a schema_version, because the api_version implies A is V1.
        with (
            modify_log_level(COMPAT_LOGGER, logging.ERROR),
            self.subTest(msg="migrate from TeacupV1 to TeacupV2 based on API version"),
        ):
            inst = load_api_object(
                data={"type": "Teacup"},
                api_version="v0.1.0",
                context=context,
            )
            self.assertIsInstance(inst, TeacupV2)
            self.assertEqual(inst.was_migrated, True)  # type: ignore [attr-defined]

        # This call should succeed and create the data as TeacupV2, even though the input data
        # doesn't specify a schema_version, because the api_version implies A is V2.
        with (
            modify_log_level(COMPAT_LOGGER, logging.ERROR),
            self.subTest(msg="Load TeacupV2 based on API version"),
        ):
            inst = load_api_object(
                data={"type": "Teacup"},
                api_version="v0.2.0",
                context=context,
            )
            self.assertIsInstance(inst, TeacupV2)
            cast(TeacupV2, inst)
            self.assertEqual(inst.was_migrated, False)  # type: ignore [attr-defined]

    def test_load_schema_versioned_data(self) -> None:
        """Test that data packets with a 'schema_version' field are loaded correctly."""
        context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={"Teacup": {2: migrate_teacup_v1_to_teacup_v2}},
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV2,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_load_schema_versioned_data",
                increments={
                    "v0.1.0": {"Teacup": 1},
                    "v0.2.0": {"Teacup": 2},
                },
            ),
        )
        # This call should succeed and load the data as TeacupV1
        for api_version in ["v0.1.0", "v0.1.5"]:
            with self.subTest(
                msg="Load TeacupV1 based on schema_version in data", api_version=api_version
            ):
                inst = load_api_object(
                    data={"type": "Teacup", "schema_version": 1},
                    api_version=api_version,
                    context=context,
                )
                self.assertIsInstance(inst, TeacupV2)
                self.assertEqual(inst.was_migrated, True)  # type: ignore [attr-defined]

    def test_migrate_through_a_rename(self) -> None:
        """Test that a data packet with an old name is migrated correctly."""
        context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={
                    "Teacup": {2: migrate_teacup_v1_to_teacup_v2},
                    "Cup": {3: migrate_teacup_v2_to_cup_v1},
                },
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV2,
                    "Cup": CupV1,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_migrate_through_a_rename",
                increments={
                    "v0.1.0": {"Teacup": 1},
                    "v0.2.0": {"Teacup": 2},
                    "v0.3.0": {"Cup": 2},
                },
                migrations={
                    "v0.3.0": {"Teacup": "Cup"},
                },
            ),
        )
        with self.subTest(_from="TeacupV1", _to="CupV1"):
            inst = load_api_object(
                data={"type": "Teacup", "schema_version": 1},
                context=context,
            )
            self.assertIsInstance(inst, CupV1)
            self.assertTrue(inst.was_migrated)  # type: ignore [attr-defined]

        with self.subTest(_from="TeacupV2", _to="CupV1"):
            inst = load_api_object(
                data={"type": "Teacup", "schema_version": 2},
                context=context,
            )
            self.assertIsInstance(inst, CupV1)
            self.assertFalse(inst.was_migrated)  # type: ignore [attr-defined]

        with self.subTest(_from="CupV1", _to="CupV1"):
            inst = load_api_object(
                data={"type": "Cup", "schema_version": 3},
                context=context,
            )
            self.assertIsInstance(inst, CupV1)
            self.assertFalse(inst.was_migrated)  # type: ignore [attr-defined]

        # No such thing as a Cup class with schema_version 1
        with self.assertRaises(InvalidDataError):
            load_api_object(
                data={"type": "Cup", "schema_version": 1},
                context=context,
            )

    def test_migrate_through_a_replacement(self) -> None:
        """Test that a data packet whose schema is replaced by another is migrated correctly."""

        class VesselV1(BaseSchemaVersionedModel):
            type: Literal["Vessel"] = "Vessel"
            schema_version: Literal[1] = 1
            volume: float
            was_migrated: bool = False

        def migrate_teacup_v2_to_vessel_v1(data: RawData) -> RawData:
            if data.get("type") != "Teacup" or data.get("schema_version") != 2:
                raise InvalidDataError(
                    data=data,
                    msg="Input data must be of type 'Teacup' with schema_version 2 to migrate to VesselV1",
                )
            return {
                "type": "Vessel",
                "volume": 250.0,
                "schema_version": 1,
                "was_migrated": True,
            }

        context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={
                    "Teacup": {2: migrate_teacup_v1_to_teacup_v2},
                    "Vessel": {1: migrate_teacup_v2_to_vessel_v1},
                },
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV2,
                    "Vessel": VesselV1,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_migrate_through_a_replacement",
                increments={
                    "v0.1.0": {"Teacup": 1},
                    "v0.2.0": {"Teacup": 2, "Vessel": 1},
                },
                migrations={
                    "v0.3.0": {"Teacup": "Vessel"},
                },
            ),
        )
        with self.subTest(_from="TeacupV1", _to="VesselV1"):
            inst = load_api_object(
                data={"type": "Teacup", "schema_version": 1},
                context=context,
            )
            self.assertIsInstance(inst, VesselV1)
            self.assertTrue(inst.was_migrated)  # type: ignore [attr-defined]

    def test_migrate_to_a_deprecation(self) -> None:
        """Test that a data packet whose schema is deprecated raises an error when loaded."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV1,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_migrate_to_a_deprecation",
                increments={
                    "v0.1.0": {"Teacup": 1},
                },
                migrations={
                    "v0.2.0": {"Teacup": None},
                },
            ),
        )

        for api_version in [None, "v0.2.0"]:
            with (
                self.subTest(api_version=api_version),
                self.assertRaises((TargetSchemaNotFoundError, DeprecatedSchemaError)),
            ):
                load_api_object(
                    data={"type": "Teacup", "schema_version": 1},
                    context=context,
                    api_version=api_version,
                )


class TestMigrateDataToLatest(unittest.TestCase):
    """Tests for the ``migrate_data_to_latest`` function."""

    def test_regression_packaging_version_type_error(self) -> None:
        """Regressoion test for migrate_data_to_latest raising a TypeError."""
        data = {"type": "Teacup", "schema_version": 1}
        context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={"Teacup": {2: migrate_teacup_v1_to_teacup_v2}},
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV2,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_regression_packaging_version_type_error",
                increments={
                    "v0.1.0": {"Teacup": 1},
                    "v0.2.0": {"Teacup": 2},
                },
            ),
        )
        migrated_data = migrate_data_to_latest(
            data=data,
            schema_name="Teacup",
            context=context,
        )
        self.assertEqual(migrated_data["schema_version"], 2)


class TestMigrateDataToVersion(unittest.TestCase):
    """Tests for the ``migrate_data_to_version`` function."""

    def setUp(self) -> None:
        """Shared context for all tests in this class."""

        #: Teacup model context with v1, v2, v3, and relevant migrators
        self.context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={
                    "Teacup": {
                        2: migrate_teacup_v1_to_teacup_v2,
                        3: migrate_teacup_v2_to_teacup_v3,
                    }
                },
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV3,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_identical_version",
                increments={
                    "v0.1.0": {"Teacup": 1},
                    "v0.2.0": {"Teacup": 2},
                    "v0.3.0": {"Teacup": 3},
                },
            ),
        )

        # Teacup model context with v1 and no migrators
        self.context_wo_migrators = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV1,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_no_migrators",
                increments={
                    "v0.1.0": {"Teacup": 1},
                },
            ),
        )

        # Teacup model context with v1, v2, v4, and relevant migrators (no v3)
        self.context_wo_v3 = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={
                    "Teacup": {
                        2: migrate_teacup_v1_to_teacup_v2,
                        4: migrate_teacup_v2_to_teacup_v4,
                    }
                },
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV4,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_no_v3",
                increments={
                    "v0.1.0": {"Teacup": 1},
                    "v0.2.0": {"Teacup": 2},
                    "v0.4.0": {"Teacup": 4},
                },
            ),
        )

    def test_no_migrators(self) -> None:
        """Running migrate_data_to_version with no migrators should return the input data unchanged."""
        data = {"type": "Teacup", "schema_version": 1}
        migrated_data = migrate_data_to_version(
            data=data,
            schema_name="Teacup",
            target_version=1,
            context=self.context_wo_migrators,
        )
        self.assertEqual(migrated_data, data)

    def test_identical_version(self) -> None:
        """Running migrate_data_to_version with the input schema's version should return the input data unchanged."""
        data = {"type": "Teacup", "schema_version": 1}
        for context in [self.context, self.context_wo_migrators, self.context_wo_v3]:
            with self.subTest(context=context):
                migrated_data = migrate_data_to_version(
                    data=data,
                    schema_name="Teacup",
                    target_version=1,
                    context=context,
                )
                self.assertEqual(migrated_data, data)

    def test_previous_version(self) -> None:
        """Running migrate_data_to_version with a target version lower than the input schema's version should raise an error."""
        data = {"type": "Teacup", "schema_version": 2}
        for context in [self.context, self.context_wo_migrators, self.context_wo_v3]:
            with self.subTest(context=context):
                with self.assertRaises(InvalidDataError):
                    migrate_data_to_version(
                        data=data,
                        schema_name="Teacup",
                        target_version=1,
                        context=context,
                    )

    def test_future_not_latest_version(self) -> None:
        """Running migrate_data_to_version with input_data_version < target_version < latest_version should migrate the data to the target version."""
        data = {"type": "Teacup", "schema_version": 1}
        for context in [self.context, self.context_wo_v3]:
            with self.subTest(context=context):
                migrated_data = migrate_data_to_version(
                    data=data,
                    schema_name="Teacup",
                    target_version=2,
                    context=context,
                )
                self.assertEqual(migrated_data["schema_version"], 2)

    def test_future_latest_version(self) -> None:
        """Running migrate_data_to_version with input_data_version < target_version == latest_version should migrate the data to the target version."""
        data = {"type": "Teacup", "schema_version": 1}
        migrated_data = migrate_data_to_version(
            data=data,
            schema_name="Teacup",
            target_version=3,
            context=self.context,
        )
        self.assertEqual(migrated_data["schema_version"], 3)

    def test_nonexistent_future_version(self) -> None:
        """Running migrate_data_to_version with input_data_version < target_version > latest_version should raise an error."""
        data = {"type": "Teacup", "schema_version": 1}
        for context in [self.context, self.context_wo_migrators, self.context_wo_v3]:
            with self.subTest(context=context):
                with self.assertRaises(InvalidDataError):
                    migrate_data_to_version(
                        data=data,
                        schema_name="Teacup",
                        target_version=5,
                        context=context,
                    )

    def test_nonexistent_intermediate_version(self) -> None:
        """Running migrate_data_to_version with input_data_version < target_version < latest_version but no migrator for the intermediate version should raise an error."""
        data = {"type": "Teacup", "schema_version": 1}
        with self.assertRaises(InvalidDataError):
            migrate_data_to_version(
                data=data,
                schema_name="Teacup",
                target_version=3,
                context=self.context_wo_v3,
            )


class TrayV2(BaseSchemaVersionedModel):
    """A test schema that holds nested Teacups, for testing nested migration."""

    type: Literal["Tray"] = "Tray"
    schema_version: Literal[2] = 2
    cup: TeacupV3 | None = None
    cups: list[TeacupV3] = []


class PlatterV1(BaseSchemaVersionedModel):
    """A test schema that Tray is renamed to, for testing nested migration through a rename."""

    type: Literal["Platter"] = "Platter"
    schema_version: Literal[3] = 3
    cup: TeacupV3 | None = None
    cups: list[TeacupV3] = []


def migrate_tray_v1_to_tray_v2(data: RawData) -> RawData:
    """Migrate TrayV1 to TrayV2, renaming the `mug` field to `cup`."""
    new_data = {k: v for k, v in data.items() if k != "mug"}
    return {**new_data, "schema_version": 2, "cup": data.get("mug")}


def migrate_tray_v2_to_platter_v1(data: RawData) -> RawData:
    """Migrate TrayV2 to PlatterV1, keeping the nested data."""
    return {**data, "type": "Platter", "schema_version": 3}


#: A migrated-to-latest Teacup, as produced by the Teacup migrators.
MIGRATED_TEACUP = TeacupV3(was_migrated=True).model_dump()


class TestMigrateNestedSchemas(unittest.TestCase):
    """Tests for migrating schemas nested inside other schemas."""

    def setUp(self) -> None:
        """Shared context: Tray v1 -> v2, containing Teacups v1 -> v3."""
        self.context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={
                    "Teacup": {
                        2: migrate_teacup_v1_to_teacup_v2,
                        3: migrate_teacup_v2_to_teacup_v3,
                    },
                    "Tray": {2: migrate_tray_v1_to_tray_v2},
                },
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV3,
                    "Tray": TrayV2,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_migrate_nested_schemas",
                increments={
                    "v0.1.0": {"Teacup": 1, "Tray": 1},
                    "v0.2.0": {"Teacup": 2, "Tray": 2},
                    "v0.3.0": {"Teacup": 3},
                },
            ),
        )

    def _migrate(self, data: dict, **kwargs) -> RawData:
        return migrate_data_to_latest(data=data, context=self.context, **kwargs)

    def test_nested_field(self) -> None:
        """A schema in a field of the parent is migrated, after the parent's own migrator has
        moved it (`mug` -> `cup`)."""
        migrated = self._migrate(
            {"type": "Tray", "schema_version": 1, "mug": TeacupV1().model_dump()}
        )
        self.assertEqual(migrated["schema_version"], 2)
        self.assertNotIn("mug", migrated)
        self.assertEqual(migrated["cup"], MIGRATED_TEACUP)

    def test_parent_already_latest(self) -> None:
        """Children are migrated even when the parent needs no migration itself."""
        migrated = self._migrate(
            {"type": "Tray", "schema_version": 2, "cup": TeacupV1().model_dump()}
        )
        self.assertEqual(migrated["cup"], MIGRATED_TEACUP)

    def test_nested_list(self) -> None:
        """Every schema in a list is migrated, from whatever version it's at."""
        migrated = self._migrate(
            {
                "type": "Tray",
                "schema_version": 2,
                "cups": [TeacupV1().model_dump(), TeacupV2().model_dump(), TeacupV3().model_dump()],
            }
        )
        self.assertEqual(
            migrated["cups"],
            [MIGRATED_TEACUP, MIGRATED_TEACUP, TeacupV3().model_dump()],
        )

    def test_nested_dict_values(self) -> None:
        """Schemas stored as values of a plain (non-schema) dict are migrated."""
        migrated = self._migrate(
            {"type": "Tray", "schema_version": 2, "cups_by_name": {"a": TeacupV1().model_dump()}}
        )
        self.assertEqual(migrated["cups_by_name"], {"a": MIGRATED_TEACUP})

    def test_deeply_nested(self) -> None:
        """Schemas nested several levels deep, including inside other nested schemas, are
        migrated."""
        migrated = self._migrate(
            {
                "type": "Tray",
                "schema_version": 2,
                "stack": {
                    "trays": [{"type": "Tray", "schema_version": 1, "mug": TeacupV1().model_dump()}]
                },
            }
        )
        inner = migrated["stack"]["trays"][0]
        self.assertEqual(inner["schema_version"], 2)
        self.assertNotIn("mug", inner)
        self.assertEqual(inner["cup"], MIGRATED_TEACUP)

    def test_nested_without_schema_version_untouched(self) -> None:
        """Without `unversioned_is_v1`, a nested object with no `schema_version` can't be
        migrated, so is left alone."""
        migrated = self._migrate({"type": "Tray", "schema_version": 2, "cup": {"type": "Teacup"}})
        self.assertEqual(migrated["cup"], {"type": "Teacup"})

    def test_nested_unregistered_type_untouched(self) -> None:
        """A nested object whose `type` isn't a registered schema is left alone."""
        saucer = {"type": "Saucer", "schema_version": 1}
        migrated = self._migrate({"type": "Tray", "schema_version": 2, "saucer": saucer})
        self.assertEqual(migrated["saucer"], saucer)

    def test_nested_non_string_type_untouched(self) -> None:
        """A nested object whose `type` isn't a string (so can't name a schema) is left alone.

        .. note:: Generated by Claude Opus 5.5.
        """
        spec = {"type": ["string", "null"], "schema_version": 1}
        migrated = self._migrate({"type": "Tray", "schema_version": 2, "spec": spec})
        self.assertEqual(migrated["spec"], spec)

    def test_primitives_untouched(self) -> None:
        """Non-schema values alongside nested schemas pass through unchanged."""
        migrated = self._migrate(
            {
                "type": "Tray",
                "schema_version": 2,
                "label": "tea",
                "count": 3,
                "tags": ["a", None, 1.5],
                "cup": None,
            }
        )
        self.assertEqual(migrated["label"], "tea")
        self.assertEqual(migrated["count"], 3)
        self.assertEqual(migrated["tags"], ["a", None, 1.5])
        self.assertIsNone(migrated["cup"])

    def test_input_not_mutated(self) -> None:
        """Nested migration returns new data rather than modifying the input."""
        data = {
            "type": "Tray",
            "schema_version": 2,
            "cup": TeacupV1().model_dump(),
            "cups": [TeacupV1().model_dump()],
        }
        self._migrate(data)
        self.assertEqual(
            data,
            {
                "type": "Tray",
                "schema_version": 2,
                "cup": TeacupV1().model_dump(),
                "cups": [TeacupV1().model_dump()],
            },
        )

    def test_recurse_false(self) -> None:
        """With `recurse=False`, only the top-level schema is migrated."""
        migrated = self._migrate(
            {"type": "Tray", "schema_version": 1, "mug": TeacupV1().model_dump()}, recurse=False
        )
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["cup"], TeacupV1().model_dump())

    def test_target_version_does_not_recurse(self) -> None:
        """Migrating to a specific version doesn't recurse by default, since nested schemas can
        only be migrated to latest."""
        migrated = migrate_data_to_version(
            data={"type": "Tray", "schema_version": 1, "mug": TeacupV1().model_dump()},
            target_version=2,
            context=self.context,
        )
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["cup"], TeacupV1().model_dump())

    def test_target_version_with_recurse_raises(self) -> None:
        """Explicitly asking to recurse while migrating to a specific version is an error."""
        with self.assertRaises(RuntimeError):
            migrate_data_to_version(
                data={"type": "Tray", "schema_version": 1, "mug": TeacupV1().model_dump()},
                target_version=2,
                context=self.context,
                recurse=True,
            )

    def test_load_api_object_builds_nested(self) -> None:
        """`load_api_object` migrates nested schemas so the result validates against the latest
        parent schema."""
        inst = load_api_object(
            data={
                "type": "Tray",
                "schema_version": 1,
                "mug": TeacupV1().model_dump(),
                "cups": [TeacupV2().model_dump()],
            },
            context=self.context,
        )
        self.assertIsInstance(inst, TrayV2)
        inst = cast(TrayV2, inst)
        self.assertIsInstance(inst.cup, TeacupV3)
        self.assertTrue(inst.cup.was_migrated)  # type: ignore [union-attr]
        self.assertTrue(inst.cups[0].was_migrated)

    @staticmethod
    def _renamed_parent_context() -> CompatContext:
        """Context where Tray (v1 -> v2) is renamed to Platter (v3), containing Teacups."""
        return CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={
                    "Teacup": {
                        2: migrate_teacup_v1_to_teacup_v2,
                        3: migrate_teacup_v2_to_teacup_v3,
                    },
                    "Tray": {2: migrate_tray_v1_to_tray_v2},
                    "Platter": {3: migrate_tray_v2_to_platter_v1},
                },
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV3,
                    "Platter": PlatterV1,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_parent_renamed",
                increments={
                    "v0.1.0": {"Teacup": 1, "Tray": 1},
                    "v0.2.0": {"Teacup": 2, "Tray": 2},
                    "v0.3.0": {"Teacup": 3, "Platter": 3},
                },
                migrations={"v0.3.0": {"Tray": "Platter"}},
            ),
        )

    def test_parent_renamed(self) -> None:
        """Nested schemas are migrated when the parent is migrated through a rename."""
        context = self._renamed_parent_context()
        data = {
            "type": "Tray",
            "schema_version": 1,
            "mug": TeacupV1().model_dump(),
            "cups": [TeacupV1().model_dump()],
        }

        migrated = migrate_data_to_latest(data=data, context=context)
        self.assertEqual(migrated["type"], "Platter")
        self.assertEqual(migrated["schema_version"], 3)
        self.assertEqual(migrated["cup"], MIGRATED_TEACUP)
        self.assertEqual(migrated["cups"], [MIGRATED_TEACUP])

        inst = load_api_object(data=data, context=context)
        self.assertIsInstance(inst, PlatterV1)

    def test_target_version_before_rename(self) -> None:
        """Migrating to a target version that predates a rename keeps the old name."""
        context = self._renamed_parent_context()
        data = {"type": "Tray", "schema_version": 1, "mug": TeacupV1().model_dump()}

        with self.subTest(target_version=2):
            migrated = migrate_data_to_version(data=data, target_version=2, context=context)
            self.assertEqual(migrated["type"], "Tray")
            self.assertEqual(migrated["schema_version"], 2)
            self.assertEqual(migrated["cup"], TeacupV1().model_dump())

        with self.subTest(target_version=3):
            migrated = migrate_data_to_version(data=data, target_version=3, context=context)
            self.assertEqual(migrated["type"], "Platter")
            self.assertEqual(migrated["schema_version"], 3)

    def test_nested_renamed(self) -> None:
        """A nested schema that was later renamed is migrated to its new name."""
        context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={
                    "Teacup": {2: migrate_teacup_v1_to_teacup_v2},
                    "Cup": {3: migrate_teacup_v2_to_cup_v1},
                },
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Cup": CupV1,
                    "Tray": TrayV2,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_nested_renamed",
                increments={
                    "v0.1.0": {"Teacup": 1, "Tray": 2},
                    "v0.2.0": {"Teacup": 2},
                    "v0.3.0": {"Cup": 3},
                },
                migrations={"v0.3.0": {"Teacup": "Cup"}},
            ),
        )
        migrated = migrate_data_to_latest(
            data={"type": "Tray", "schema_version": 2, "cup": TeacupV1().model_dump()},
            context=context,
        )
        self.assertEqual(migrated["cup"]["type"], "Cup")
        self.assertEqual(migrated["cup"]["schema_version"], 3)

    def test_nested_renamed_twice(self) -> None:
        """A nested schema renamed more than once is migrated through every rename."""
        context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={
                    "Teacup": {2: migrate_teacup_v1_to_teacup_v2},
                    "Mug": {3: migrate_teacup_v2_to_cup_v1},
                },
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Cup": CupV1,
                    "Tray": TrayV2,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_nested_renamed_twice",
                increments={
                    "v0.1.0": {"Teacup": 1, "Tray": 2},
                    "v0.2.0": {"Teacup": 2},
                    "v0.3.0": {"Mug": 3},
                },
                migrations={"v0.3.0": {"Teacup": "Mug"}, "v0.4.0": {"Mug": "Cup"}},
            ),
        )
        migrated = migrate_data_to_latest(
            data={
                "type": "Tray",
                "schema_version": 2,
                "cups": [TeacupV1().model_dump(), TeacupV2().model_dump()],
            },
            context=context,
        )
        expected = {"type": "Cup", "schema_version": 3, "was_migrated": True}
        self.assertEqual(migrated["cups"], [expected, {**expected, "was_migrated": False}])

    def test_nested_deprecated(self) -> None:
        """A nested schema that was deprecated raises, matching top-level behavior."""
        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(
                _builders_to_preload={"Tray": TrayV2},
            ),
            api_history_log=APIHistoryLog(
                name="test_nested_deprecated",
                increments={"v0.1.0": {"Teacup": 1, "Tray": 2}},
                migrations={"v0.2.0": {"Teacup": None}},
            ),
        )
        with self.assertRaises(DeprecatedSchemaError):
            migrate_data_to_latest(
                data={"type": "Tray", "schema_version": 2, "cup": TeacupV1().model_dump()},
                context=context,
            )


class TestUnversionedData(unittest.TestCase):
    """Data with no `schema_version` is version 1 or an error, per `unversioned_is_v1`.

    .. note:: Generated by Claude Opus 5.5.
    """

    def setUp(self) -> None:
        """Shared context: Tray v1 -> v2, containing Teacups v1 -> v3."""
        self.context = CompatContext(
            migration_registry=MigrationRegistry(
                _migrators_to_preload={
                    "Teacup": {
                        2: migrate_teacup_v1_to_teacup_v2,
                        3: migrate_teacup_v2_to_teacup_v3,
                    },
                    "Tray": {2: migrate_tray_v1_to_tray_v2},
                },
            ),
            schema_registry=SchemaRegistry(
                _builders_to_preload={
                    "Teacup": TeacupV3,
                    "Tray": TrayV2,
                },
            ),
            api_history_log=APIHistoryLog(
                name="test_unversioned_data",
                increments={
                    "v0.1.0": {"Teacup": 1, "Tray": 1},
                    "v0.2.0": {"Teacup": 2, "Tray": 2},
                    "v0.3.0": {"Teacup": 3},
                },
            ),
        )

    def test_migrate_raises_by_default(self) -> None:
        for target_version in [None, 2]:
            with (
                self.subTest(target_version=target_version),
                self.assertRaises(InvalidDataError),
            ):
                migrate_data_to_version({"type": "Teacup"}, target_version, context=self.context)

    def test_migrate_as_v1(self) -> None:
        with self.subTest(target_version=None):
            migrated = migrate_data_to_latest(
                {"type": "Teacup"}, context=self.context, unversioned_is_v1=True
            )
            self.assertEqual(migrated, MIGRATED_TEACUP)

        with self.subTest(target_version=2):
            migrated = migrate_data_to_version(
                {"type": "Teacup"}, 2, context=self.context, unversioned_is_v1=True
            )
            self.assertEqual(migrated["schema_version"], 2)

    def test_load_raises_by_default(self) -> None:
        with self.assertRaises(InvalidDataError):
            load_api_object({"type": "Teacup"}, context=self.context)

    def test_load_as_v1(self) -> None:
        inst = load_api_object({"type": "Teacup"}, context=self.context, unversioned_is_v1=True)
        self.assertEqual(inst, TeacupV3(was_migrated=True))

    def test_api_version_takes_precedence(self) -> None:
        """A version looked up from `api_version` is used over the flag's default of 1."""
        for unversioned_is_v1 in [False, True]:
            with self.subTest(unversioned_is_v1=unversioned_is_v1):
                inst = load_api_object(
                    {"type": "Teacup"},
                    context=self.context,
                    api_version="v0.3.0",
                    unversioned_is_v1=unversioned_is_v1,
                )
                self.assertEqual(inst, TeacupV3(was_migrated=False))

    def test_nested_as_v1(self) -> None:
        """With the flag, a nested schema with no `schema_version` is migrated from v1, rather
        than left alone."""
        migrated = migrate_data_to_latest(
            {"type": "Tray", "mug": {"type": "Teacup"}},
            context=self.context,
            unversioned_is_v1=True,
        )
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["cup"], MIGRATED_TEACUP)

    def test_unmigrated_data_gets_version(self) -> None:
        """Unversioned data with nothing to migrate still comes out versioned, so it builds even
        when the schema has no default `schema_version`."""

        class SaucerV1(BaseSchemaVersionedModel):
            type: Literal["Saucer"] = "Saucer"

        context = CompatContext(
            migration_registry=MigrationRegistry(),
            schema_registry=SchemaRegistry(_builders_to_preload={"Saucer": SaucerV1}),
            api_history_log=APIHistoryLog(
                name="test_unmigrated_data_gets_version",
                increments={"v0.1.0": {"Saucer": 1}},
            ),
        )
        migrated = migrate_data_to_latest(
            {"type": "Saucer"}, context=context, unversioned_is_v1=True
        )
        self.assertEqual(migrated, {"type": "Saucer", "schema_version": 1})
        inst = load_api_object({"type": "Saucer"}, context=context, unversioned_is_v1=True)
        self.assertEqual(inst, SaucerV1(schema_version=1))
