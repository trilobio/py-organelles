"""Functions to assist in configuring multiple loggers."""

import atexit
import logging
import pathlib
import queue
import threading
import time
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

from py_organelles.log_tools.formatters import ColorFormatter
from py_organelles.log_tools.utilities import (
    LoggerList,
    has_similar_handler,
    normalize_logger_list,
)

BASIC_LOG_FORMAT_STR = "%(name)s.%(levelname)s: %(message)s"
DEBUG_LOG_FORMAT_STR = "%(asctime)s %(levelname)-7s - %(message)s"


def basic_logging_config(
    logger_list: LoggerList,
    stream_log_level: int = logging.INFO,
    format_str: str = BASIC_LOG_FORMAT_STR,
) -> None:
    """Attach stream_log_level streamhandler and DEBUG filehandler to each named logger.

    Note: If your handlers aren't showing up, check that the handlers aren't being
    removed by the has_similar_handler() function. The function compares the log level,
    name, and format_str of the desired handler to the handlers already attached to the logger
    and its parents. If the handler matches all of these criteria, it will not be attached.

    :param logger_list: logger(s) or name(s) of loggers to configure
    :param stream_log_level: logging level for StreamHandler, defaults to logging.INFO
    :param format_str: passed to logging.Formatter, defaults to BASIC_LOG_FORMAT_STR;
        See https://docs.python.org/3/library/logging.html#logrecord-attributes for format info
    """
    loggers = normalize_logger_list(logger_list)
    stream_formatter = ColorFormatter(format_str)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_log_level)
    stream_handler.setFormatter(stream_formatter)

    for logger in loggers:
        logger.setLevel(logging.DEBUG)
        if not has_similar_handler(logger, stream_handler):
            logger.addHandler(stream_handler)


class _DropOnFullQueueHandler(QueueHandler):
    """A QueueHandler that never blocks the logging caller.

    When the queue is full, records are dropped and counted instead of blocking.
    Once the queue has room again, a single WARNING record reporting the number
    of dropped records is enqueued.
    """

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__(log_queue)
        # self.queue is typed as a minimal queue protocol without put(); keep a
        # reference typed as queue.Queue for the non-blocking put calls.
        self._bounded_queue = log_queue
        self.dropped_records = 0

    def enqueue(self, record: logging.LogRecord) -> None:
        # Called with the handler lock held, so dropped_records is thread-safe.
        try:
            self._bounded_queue.put(record, block=False)
        except queue.Full:
            self.dropped_records += 1
            return
        if self.dropped_records:
            dropped, self.dropped_records = self.dropped_records, 0
            warning = logging.LogRecord(
                name=__name__,
                level=logging.WARNING,
                pathname=__file__,
                lineno=0,
                msg="Log queue overflowed: %d log record(s) dropped",
                args=(dropped,),
                exc_info=None,
            )
            try:
                self._bounded_queue.put(warning, block=False)
            except queue.Full:
                self.dropped_records += dropped


class _BoundedQueueListener(QueueListener):
    """A QueueListener whose stop() tolerates a full queue and repeated calls.

    The stdlib enqueue_sentinel() uses put_nowait, which raises queue.Full if
    the bounded queue is saturated at shutdown; retry until the listener thread
    (which is still draining the queue) frees up room. stop() is also made
    idempotent so the atexit hook is safe after an explicit stop().
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._stop_lock = threading.Lock()
        self._stopped = False

    def enqueue_sentinel(self) -> None:
        while True:
            try:
                super().enqueue_sentinel()
                return
            except queue.Full:
                time.sleep(0.01)

    def stop(self) -> None:
        with self._stop_lock:
            if self._stopped:
                return
            self._stopped = True
        super().stop()


def setup_debug_loggers(
    loggers: LoggerList,
    filepath: pathlib.Path,
    log_level: int = logging.INFO,
    max_bytes: int = int(200e6),
    backup_count: int = 5,
    format_str: str = DEBUG_LOG_FORMAT_STR,
    queue_size: int = 65_536,
) -> QueueListener:
    """Set up provided loggers to save debug logs to a file and stream info logs.

    Logging calls are non-blocking: records are placed on a bounded in-memory
    queue and a background thread writes them to a rotating file handler and a
    stream handler. This buffers slow-disk write spikes (e.g. SD cards) without
    stalling the calling thread. If the queue fills up, new records are dropped
    and a warning reporting the drop count is logged once the queue has room.

    The returned QueueListener is stopped (flushing buffered records) at
    interpreter exit via atexit; call its stop() method for earlier deterministic
    shutdown.

    :param loggers: logger(s) or name(s) of loggers to set up
    :type loggers: LoggerList
    :param filepath: Passed to logging.RotatingFileHandler. Parent dirs are created if
        they don't exist
    :type filepath: pathlib.Path
    :param log_level: logging level for StreamHandler, defaults to logging.INFO
    :type log_level: int
    :param max_bytes: Passed to logging.RotatingFileHandler, default is 200 MB
    :type max_bytes: int
    :param backup_count: Passed to logging.RotatingFileHandler, default is 5
    :type backup_count: int
    :param format_str: passed to logging.Formatter, defaults to DEBUG_LOG_FORMAT_STR;
        See https://docs.python.org/3/library/logging.html#logrecord-attributes for format info
    :type format_str: str
    :param queue_size: max number of log records buffered in memory before drops occur,
        defaults to 65,536
    :type queue_size: int
    :return: the started QueueListener draining the queue in a background thread
    :rtype: QueueListener
    """
    formatter = logging.Formatter(format_str)

    # Set up rotating file handler
    filepath.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(filepath, maxBytes=max_bytes, backupCount=backup_count)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Set up stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    # All I/O happens on the listener's background thread; loggers only enqueue.
    log_queue: queue.Queue = queue.Queue(maxsize=queue_size)
    listener = _BoundedQueueListener(
        log_queue, file_handler, stream_handler, respect_handler_level=True
    )
    listener.start()
    atexit.register(listener.stop)

    queue_handler = _DropOnFullQueueHandler(log_queue)
    for logger in normalize_logger_list(loggers):
        logger.addHandler(queue_handler)

    return listener
