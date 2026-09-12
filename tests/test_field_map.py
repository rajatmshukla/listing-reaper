from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reaper.config import Config, ConfigError, load_config, validate_field_map
from reaper.model import Listing, apply_field_map
from reaper.sources import FixtureSource
from reaper.workflow import run_workflow


class TestFieldMap(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_field_map_renaming_every_listable_field(self) -> None:
        raw_record = {
            "src_id": "job-999",
            "src_title": "Platform Infrastructure Engineer",
            "src_company": "Acme Widgets Ltd",
            "src_location": "Austin, TX",
            "src_type": "full-time",
            "src_desc": "Design scalable cloud infrastructure and event queues.",
            "src_url": "https://example.com/jobs/999",
            "src_posted": "2026-08-25",
            "src_sal_min": "120000",
            "src_sal_max": "140000",
            "src_sal_period": "year",
            "src_source": "custom_board",
        }
        field_map = {
            "src_id": "id",
            "src_title": "title",
            "src_company": "company",
            "src_location": "location",
            "src_type": "employment_type",
            "src_desc": "description",
            "src_url": "url",
            "src_posted": "posted_at",
            "src_sal_min": "salary_min",
            "src_sal_max": "salary_max",
            "src_sal_period": "salary_period",
            "src_source": "source",
        }

        listing = Listing.from_dict(raw_record, field_map=field_map)
        self.assertEqual(listing.id, "job-999")
        self.assertEqual(listing.title, "Platform Infrastructure Engineer")
        self.assertEqual(listing.company, "Acme Widgets Ltd")
        self.assertEqual(listing.location, "Austin, TX")
        self.assertEqual(listing.employment_type, "full-time")
        self.assertEqual(listing.description, "Design scalable cloud infrastructure and event queues.")
        self.assertEqual(listing.url, "https://example.com/jobs/999")
        self.assertEqual(listing.posted_at, "2026-08-25")
        self.assertEqual(listing.salary_min, 120000)
        self.assertEqual(listing.salary_max, 140000)
        self.assertEqual(listing.salary_period, "year")
        self.assertEqual(listing.source, "custom_board")

    def test_mapped_key_colliding_with_real_field_name(self) -> None:
        # 1. A mapped value wins over a same-named source field
        record1 = {
            "id": "job-101",
            "title": "Default Title",
            "job_title": "Winning Mapped Title",
            "company": "Acme Widgets Ltd",
        }
        listing1 = Listing.from_dict(record1, field_map={"job_title": "title"})
        self.assertEqual(listing1.title, "Winning Mapped Title")

        # 2. Source key shares a name with a Listing field but is mapped to another target
        record2 = {
            "id": "job-102",
            "title": "Senior Systems Engineer",
            "company": "Detailed description originally stored in company column",
            "employer": "Acme Digital Systems",
        }
        field_map2 = {
            "company": "description",
            "employer": "company",
        }
        listing2 = Listing.from_dict(record2, field_map=field_map2)
        self.assertEqual(listing2.company, "Acme Digital Systems")
        self.assertEqual(listing2.description, "Detailed description originally stored in company column")

    def test_invalid_target_field_erroring_with_exit_2(self) -> None:
        bad_config_path = self.tmp_path / "bad_config.json"
        bad_config_path.write_text(
            json.dumps({"field_map": {"x": "not_a_real_field"}}),
            encoding="utf-8",
        )

        with self.assertRaises(ConfigError) as ctx:
            validate_field_map({"x": "not_a_real_field"})
        self.assertIn("not_a_real_field", str(ctx.exception))

        # CLI test verifying exit code 2
        res = subprocess.run(
            [sys.executable, "-m", "reaper", "validate", "--config", str(bad_config_path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2)
        self.assertIn("not_a_real_field", res.stderr)

    def test_field_map_on_csv_and_jsonl(self) -> None:
        field_map = {
            "external_id": "id",
            "role": "title",
            "organization": "company",
            "work_place": "location",
        }

        # CSV test
        csv_file = self.tmp_path / "test_export.csv"
        csv_file.write_text(
            "external_id,role,organization,work_place\n"
            'csv-1,Software Developer,Acme Widgets Ltd,"Austin, TX"\n',
            encoding="utf-8",
        )
        csv_source = FixtureSource(csv_file, field_map=field_map)
        self.assertEqual(len(csv_source.listings), 1)
        self.assertEqual(csv_source.listings[0].id, "csv-1")
        self.assertEqual(csv_source.listings[0].title, "Software Developer")
        self.assertEqual(csv_source.listings[0].company, "Acme Widgets Ltd")
        self.assertEqual(csv_source.listings[0].location, "Austin, TX")

        # JSONL test
        jsonl_file = self.tmp_path / "test_export.jsonl"
        jsonl_file.write_text(
            json.dumps({
                "external_id": "jsonl-1",
                "role": "Cloud Architect",
                "organization": "Cascade Computing Group",
                "work_place": "New York, NY",
            }) + "\n",
            encoding="utf-8",
        )
        jsonl_source = FixtureSource(jsonl_file, field_map=field_map)
        self.assertEqual(len(jsonl_source.listings), 1)
        self.assertEqual(jsonl_source.listings[0].id, "jsonl-1")
        self.assertEqual(jsonl_source.listings[0].title, "Cloud Architect")
        self.assertEqual(jsonl_source.listings[0].company, "Cascade Computing Group")
        self.assertEqual(jsonl_source.listings[0].location, "New York, NY")

    def test_config_with_no_field_map_still_working(self) -> None:
        cfg_file = self.tmp_path / "clean_config.json"
        cfg_file.write_text(
            json.dumps({"version": 1, "target_count": 5, "rules": []}),
            encoding="utf-8",
        )
        config = load_config(cfg_file)
        self.assertEqual(config.field_map, {})

        # Loading standard fixture without field_map works cleanly
        src = FixtureSource("fixtures/sample_listings.jsonl", field_map=config.field_map)
        self.assertGreater(len(src.listings), 0)

    def test_end_to_end_aggregator_export_to_non_empty_shortlist(self) -> None:
        config = load_config("examples/workflow.aggregator.example.json")
        result = run_workflow(
            fixtures=["examples/exports/aggregator_export.csv"],
            config=config,
            state_path="fixtures/sample_seen.json",
            dry_run=True,
        )
        self.assertTrue(len(result.shortlist) > 0)
        recon = result.reconciliation
        self.assertEqual(recon["ingested"], 9)
        self.assertEqual(recon["duplicates"], 1)
        self.assertEqual(recon["reaped"], 4)
        self.assertEqual(recon["already_seen"], 0)
        self.assertEqual(recon["survived"], 4)
        self.assertEqual(recon["shortlisted"], 4)
        # Verify reconciliation balance invariant
        self.assertEqual(
            recon["ingested"] - recon["duplicates"] - recon["reaped"] - recon["already_seen"],
            recon["survived"],
        )
        self.assertEqual(len(result.shortlist), recon["shortlisted"])


if __name__ == "__main__":
    unittest.main()
