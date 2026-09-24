"""Test py_organelles.TelemetrySource."""

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from py_organelles import TelemetrySource


class TestTelemetrySource(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())

    def read(self, name: str) -> dict:
        return json.loads((self.dir / f"{name}.json").read_text())

    def test_publishes_the_non_empty_sections(self) -> None:
        src = TelemetrySource("board", self.dir)
        src.state["temp"] = {"ok": True}
        src.counters["resets"] = 3
        src.publish()
        self.assertEqual(
            self.read("board"), {"state": {"temp": {"ok": True}}, "counters": {"resets": 3}}
        )
        self.assertEqual([p.name for p in self.dir.iterdir()], ["board.json"])  # no temp file left

    def test_events_ring_is_bounded_and_stamped(self) -> None:
        src = TelemetrySource("estop", self.dir, events=2)
        before = time.monotonic()
        for kind in ("pressed", "released", "pressed"):
            src.event(kind=kind)
        src.publish()
        ring = self.read("estop")["events"]
        self.assertEqual([(e["seq"], e["kind"]) for e in ring], [(2, "released"), (3, "pressed")])
        self.assertTrue(all(before - 0.001 <= e["mono"] <= time.monotonic() for e in ring))

    def test_samples_ring_or_latest_values(self) -> None:
        src = TelemetrySource("motor", self.dir, samples=2)
        for i in range(3):
            src.sample(current=i)
        src.publish()
        self.assertEqual([s["current"] for s in self.read("motor")["metrics"]], [1, 2])
        latest = TelemetrySource("temps", self.dir)
        latest.metrics["cpu"] = 51.5
        latest.publish()
        self.assertEqual(self.read("temps")["metrics"], {"cpu": 51.5})
        with self.assertRaises(ValueError):
            latest.sample(cpu=1)

    def test_reserved_names_refused(self) -> None:
        for name in ("", "_", "_meta", ".hidden", "a/b", "x.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                TelemetrySource(name, self.dir)

    def test_concurrent_events(self) -> None:
        src = TelemetrySource("many", self.dir, events=1000)

        def burst() -> None:
            for i in range(100):
                src.event(n=i)

        threads = [threading.Thread(target=burst) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        seqs = [e["seq"] for e in src.document()["events"]]
        self.assertEqual(sorted(seqs), list(range(1, 501)))


if __name__ == "__main__":
    unittest.main()
