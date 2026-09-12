from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reaper.config import Config, ConfiguredRule, OutputConfig, ScoringConfig
from reaper.tracker import Tracker
from reaper.workflow import run_workflow


class TestWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

        # Write sample fixture 1
        self.fixture1 = self.tmp_path / "fixture1.jsonl"
        rows1 = [
            {"id": "j1", "title": "Software Engineer", "company": "Alpha Corp", "location": "Austin, TX", "employment_type": "full-time", "salary_max": 120000, "posted_at": "2026-08-25", "description": "Good description that is long enough."},
            {"id": "j2", "title": "Backend Developer", "company": "Beta Labs", "location": "Remote", "employment_type": "full-time", "salary_max": 130000, "posted_at": "2026-08-26", "description": "Good description that is long enough."},
            {"id": "j3", "title": "Senior Staff Architect", "company": "Gamma Corp", "location": "Austin, TX", "employment_type": "full-time", "salary_max": 200000, "posted_at": "2026-08-20", "description": "Good description that is long enough."}, # Reaped by seniority
            {"id": "j4", "title": "Systems Specialist", "company": "Delta Inc", "location": "Austin, TX", "employment_type": "full-time", "salary_max": 110000, "posted_at": "2026-08-15", "description": "Good description that is long enough."},
        ]
        self.fixture1.write_text("\n".join(json.dumps(r) for r in rows1) + "\n", encoding="utf-8")

        # Write sample fixture 2 (with cross-file duplicate of j1)
        self.fixture2 = self.tmp_path / "fixture2.jsonl"
        rows2 = [
            {"id": "j1-dupe", "title": "Software Engineer", "company": "Alpha Corp", "location": "Austin, TX", "employment_type": "full-time", "salary_max": 120000, "posted_at": "2026-08-25", "description": "Good description that is long enough."}, # Duplicate of j1
            {"id": "j5", "title": "Infrastructure Engineer", "company": "Epsilon Works", "location": "Austin, TX", "employment_type": "full-time", "salary_max": 115000, "posted_at": "2026-08-22", "description": "Good description that is long enough."},
            {"id": "j6", "title": "Developer", "company": "Zeta Systems", "location": "Austin, TX", "employment_type": "full-time", "salary_max": 105000, "posted_at": "2026-07-01", "description": "Good description that is long enough."}, # Old date for since-days test
        ]
        self.fixture2.write_text("\n".join(json.dumps(r) for r in rows2) + "\n", encoding="utf-8")

        self.state_file = self.tmp_path / "seen.json"
        self.out_dir = self.tmp_path / "out"

        self.config = Config(
            target_count=3,
            scoring=ScoringConfig(
                signals={"title_match": 1.0, "salary": 1.0, "freshness": 1.0},
                salary_ceiling=200000,
            ),
            output=OutputConfig(formats=["markdown", "csv", "json"], directory=str(self.out_dir)),
            rules=[
                ConfiguredRule(
                    rule_id="exclude_seniority",
                    params={"terms": ["senior", "staff"]},
                ),
            ],
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_reconciliation_counts_and_multi_fixture_dedupe(self) -> None:
        # Pre-seed state with j2 ("backend developer::beta labs")
        tracker = Tracker()
        tracker.record("backend developer::beta labs", status="shortlisted", date="2026-08-20", listing_id="j2")
        tracker.save(self.state_file)

        result = run_workflow(
            fixtures=[self.fixture1, self.fixture2],
            config=self.config,
            state_path=self.state_file,
            out_dir=self.out_dir,
            today="2026-08-30",
        )

        recon = result.reconciliation
        # Fixture 1: 4 listings. Fixture 2: 3 listings. Total ingested = 7
        self.assertEqual(recon["ingested"], 7)
        # Duplicate j1-dupe has key 'software engineer::alpha corp' already in fixture 1
        self.assertEqual(recon["duplicates"], 1)
        # 6 unique listings evaluated. j3 has seniority 'Senior Staff' -> reaped by exclude_seniority
        self.assertEqual(recon["reaped"], 1)
        # 5 survivors of reaping: j1, j2, j4, j5, j6.
        # j2 is in state file -> already_seen = 1
        self.assertEqual(recon["already_seen"], 1)
        # 4 eligible survivors remain: j1, j4, j5, j6
        self.assertEqual(recon["survived"], 4)
        # Target count is 3 -> shortlisted = 3
        self.assertEqual(recon["shortlisted"], 3)
        self.assertEqual(recon["target"], 3)
        self.assertEqual(recon["shortfall"], 0)

        # Invariant check: ingested = duplicates + reaped + already_seen + survived
        self.assertEqual(
            recon["ingested"],
            recon["duplicates"] + recon["reaped"] + recon["already_seen"] + recon["survived"],
        )

        # Verify output files were written
        self.assertTrue((self.out_dir / "shortlist.md").exists())
        self.assertTrue((self.out_dir / "shortlist.csv").exists())
        self.assertTrue((self.out_dir / "shortlist.json").exists())

        # Verify state file recorded shortlisted items
        updated_tracker = Tracker.load(self.state_file)
        self.assertTrue(updated_tracker.has("software engineer::alpha corp"))

    def test_dry_run_writes_nothing(self) -> None:
        result = run_workflow(
            fixtures=[self.fixture1],
            config=self.config,
            state_path=self.state_file,
            out_dir=self.out_dir,
            dry_run=True,
            today="2026-08-30",
        )

        # Reports directory not created, state file not created
        self.assertFalse(self.out_dir.exists())
        self.assertFalse(self.state_file.exists())
        self.assertEqual(len(result.written_files), 0)
        self.assertEqual(len(result.shortlist), 3)

    def test_limit_caps_shortlist_independently(self) -> None:
        # Target is 3, but limit is 1
        result = run_workflow(
            fixtures=[self.fixture1],
            config=self.config,
            state_path=self.state_file,
            out_dir=self.out_dir,
            limit=1,
            dry_run=True,
            today="2026-08-30",
        )
        self.assertEqual(len(result.shortlist), 1)
        self.assertEqual(result.reconciliation["shortlisted"], 1)
        # Target remains 3, so shortfall is 3 - 1 = 2
        self.assertEqual(result.reconciliation["target"], 3)
        self.assertEqual(result.reconciliation["shortfall"], 2)

    def test_since_days_filter(self) -> None:
        # Run with --since-days 10 relative to 2026-08-30:
        # j4 (posted 2026-08-15, 15 days old) will exceed 10 days
        result = run_workflow(
            fixtures=[self.fixture1],
            config=self.config,
            state_path=self.state_file,
            out_dir=self.out_dir,
            since_days=10,
            dry_run=True,
            today="2026-08-30",
        )
        self.assertIn("since_days", result.reap_stats)
        # j4 reaped by since_days
        shortlisted_ids = [item.listing.id for item in result.shortlist]
        self.assertNotIn("j4", shortlisted_ids)

    def test_no_track_does_not_modify_state(self) -> None:
        run_workflow(
            fixtures=[self.fixture1],
            config=self.config,
            state_path=self.state_file,
            out_dir=self.out_dir,
            no_track=True,
            today="2026-08-30",
        )
        # Output files written, but state file not created
        self.assertTrue((self.out_dir / "shortlist.md").exists())
        self.assertFalse(self.state_file.exists())


if __name__ == "__main__":
    unittest.main()
