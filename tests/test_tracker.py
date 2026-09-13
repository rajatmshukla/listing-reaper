"""Tests for persistent state tracking, record transitions, and atomic file storage."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reaper.tracker import StateError, Tracker


class TestTracker(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        self.state_file = self.tmp_path / "seen.json"

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_record_and_has(self) -> None:
        tracker = Tracker()
        key = "software engineer::acme corp"
        self.assertFalse(tracker.has(key))

        tracker.record(key=key, status="shortlisted", date="2026-08-25", listing_id="job-100")
        self.assertTrue(tracker.has(key))

        rec = tracker.get(key)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.status, "shortlisted")
        self.assertEqual(rec.listing_id, "job-100")
        self.assertEqual(rec.first_seen, "2026-08-25")
        self.assertEqual(rec.last_seen, "2026-08-25")

    def test_status_transitions(self) -> None:
        tracker = Tracker()
        key = "backend developer::nova inc"
        tracker.record(key=key, status="shortlisted", date="2026-08-20", listing_id="job-200")

        # Update to applied
        tracker.update_by_id("job-200", status="applied", date="2026-08-21")
        rec = tracker.get(key)
        self.assertEqual(rec.status, "applied")
        self.assertEqual(rec.last_seen, "2026-08-21")

        # Update to rejected
        tracker.update_by_id("job-200", status="rejected", date="2026-08-22")
        rec = tracker.get(key)
        self.assertEqual(rec.status, "rejected")

        # Update to skipped
        tracker.update_by_id("job-200", status="skipped", date="2026-08-23")
        rec = tracker.get(key)
        self.assertEqual(rec.status, "skipped")

    def test_track_unknown_id_raises_key_error(self) -> None:
        tracker = Tracker()
        with self.assertRaises(KeyError) as ctx:
            tracker.update_by_id("nonexistent-job-id", status="applied", date="2026-08-25")
        self.assertIn("nonexistent-job-id", str(ctx.exception))

    def test_atomic_state_save_and_load(self) -> None:
        tracker = Tracker()
        tracker.record("eng::co", status="shortlisted", date="2026-08-25", listing_id="job-01")
        tracker.save(self.state_file)

        # Ensure file exists and contains valid JSON
        self.assertTrue(self.state_file.exists())
        content = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(content["version"], 1)
        self.assertIn("eng::co", content["seen"])

        # Load back
        loaded = Tracker.load(self.state_file)
        self.assertTrue(loaded.has("eng::co"))
        self.assertEqual(loaded.get("eng::co").listing_id, "job-01")

    def test_corrupt_state_file_raises_cleanly(self) -> None:
        # 1. Invalid JSON
        self.state_file.write_text("NOT_JSON_DATA_!!!", encoding="utf-8")
        with self.assertRaises(StateError) as ctx:
            Tracker.load(self.state_file)
        self.assertIn("corrupt", str(ctx.exception))
        self.assertIn("invalid JSON", str(ctx.exception))

        # 2. Corrupt root structure
        self.state_file.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
        with self.assertRaises(StateError) as ctx:
            Tracker.load(self.state_file)
        self.assertIn("root must be a JSON object", str(ctx.exception))

        # 3. Corrupt invalid status
        bad_status = {
            "version": 1,
            "seen": {
                "k1": {"listing_id": "1", "status": "bogus_status"},
            },
        }
        self.state_file.write_text(json.dumps(bad_status), encoding="utf-8")
        with self.assertRaises(StateError) as ctx:
            Tracker.load(self.state_file)
        self.assertIn("invalid status 'bogus_status'", str(ctx.exception))

    def test_nonexistent_state_file(self) -> None:
        missing = self.tmp_path / "does_not_exist.json"
        with self.assertRaises(FileNotFoundError):
            Tracker.load(missing)

        # load_or_empty returns empty tracker on nonexistent file
        empty = Tracker.load_or_empty(missing)
        self.assertEqual(len(empty.records), 0)


if __name__ == "__main__":
    unittest.main()
