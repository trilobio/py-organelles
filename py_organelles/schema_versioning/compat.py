"""Code to manage compatibility between different versions of an API's schemas."""

import collections.abc
import dataclasses
import logging

from packaging.version import Version
from pydantic import ValidationError

from .base import BaseSchemaVersionedModel
from .registry import (
    BuilderNotFoundError,
    MigrationRegistry,
    Migrator,
    RawData,
    SchemaRegistry,
)

_logger = logging.getLogger(__name__)

APIVersion = str
SchemaVersion = int
SchemaName = str


@dataclasses.dataclass
class APIHistoryLog:
    """Data structure to track a given APIs evolution history."""

    name: str
    """API name (e.g. "tcode-api"), used for logging purposes."""

    increments: dict[APIVersion, dict[SchemaName, SchemaVersion]] = dataclasses.field(
        default_factory=dict
    )
    """Mapping of API versions to version increments of schemas in that version.

    Example:
        {
            "v0.1.0": {         # represents the initial supported release of the API
                "POUR_TEA": 1,
                "SMASH_CUP": 1,
                "TeaCup": 1,
            }
            "v0.1.1": {
                "POUR_TEA": 2,  # indicates that the ``POUR_TEA`` command was incremented to V2 in v0.1.1
                "TeaCup": 2,    # indicates that the ``TeaCup`` schema was incremented to V2 in v0.1.1
            },

            # Other versions may have been released, but because they didn't change the API,
            # they aren't represented in the changelog

            "v0.2.0": {
                "CoffeeCup": 1,  # indicates that the ``CoffeeCup`` schema was newly added in v0.2.0
                "POUR_COFFEE": 1,# indicates that the ``POUR_COFFEE`` command was newly added in v0.2.0
                "TeaCup": 3,     # indicates that the ``TeaCup`` schema was incremented to V3 in v0.2.0
        }
    """
    migrations: dict[APIVersion, dict[SchemaName, SchemaName | None]] = dataclasses.field(
        default_factory=dict
    )
    """Mapping of API versions to mappings of old schema names to new schema names.

    This functionality covers both renames (schema is the same but name changes) and replacements(schema is removed in favor of an existent schema).

    Example:
        {
            "v0.3.0": {
                "POUR_TEA": "POUR",  # indicates that the ``POUR_TEA`` command was replaced by ``POUR`` in v0.2.0
                "SMASH_CUP": None,   # indicates that the ``SMASH_CUP`` command was removed without replacement in v0.2.0
            }
        }
    """

    def get_most_recent_version(self) -> str:
        """Get the most recent API version in the history log."""
        return max(self.increments.keys(), key=Version)


@dataclasses.dataclass
class CompatContext:
    """Data structure unifying the state objects relevant for compatibility management.

    Each API defines one of these, and passes it to the functions in this module.
    """

    api_history_log: APIHistoryLog
    """The API history log to use for compatibility management."""

    migration_registry: MigrationRegistry
    """Registry of migrations between versions represented in ``api_history_log``."""

    schema_registry: SchemaRegistry
    """Registry of builders for schemas represented in the most modern version of the ``api_history_log``."""

    def known_schema_names(self) -> set[SchemaName]:
        names = set(self.schema_registry.keys)
        for renames in self.api_history_log.migrations.values():
            names.update(renames.keys())
        return names


class TargetSchemaNotFoundError(Exception):
    """Exception raised when a targeted schema is not found within in APIHistoryLog."""

    def __init__(
        self,
        schema_name: SchemaName,
        profile: dict[SchemaName, SchemaVersion],
        msg: str | None = None,
    ):
        if msg is None:
            msg = f"schema '{schema_name}' not valid within profile '{profile}'."
        super().__init__(msg)
        self.schema_name = schema_name
        self.profile = profile


