"""Publishing a robot telemetry source.

A source is one JSON file, ``/run/trilo/telemetry/<name>.json``, holding the source's
complete current value as an object of sections, rewritten whole (a temp file, then a
rename). The robot's ``trilo-telemetry`` daemon (rpi-image) streams it to the fleet
controller, whose heartbeat receiver logs each section its own way (heartbeat README
"Sources and sections"):

- ``state``: the subsystem's complete current state (diffed into change entries);
- ``events``: a bounded ring of ``{seq, mono, ...}`` entries;
- ``metrics``: the latest values, or -- with ``samples`` -- a ring of samples, each stamped
  with ``mono`` so it is logged at its own time (any resolution you choose);
- ``counters``: lifetime counts.

``mono`` is ``time.monotonic()``: the fleet controller places a stamped entry on its own
clock, so nothing depends on the robot's wall clock. `TelemetrySource` keeps the sections
and writes them only when `publish` is called -- call it from a thread that may block on
the filesystem, never from one that must not.
"""

import json
import logging
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TELEMETRY_DIR = Path("/run/trilo/telemetry")
WARN_BYTES = 512 * 1024  # the daemon warns above this too: sources are state, keep them small


class TelemetrySource:
    """One telemetry source: set `state`, `metrics` and `counters`, add `event`s and
    `sample`s, then `publish`. Safe to use from several threads."""

    def __init__(
        self,
        name: str,
        directory: Path | str = TELEMETRY_DIR,
        events: int = 100,
        samples: int = 0,
    ) -> None:
        """
        :param name: the source's name (its file is ``<name>.json``); not starting with
            ``_`` (reserved for the stream) or ``.`` (temp files)
        :param directory: where sources live (default ``/run/trilo/telemetry``)
        :param events: how many events the ring keeps: size it for the outage it must
            survive at the source's peak rate
        :param samples: how many metrics samples the ring keeps; 0 publishes `metrics`
            as an object of the latest values instead
        """
        if not name or name[0] in "_." or "/" in name or name.endswith(".json"):
            raise ValueError(f"not a source name: {name!r}")
        self.name = name
        self.path = Path(directory) / f"{name}.json"
        self.state: dict[str, Any] = {}
        self.metrics: dict[str, Any] = {}
        self.counters: dict[str, Any] = {}
        self._events: deque[dict[str, Any]] = deque(maxlen=events)
        self._samples: deque[dict[str, Any]] | None = deque(maxlen=samples) if samples else None
        self._seq = 0
        self._lock = threading.Lock()
        self._big = False

    def event(self, **data: Any) -> None:
        """Add an entry to the events ring, stamped with its sequence number and ``mono``."""
        with self._lock:
            self._seq += 1
            self._events.append({"seq": self._seq, "mono": round(time.monotonic(), 3), **data})

    def sample(self, **values: Any) -> None:
        """Add a metrics sample, stamped with ``mono`` (the source was made with ``samples``)."""
        if self._samples is None:
            raise ValueError(f"{self.name}: made without a samples ring (samples=0)")
        with self._lock:
            self._samples.append({"mono": round(time.monotonic(), 3), **values})

    def document(self) -> dict[str, Any]:
        """The source as published: its non-empty sections."""
        with self._lock:
            doc: dict[str, Any] = {
                "state": self.state,
                "events": list(self._events),
                "metrics": list(self._samples) if self._samples is not None else self.metrics,
                "counters": self.counters,
            }
            return {k: v for k, v in doc.items() if v}

    def publish(self) -> None:
        """Write the source whole (a temp file beside it, then a rename). Raises OSError."""
        text = json.dumps(self.document(), separators=(",", ":"))
        if len(text) > WARN_BYTES and not self._big:
            logger.warning(
                "telemetry source %s is %d bytes: sources are state and should stay small",
                self.name,
                len(text),
            )
        self._big = len(text) > WARN_BYTES
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.name}.tmp")
        try:
            tmp.write_text(text)
            os.replace(tmp, self.path)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise
