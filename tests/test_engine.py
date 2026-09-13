"""Tests for the filter engine gate model, short-circuit execution, and honesty checks."""
from __future__ import annotations

import unittest

from reaper.config import ConfiguredRule, Config
from reaper.engine import Reaper
from reaper.model import Listing, Verdict


class TestEngine(unittest.TestCase):
    def _create_listing(self, **kwargs) -> Listing:
        base = {
            "id": "job-eng-1",
            "title": "Software Engineer",
            "company": "Engine Test Org",
            "location": "Austin, TX",
            "employment_type": "full-time",
            "description": "A sufficiently long description for testing the reaper engine pipeline.",
            "posted_at": "2026-08-20",
            "salary_min": 100000,
            "salary_max": 120000,
            "salary_period": "year",
        }
        base.update(kwargs)
        return Listing.from_dict(base)

    def test_short_circuit_and_gate_model(self) -> None:
        # Configure three rules:
        # 1. require_description (min_chars: 40)
        # 2. exclude_seniority (terms: ['senior'])
        # 3. location_policy (allowed_locations: ['New York, NY'])
        config = Config(
            rules=[
                ConfiguredRule("require_description", {"min_chars": 40}),
                ConfiguredRule("exclude_seniority", {"terms": ["senior"]}),
                ConfiguredRule("location_policy", {"allowed_locations": ["New York, NY"], "allow_remote": False}),
            ]
        )
        reaper = Reaper(config)

        # Listing has short description. Rule 1 reaps it.
        # Rules 2 and 3 must NOT run!
        short_l = self._create_listing(
            id="l-short",
            description="Short.",
            title="Senior Developer",
            location="Seattle, WA",
        )
        verdict, traces = reaper.reap(short_l)
        self.assertEqual(verdict.decision, "reap")
        self.assertEqual(verdict.rule_id, "require_description")
        self.assertEqual(verdict.detail.get("rules_evaluated"), 1)
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].rule_id, "require_description")

        # Listing passes rule 1, but fails rule 2 (Senior).
        # Rule 3 must NOT run.
        senior_l = self._create_listing(
            id="l-senior",
            description="A valid long description that easily passes the 40-character gate threshold.",
            title="Senior Platform Engineer",
            location="Seattle, WA",
        )
        verdict2, traces2 = reaper.reap(senior_l)
        self.assertEqual(verdict2.decision, "reap")
        self.assertEqual(verdict2.rule_id, "exclude_seniority")
        self.assertEqual(verdict2.detail.get("rules_evaluated"), 2)
        self.assertEqual(len(traces2), 2)
        self.assertEqual(traces2[0].rule_id, "require_description")
        self.assertEqual(traces2[0].decision, "keep")
        self.assertEqual(traces2[1].rule_id, "exclude_seniority")
        self.assertEqual(traces2[1].decision, "reap")

    def test_kept_listing_complete_trace(self) -> None:
        config = Config(
            rules=[
                ConfiguredRule("require_description", {"min_chars": 40}),
                ConfiguredRule("exclude_seniority", {"terms": ["senior"]}),
            ]
        )
        reaper = Reaper(config)
        good_l = self._create_listing(
            id="l-good",
            title="Junior Software Engineer",
            description="A valid long description that easily passes the 40-character gate threshold.",
        )
        verdict, traces = reaper.reap(good_l)
        self.assertEqual(verdict.decision, "keep")
        self.assertEqual(verdict.detail.get("rules_evaluated"), 2)
        self.assertEqual(len(traces), 2)
        self.assertEqual(traces[0].decision, "keep")
        self.assertEqual(traces[1].decision, "keep")

    def test_honesty_checks(self) -> None:
        config = Config(
            rules=[
                ConfiguredRule("require_description", {"min_chars": 40}),
            ]
        )
        reaper = Reaper(config)

        listings = [
            self._create_listing(id="l-1", description="Short description."),
            self._create_listing(id="l-2", description="A valid long description that passes the rule cleanly."),
        ]

        report = reaper.reap_many(listings)
        self.assertEqual(len(report.violations), 0)
        self.assertEqual(len(report.kept), 1)
        self.assertEqual(len(report.reaped), 1)
        self.assertEqual(report.stats["require_description"], 1)
        self.assertEqual(report.stats["kept"], 1)

    def test_honesty_violation_detection(self) -> None:
        config = Config()
        reaper = Reaper(config)
        report = reaper.reap_many([])

        # Manually corrupt report to simulate dishonest state
        bad_l = self._create_listing(id="bad-1")
        report.reaped.append((bad_l, Verdict(rule_id="r1", decision="reap", reason="")))
        report.kept.append(bad_l)
        report.stats["r1"] = 0  # mismatch with len(reaped)

        # Re-run honesty verification logic
        violations = []
        for l, v in report.reaped:
            if not v.reason.strip():
                violations.append("empty reason")
        kept_ids = {l.id for l in report.kept}
        reaped_ids = {l.id for l, _ in report.reaped}
        if kept_ids & reaped_ids:
            violations.append("overlap")
        sum_reaped = sum(v for k, v in report.stats.items() if k != "kept")
        if sum_reaped != len(report.reaped):
            violations.append("sum mismatch")

        self.assertIn("empty reason", violations)
        self.assertIn("overlap", violations)
        self.assertIn("sum mismatch", violations)


if __name__ == "__main__":
    unittest.main()