class TargetSchemaExistsError(Exception):
    """Exception raised when a targeted schema already exists within in APIHistoryLog."""

    def __init__(
        self,
        schema_name: SchemaName,
        profile: dict[SchemaName, SchemaVersion],
        msg: str | None = None,
    ):
        if msg is None:
            msg = f"'{schema_name}' exists in '{profile}'."
        super().__init__(msg)
        self.schema_name = schema_name
        self.profile = profile


class InvalidDataError(ValueError):
    """Exception raised when data doesn't match schema expectations.

    Example cases include:
        * Missing 'type' key
        * 'schema_version' field doesn't match expected schema_version.
    """

    def __init__(self, data: RawData, msg: str | None = None):
        if msg is None:
            msg = f"Invalid data `{data}`"
        super().__init__(msg)
        self.data = data


class SchemaVersionMismatchError(Exception):
    """Exception raised on mismatching `schema_version` field in data and expected version from API."""

    def __init__(
        self,
        data: RawData,
        expected_schema_version: SchemaVersion,
        msg: str | None = None,
    ):
        if msg is None:
            msg = f"Expected schema version '{expected_schema_version}' but got '{data.get('schema_version')}' in data '{data}'."
        super().__init__(msg)
        self.data = data
        self.expected_schema_version = expected_schema_version


class DeprecatedSchemaError(Exception):
    """Exception raised when a schema is deprecated and cannot be migrated to the latest version."""

    def __init__(self, type: SchemaName, msg: str | None = None):
        if msg is None:
            msg = f"Schema '{type}' is deprecated in the latest API version and cannot be migrated."
        super().__init__(msg)
        self.type = type


def migrate_data_to_latest(
    data: RawData,
    context: CompatContext,
    *,
    schema_name: str | None = None,
    schema_version: int | None = None,
    recurse: bool = True,
    unversioned_is_v1: bool = False,
) -> RawData:
    """Migrate a given json blob to the latest version of its schema.

    :param data: The json blob to migrate.
    :param context: The targeted compatibility context.
    :param schema_name: The name of the schema to migrate. If not provided, will attempt to infer
        from the 'type' key in the data.
    :param schema_version: The version of the schema to migrate. If not provided, will attempt to
        infer from the 'schema_version' key in the data.
    :param recurse: Whether to migrate schemas nested inside this schema. Defaults to True.
    :param unversioned_is_v1: Whether data with no schema version is version 1 of its schema. If
        False, such data raises ``InvalidDataError``. Defaults to False.

    :returns: The migrated json blob, updated to match the latest version of the schema.
        If no migrators were found for the given schema, returns the data unchanged.

    :raises InvalidDataError: If the schema name or version cannot be inferred from the data and
        not provided as an argument.
    """
    return migrate_data_to_version(
        data,
        None,
        context,
        schema_name=schema_name,
        schema_version=schema_version,
        recurse=recurse,
        unversioned_is_v1=unversioned_is_v1,
    )


