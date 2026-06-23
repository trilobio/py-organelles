# Changelog

All notable changes to this project will be documented here.
Format: [Semantic Versioning](https://semver.org)

## [v1.4.0]
### Added
- `Runner` task-runner and documentation (docs/runner.md) of it's usage.
- `CommandError` plac-compatible exception for use in `Runner` tasks.
- Standard documentation for setting up commit-hooks to run `Runner` tasks on commit.
- `runner.py` at module-level for running py-organelles linting, formatting, and testing.

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
