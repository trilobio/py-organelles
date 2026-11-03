"""Schema-versioned pydantic models, and migration of their data between schema versions."""

from py_organelles.core.factory import BuilderExistsError, BuilderNotFoundError
from py_organelles.schema_versioning.base import BaseSchemaVersionedModel
from py_organelles.schema_versioning.compat import (
    APIHistoryLog,
    APIVersion,
    CompatContext,
    DeprecatedSchemaError,
    InvalidDataError,
    SchemaName,
    SchemaVersion,
    SchemaVersionMismatchError,
    TargetSchemaExistsError,
    TargetSchemaNotFoundError,
    load_api_object,
    migrate_data_to_latest,
    migrate_data_to_version,
    resolve_api_profile,
)
from py_organelles.schema_versioning.registry import (
    BuilderFunc,
    MigrationRegistry,
    Migrator,
    RawData,
    RegistryKey,
    SchemaRegistry,
)

__all__ = [
    "APIHistoryLog",
    "APIVersion",
    "BaseSchemaVersionedModel",
    "BuilderExistsError",
    "BuilderFunc",
    "BuilderNotFoundError",
    "CompatContext",
    "DeprecatedSchemaError",
    "InvalidDataError",
    "MigrationRegistry",
    "Migrator",
    "RawData",
    "RegistryKey",
    "SchemaName",
    "SchemaRegistry",
    "SchemaVersion",
    "SchemaVersionMismatchError",
    "TargetSchemaExistsError",
    "TargetSchemaNotFoundError",
    "load_api_object",
    "migrate_data_to_latest",
    "migrate_data_to_version",
    "resolve_api_profile",
]