def migrate_data_to_version(
    data: RawData,
    target_version: int | None,
    context: CompatContext,
    *,
    schema_name: str | None = None,
    schema_version: int | None = None,
    recurse: bool | None = None,
    unversioned_is_v1: bool = False,
) -> RawData:
    """Migrate a given json blob to the specified version of it's schema.

    :param data: The json blob to migrate.
    :param target_version: The target version of the schema to migrate to. If None, will migrate
        to the latest version.
    :param context: The targeted compatibility context.
    :param schema_name: The name of the schema to migrate. If not provided, will attempt to infer
        from the 'type' key in the data.
    :param schema_version: The version of the schema to migrate. If not provided, will attempt to
        infer from the 'schema_version' key in the data.
    :param recurse: Whether to migrate schemas nested inside this schema. Only possible when
        we're migrating to the newest version (target_version is None). Defaults to None, which sets
        it to True iff target_version is None.
    :param unversioned_is_v1: Whether data with no schema version is version 1 of its schema. If
        False, such data raises ``InvalidDataError``. Defaults to False.

    :returns: The migrated json blob, updated to match the specified version of the schema.
        Its 'schema_version' is always set, even if no migrators were found for the given schema.

    :raises InvalidDataError: If any of the following are true:
        * the schema name or version cannot be inferred from the data and not provided as an
            argument.
        * the target version is older than the current version of the schema.
        * the target version has no registered migrator.

    """
    if recurse is None:
        recurse = target_version is None

    try:
        schema_name = schema_name or data["type"]
    except KeyError as err:
        raise InvalidDataError(
            msg="`schema_name` argument not supplied and no key 'type' in provided data",
            data=data,
        ) from err

    if schema_version is None:
        schema_version = data.get("schema_version")
        if schema_version is None:
            if not unversioned_is_v1:
                raise InvalidDataError(
                    msg=(
                        "`schema_version` argument not supplied and no key 'schema_version' in "
                        "provided data, and `unversioned_is_v1` is False"
                    ),
                    data=data,
                )
            schema_version = 1
    # Record the version we're migrating from, in case it didn't come from the data.
    data = {**data, "schema_version": schema_version}

    # Validate target version against current version
    if target_version is not None:
        if target_version == schema_version:
            return data  # No migration needed
        if target_version < schema_version:
            raise InvalidDataError(
                msg=f"Cannot migrate from version '{schema_version}' to version '{target_version}' for schema '{schema_name}' because the target version is older than the current version.",
                data=data,
            )

    try:
        final_name, migration_steps = _build_migrator_chain(
            incoming_name=schema_name,
            incoming_schema_version=schema_version,
            context=context,
            target_schema_version=target_version,
        )
    except ValueError as err:
        raise InvalidDataError(
            msg=f"Invalid migration path for data with type '{schema_name}' and schema_version '{schema_version}'.",
            data=data,
        ) from err

    if target_version is not None and target_version not in {v for _, v, _ in migration_steps}:
        raise InvalidDataError(
            msg=f"Cannot migrate from version '{schema_version}' to version '{target_version}' for schema '{schema_name}' because there is no registered migrator for the target version.",
            data=data,
        )

    for step_name, step_version, migrator in migration_steps:
        data = migrator(data)

    # Recurse, and migrate nested schemas.
    # We can only really do this if we're trying to migrate to the latest version.
    if recurse:
        if target_version is None:
            data = _migrate_nested_schemas_to_latest(
                context, data, unversioned_is_v1, skip_parent=True
            )
        else:
            raise RuntimeError("Can only migrate nested schemas to newest version")

    return {**data, "type": final_name}


def _migrate_nested_schemas_to_latest(
    context: CompatContext, data: RawData, unversioned_is_v1: bool, skip_parent: bool = False
) -> RawData:
    """Recursively migrate nested schemas.

    Because we don't reliably track the versions of nested schemas, this just migrates
    everything to the newest version.

    Also: this currently only reads the schema version embedded in the data as `schema_version`. It
    doesn't figure out the schema version from the overall API version, as `load_api_object`
    does.

    :param context: The targeted compatibility context.
    :param data: JSON-like data to migrate.
    :param unversioned_is_v1: Whether a nested schema with no ``schema_version`` is version 1. If
        False, it's left as is, rather than raising as at the top level: old data nests
        unversioned schemas that still validate.
    :param skip_parent: Don't migrate this object, only migrate nested ones.

    :returns: Data, migrated to newest versions.
    """

    if isinstance(data, list):
        return [_migrate_nested_schemas_to_latest(context, d, unversioned_is_v1) for d in data]
    if not isinstance(data, collections.abc.Mapping):
        return data

    schema_name = data.get("type")
    is_schema = isinstance(schema_name, str) and schema_name in context.known_schema_names()
    if (
        not skip_parent
        and is_schema
        and (data.get("schema_version") is not None or unversioned_is_v1)
    ):
        data = migrate_data_to_latest(
            data,
            context,
            recurse=False,  # We're recursing out here, don't need to do it twice
            unversioned_is_v1=unversioned_is_v1,
        )

    return {
        k: _migrate_nested_schemas_to_latest(context, v, unversioned_is_v1) for k, v in data.items()
    }


