"""Tests for offline simulation rounds, deduplication, paging stops, and shortfall honesty."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Iterator

from reaper.config import Config, ConfiguredRule
from reaper.model import Listing
from reaper.simulator import make_dedupe_key, simulate
from reaper.sources import FixtureSource, Source


class DummySource:
    name: str = "dummy_source"

    def __init__(self, listings: list[Listing]) -> None:
        self.listings = listings
        self.errors: list[tuple[str, int, str]] = []

    def pages(self, page_size: int) -> Iterator[list[Listing]]:
        for i in range(0, len(self.listings), page_size):
            yield self.listings[i : i + page_size]


class TestSimulator(unittest.TestCase):
    def _create_listing(self, id_val: str, title: str, company: str) -> Listing:
        return Listing.from_dict(
            {
                "id": id_val,
                "title": title,
                "company": company,
                "description": "A long and thorough job description that easily passes all gate checks.",
            }
        )

    def test_quota_stop(self) -> None:
        # 10 good listings, target is 3
        listings = [
            self._create_listing(f"id-{i}", f"Title {i}", f"Company {i}")
            for i in range(10)
        ]
        source = DummySource(listings)
        config = Config(
            target_count=3,
            max_rounds=5,
            round_page_size=2,
            rules=[],  # Keep everything
        )

        result = simulate(config, source)
        self.assertEqual(len(result.kept), 3)
        self.assertEqual(result.shortfall, 0)
        self.assertIn("Target reached", result.note)
        # With page size 2, reaching 3 takes 2 rounds
        self.assertEqual(result.rounds_run, 2)

    def test_exhaustion_shortfall_honesty(self) -> None:
        # Only 3 listings available, target is 5
        listings = [
            self._create_listing(f"id-{i}", f"Title {i}", f"Company {i}")
            for i in range(3)
        ]
        source = DummySource(listings)
        config = Config(
            target_count=5,
            max_rounds=5,
            round_page_size=2,
            rules=[],
        )

        result = simulate(config, source)
        self.assertEqual(len(result.kept), 3)
        self.assertEqual(result.shortfall, 2)
        self.assertIn("Source exhausted", result.note)
        self.assertIn("shortfall of 2", result.note)
        self.assertIn("(kept 3 of target 5)", result.note)

    def test_dedupe_within_batch_and_seen_set(self) -> None:
        # Listing 1 and Listing 2 have identical title + company
        # Listing 0 is already in seen set
        listings = [
            self._create_listing("id-0", "Dev Ops", "Acme Org"),
            self._create_listing("id-1", "Software Engineer", "Widget Co"),
            self._create_listing("id-2", "Software Engineer", "Widget Co"),  # Dupe of id-1
            self._create_listing("id-3", "Data Engineer", "Widget Co"),
        ]
        source = DummySource(listings)
        config = Config(
            target_count=10,
            max_rounds=5,
            round_page_size=10,
            rules=[],
        )

        # Pre-populate seen set with id-0's normalized key
        seen_key_0 = make_dedupe_key(listings[0], config.dedupe_by)
        initial_seen = {seen_key_0}

        result = simulate(config, source, seen_keys=initial_seen)
        self.assertEqual(result.stats["already_seen"], 2)  # id-0 and id-2
        self.assertEqual(len(result.kept), 2)  # id-1 and id-3
        kept_ids = {l.id for l in result.kept}
        self.assertEqual(kept_ids, {"id-1", "id-3"})

    def test_seed_determinism(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_listings.jsonl"
            lines = [
                f'{{"id": "id-{i}", "title": "Job {i}", "company": "Co {i}"}}'
                for i in range(20)
            ]
            file_path.write_text("\n".join(lines), encoding="utf-8")

            source1 = FixtureSource(file_path, seed=42)
            source2 = FixtureSource(file_path, seed=42)
            source3 = FixtureSource(file_path, seed=99)

            ids1 = [l.id for l in source1.listings]
            ids2 = [l.id for l in source2.listings]
            ids3 = [l.id for l in source3.listings]

            # Same seed produces identical ordering
            self.assertEqual(ids1, ids2)
            # Different seed produces different ordering
            self.assertNotEqual(ids1, ids3)

    def test_csv_fixture_loading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "jobs.csv"
            csv_content = (
                "id,title,company,location,employment_type,salary_max,salary_period,description\n"
                "csv-1,Software Developer,Acme Corp,Austin TX,full-time,120000,year,A long description.\n"
                "csv-2,DevOps Engineer,Beta Corp,Remote,full-time,130000,year,Another long description.\n"
            )
            csv_path.write_text(csv_content, encoding="utf-8")
            source = FixtureSource(csv_path)
            self.assertEqual(len(source.listings), 2)
            self.assertEqual(source.listings[0].title, "Software Developer")
            self.assertEqual(source.listings[0].salary_max, 120000)

    def test_fixture_error_collection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "bad.jsonl"
            lines = [
                '{"id": "ok-1", "title": "Good Job", "company": "Good Co"}',
                '{"id": "bad-1", "title": "Corrupt JSON',
                '{"id": "bad-2", "company": "Missing Title"}',
            ]
            file_path.write_text("\n".join(lines), encoding="utf-8")
            source = FixtureSource(file_path)
            self.assertEqual(len(source.listings), 1)
            self.assertEqual(len(source.errors), 2)
            # Verify file, line number, and error message
            self.assertEqual(source.errors[0][1], 2)
            self.assertIn("JSON decode error", source.errors[0][2])
            self.assertEqual(source.errors[1][1], 3)
            self.assertIn("Missing required field: 'title'", source.errors[1][2])

    def test_round_trace_invariant_pinned(self) -> None:
        # Mix of keep, reap, and duplicates across multiple rounds
        listings = [
            self._create_listing("id-1", "Software Engineer", "Alpha Corp"),
            self._create_listing("id-2", "Senior Software Engineer", "Alpha Corp"),  # reap by seniority
            self._create_listing("id-3", "Software Engineer", "Alpha Corp"),  # duplicate of id-1
            self._create_listing("id-4", "Backend Developer", "Beta Corp"),
            self._create_listing("id-5", "Frontend Developer", "Gamma Corp"),
            self._create_listing("id-6", "DevOps Engineer", "Delta Corp"),
        ]
        source = DummySource(listings)
        config = Config(
            target_count=3,
            max_rounds=3,
            round_page_size=4,
            rules=[
                ConfiguredRule("exclude_seniority", {"terms": ["senior"]}),
            ],
        )

        result = simulate(config, source)
        self.assertGreater(len(result.round_traces), 0)
        self.assertEqual(len(result.violations), 0)

        for trace in result.round_traces:
            self.assertEqual(
                trace.fetched,
                trace.kept + trace.reaped + trace.duplicates + trace.unevaluated,
                f"Invariant failed for round {trace.round_index}",
            )

    def test_mid_page_stop_accounting(self) -> None:
        # 10 listings in a page, target is 2
        listings = [
            self._create_listing(f"id-{i}", f"Title {i}", f"Company {i}")
            for i in range(10)
        ]
        source = DummySource(listings)
        config = Config(
            target_count=2,
            max_rounds=1,
            round_page_size=10,
            rules=[],
        )

        result = simulate(config, source)
        self.assertEqual(result.rounds_run, 1)
        self.assertEqual(len(result.kept), 2)
        self.assertEqual(len(result.round_traces), 1)

        trace = result.round_traces[0]
        self.assertEqual(trace.fetched, 10)
        self.assertEqual(trace.kept, 2)
        self.assertEqual(trace.reaped, 0)
        self.assertEqual(trace.duplicates, 0)
        self.assertEqual(trace.unevaluated, 8)
        self.assertEqual(
            trace.fetched,
            trace.kept + trace.reaped + trace.duplicates + trace.unevaluated,
        )
        self.assertIn("Evaluation stopped early because the target was reached.", trace.note)
        self.assertEqual(result.violations, [])


if __name__ == "__main__":
    unittest.main()
