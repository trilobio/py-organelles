"""Top-level API for the package."""

from py_organelles.log_tools.context_managers import modify_log_level, stream_logs
from py_organelles.log_tools.csv import csv_append_row, set_up_csv
from py_organelles.log_tools.decorators import log_enter_exit_factory, log_timer_factory
from py_organelles.log_tools.formatters import ColorFormatter, DurationFormatter
from py_organelles.log_tools.helper_functions import (
    BASIC_LOG_FORMAT_STR,
    DEBUG_LOG_FORMAT_STR,
    basic_logging_config,
    setup_debug_loggers,
)
from py_organelles.log_tools.semver_meta import SemverMeta, get_semver_meta
from py_organelles.log_tools.ui import (
    append_annotation,
    log_format_str_annotation,
    log_level_annotation,
    log_level_factory,
    output_dir_annotation,
    overwrite_annotation,
)
from py_organelles.log_tools.utilities import (
    LoggerList,
    get_handlers,
    has_similar_handler,
    normalize_logger_list,
)

__all__ = [
    "BASIC_LOG_FORMAT_STR",
    "DEBUG_LOG_FORMAT_STR",
    "ColorFormatter",
    "DurationFormatter",
    "LoggerList",
    "SemverMeta",
    "append_annotation",
    "basic_logging_config",
    "csv_append_row",
    "get_handlers",
    "get_semver_meta",
    "has_similar_handler",
    "log_enter_exit_factory",
    "log_format_str_annotation",
    "log_level_annotation",
    "log_level_factory",
    "log_timer_factory",
    "modify_log_level",
    "normalize_logger_list",
    "output_dir_annotation",
    "overwrite_annotation",
    "set_up_csv",
    "setup_debug_loggers",
    "stream_logs",
]