def resolve_api_profile(
    api_version: APIVersion,
    context: CompatContext,
) -> dict[SchemaName, SchemaVersion]:
    """Resolve a schema-version profile for the given API version.

    :param api_version: The API version to resolve the profile for.
    :param context: The targeted compatibility context.

    :returns: a mapping of schema names to their respective versions for the given API version,
        taking into account all changes up to that version.
    """
    requested = Version(api_version)

    profile: dict[SchemaName, SchemaVersion] = {}

    # Create sorted list of version strings that modified the API
    versions_of_note = sorted(
        set(context.api_history_log.increments.keys()).union(
            set(context.api_history_log.migrations.keys())
        ),
        key=Version,
    )
    for version_str in versions_of_note:
        # Check if we've got a modern enough version to return
        if Version(version_str) > requested:
            break

        # Handle increments
        if version_str in context.api_history_log.increments:
            for schema_name, schema_version in context.api_history_log.increments[
                version_str
            ].items():
                profile[schema_name] = schema_version

        # Handle migrations
        if version_str in context.api_history_log.migrations:
            for old_schema_name, new_schema_name in context.api_history_log.migrations[
                version_str
            ].items():
                if new_schema_name not in profile and new_schema_name is not None:
                    try:
                        profile[new_schema_name] = profile[old_schema_name]
                    except KeyError:
                        raise TargetSchemaNotFoundError(
                            schema_name=old_schema_name,
                            profile=profile,
                        )
                profile.pop(old_schema_name)

    return profile


def load_api_object(
    data: RawData,
    context: CompatContext,
    *,
    api_version: APIVersion | None = None,
    unversioned_is_v1: bool = False,
) -> BaseSchemaVersionedModel:
    """Given a data blob and the API version it corresponds to, return an instance of the most modern
        schema that the data can be migrated to.

    The data's schema version is its `schema_version` field. If that's absent, the version is
    looked up using `api_version`, if given. Failing both, we assume it's version 1 (if
    unversioned_is_v1 == True) or raise an error (if unversioned_is_v1 == False).

    :param data: The mapping of data to load.
    :param context: The targeted compatibility context.
    :param api_version: The API version to resolve the schema profile against for loading.
        If not given, uses `type` and `schema_version` fields in the data to resolve the schema.
    :param unversioned_is_v1: Whether data with no schema version is version 1 of its schema. If
        False, such data raises ``InvalidDataError``. Defaults to False.

    :returns: An instance of the most recent schema.

    :raises SchemaVersionMismatchError: If the schema_version targeted by the api_version doesn't match the
        schema_version of the provided data.
    :raises TargetSchemaNotFoundError: If the incoming data references a schema that doesn't exist in the
        API profile for the given api_version.
    :raises InvalidDataError: If the data is missing necessary keys to resolve the schema or
        doesn't match expected schema structure.
    :raises DeprecatedSchemaError: If the data references a schema that has been deprecated; only raised if
        no api_version argument provided.
    """
    try:
        incoming_name = data["type"]
        _logger.debug("data contains type='%s'", incoming_name)
    except KeyError as err:
        raise InvalidDataError(
            msg="Unable to find expected key 'type' in command schema",
            data=data,
        ) from err

    schema_version = data.get("schema_version")

    if api_version is not None:
        profile = resolve_api_profile(api_version, context)
        if incoming_name not in profile:
            raise TargetSchemaNotFoundError(
                msg=f"Schema '{incoming_name}' not valid for API version '{api_version}'.",
                schema_name=incoming_name,
                profile=profile,
            )

        # If we didn't get a schema_version from the data, look it up with the API version.
        if schema_version is None:
            _logger.debug("No `schema_version` in data, looking up using `api_version`.")
            schema_version = profile[incoming_name]

        if schema_version != profile[incoming_name]:
            raise SchemaVersionMismatchError(
                data=data,
                expected_schema_version=profile[incoming_name],
            )

    # Migrate data to the most recent accepted schema version for the incoming command.
    # `migrate_data_to_latest` follows renames and rewrites the "type" key to the final name.
    data = migrate_data_to_latest(
        data,
        context,
        schema_name=incoming_name,
        schema_version=schema_version,
        unversioned_is_v1=unversioned_is_v1,
    )
    new_name = data["type"]

    try:
        return context.schema_registry.build_instance(data=data, key=new_name)
    except ValidationError as err:
        raise InvalidDataError(
            msg=f"Data failed validation against schema '{new_name}' version '{data.get('schema_version')}'.",
            data=data,
        ) from err


