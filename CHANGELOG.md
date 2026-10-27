# Changelog

All notable changes to this project will be documented here.
Format: [Semantic Versioning](https://semver.org)

## [Unreleased]

### Added

#### `schema_versioning` Submodule
- Schema-versioned pydantic models, and migration of their serialized data between schema
  versions. Moved from `tcode-api`, so that other projects (e.g. `config-db`) can share it.
  - `BaseSchemaVersionedModel`: a `schema_version` field and `read()` / `write()`, with no
    `model_config`, so that each project mixes in its own configured base model.
  - `SchemaRegistry` and `MigrationRegistry`, raising `core`'s `BuilderNotFoundError` and
    `BuilderExistsError`. Each project keeps its own instances; there are no module-level
    registries.
  - `CompatContext` and `APIHistoryLog`, and the functions that take one: `load_api_object`,
    `migrate_data_to_latest`, `migrate_data_to_version`, and `resolve_api_profile`.
  - `unversioned_is_v1` on `load_api_object`, `migrate_data_to_latest`, and
    `migrate_data_to_version`: whether data with no `schema_version` is version 1 of its schema,
    or an `InvalidDataError`. In `load_api_object`, a version looked up from `api_version` takes
    precedence. A nested schema with no `schema_version` is version 1 if set, and otherwise left
    as is.
- `packaging` dependency.

---

## [v3.0.0]

### Changed

#### `core` Submodule
- **Breaking.** `BuilderNotFoundError` now takes `(factory_name, factory_key, builder_keys=None,
  message=None)` and keeps them as attributes, instead of a single pre-formatted message. Callers
  constructing it by hand must pass the lookup that failed.

### Added

#### `core` Submodule
- `BuilderExistsError`, raised by both factories when registering over an existing key. Previously
  a bare `ValueError`.

### Fixed

#### `core` Submodule
- `MultiBuilderObjectFactory.register_builder` checks the builders registered under the given
  kind. It read the outer dict, keyed by builder kind, so a duplicate key never matched and
  silently replaced its builder.

---

## [v2.2.0]

### Changed

- `basic_logging_config` no longer writes any file to `/tmp` by default

## [v2.1.0]

### Fixed
- `LoggerList` typing now accepts a `Sequence[str | logging.Logger]` (not just `list[...]`).
- Pre-commit hook now fails the commit when any formatting, linting, or mypy check fails.

### Added
- Developer task runner for linting, formatting, testing.
- Add "frane" product type

---

## [v2.0.1]

### Fixed
- `LoggerList` typing now accepts a `Sequence[str | logging.Logger]` (not just `list[...]`).
- Pre-commit hook now fails the commit when any formatting, linting, or mypy check fails.

### Added
- Developer task runner for linting, formatting, testing.

---

## [v2.0.0]
### Changed
#### `log_tools` Submodule
- `setup_debug_loggers` is now non-blocking: records are placed on a bounded in-memory queue (new `queue_size` arg, default 65,536 records) and written to the file and stream handlers by a background thread, buffering slow-disk write spikes (e.g. SD cards) without stalling the calling thread. If the queue fills up, new records are dropped and a warning with the drop count is logged once the queue has room. The function now returns the `QueueListener`; it is stopped (flushing buffered records) automatically at interpreter exit, or call its `stop()` method for earlier deterministic shutdown.
### Removed
#### `log_tools` Submodule
- Structured logging API: `setup_structured_loggers`, `STRUCTURED_LOG_FORMAT_STR`, and `StructuredJSONMessage`.
- `python-json-logger` dependency.

---

## [v1.3.0]
### Added
#### `log_tools` Submodule
- `log_format_str_annotation` annotation for exposing standard log formatting string args in CLIs.
- `BASIC_LOG_FORMAT_STR`, `DEBUG_LOG_FORMAT_STR`, and `STRUCTURED_LOG_FORMAT_STR` constants corresponding to the default arguments for the three `log_tools` helper functions. Intended usage for building CLIs is as follows:
```
import logging

import plac  # type: ignore [import-untyped]

from py_organelles.log_tools import (
    BASIC_LOG_FORMAT_STR,
    basic_logging_config,
    log_format_str_annotation,
    log_level_annotation,
)

_logger = logging.getLogger(__name__)


@plac.annotations(
    log_format_str=log_format_str_annotation,
    log_level=log_level_annotation,
)
def main(
    log_format_str: str = BASIC_LOG_FORMAT_STR,
    log_level: int = logging.INFO,
):
    basic_logging_config(_logger, stream_log_level=log_level, format_str=log_format_str)
```
### Fixed
#### `log_tools` Submodule
- Bad documentation for helper function `setup_structured_loggers`.

---

## [v1.2.0]
### Added
#### `log_tools` submodule
- `get_semver_meta()` - retrieve version of the provided package, along with the current state of the git environment.
- `SemverMeta` - dataclass to hold the version and git environment information.
### Fixed
### Deprecated

---