MigrationStep = tuple[
    SchemaName, SchemaVersion, Migrator
]  # (name the migrator belongs to, version it migrates *to*, fn)


def _build_migrator_chain(
    incoming_name: SchemaName,
    incoming_schema_version: SchemaVersion,
    context: CompatContext,
    target_schema_version: SchemaVersion | None = None,
) -> tuple[SchemaName, list[MigrationStep]]:
    """Helper function to fetch all migrators necessary to migrate data from one schema_version to another, handling renames.

    :param incoming_name: The original name of the schema to migrate.
        if 'Teacup' was renamed to 'Cup' in a later version, provide 'Teacup'.
    :param incoming_schema_version: The version of the schema to migrate from.
    :param context: The targeted compatibility context.
    :param target_schema_version: The version of the schema to migrate to. If not provided, migrates
        to the latest version.

    :returns: The most recent name of the target schema and a list of migrator functions to apply in order.

    :raises ValueError: If there is a gap in the migration path (e.g. no migrator from v1 to v2, but
        there is a migrator from v2 to v3).
    :raises DeprecatedSchemaError: If the target schema is deprecated and cannot be migrated to the latest version.
    """
    migrators_to_apply: list[MigrationStep] = []

    current_name = incoming_name
    current_version = incoming_schema_version

    continue_traversing: bool = True
    while continue_traversing:
        # Fetch and sequentially store all migrators for current_name starting at current_version.
        try:
            migrators = context.migration_registry.get_migrators_for_schema(current_name)
        except BuilderNotFoundError:
            migrators = {}

        for version in sorted(migrators.keys()):
            if (target_schema_version is not None) and (target_schema_version <= current_version):
                break

            if version - current_version > 1:
                raise ValueError(
                    f"Cannot migrate from version '{current_version}' to version '{version}' for schema '{current_name}' because there is a gap in the migration path. Missing migrator for version '{current_version + 1}'."
                )

            # Only check for version on the input name. For all other names, we need to walk the entire version tree
            if current_name == incoming_name and version <= current_version:
                continue
            _logger.debug(
                "Adding migrator for '%s' from v%d to v%d to migrator chain",
                current_name,
                current_version,
                version,
            )
            migrators_to_apply.append((current_name, version, migrators[version]))
            current_version = version

        if target_schema_version is not None and current_version >= target_schema_version:
            break  # reached the target; don't follow renames past it

        # Check for renames in the API history log and update the current_name accordingly
        continue_traversing = False  # Set back to true if we find a rename
        for api_version_str in sorted(context.api_history_log.migrations, key=Version):
            for schema_name in context.api_history_log.migrations[api_version_str]:
                if schema_name == current_name:
                    new_name = context.api_history_log.migrations[api_version_str][schema_name]
                    if new_name is None:
                        raise DeprecatedSchemaError(type=schema_name)

                    current_name = new_name
                    _logger.debug(
                        "Found rename of '%s' to '%s' in API version '%s'",
                        schema_name,
                        current_name,
                        api_version_str,
                    )
                    continue_traversing = True
                    break
            if continue_traversing:
                break

    return current_name, migrators_to_apply
