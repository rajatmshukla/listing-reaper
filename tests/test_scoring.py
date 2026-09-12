from __future__ import annotations

import datetime
import unittest

from reaper.config import Config, ConfigError, ConfiguredRule, ScoringConfig, validate_scoring_config
from reaper.model import Listing
from reaper.scoring import Scorer


class TestScoring(unittest.TestCase):
    def _create_listing(
        self,
        id_val: str = "job-001",
        title: str = "Software Engineer",
        company: str = "Acme Corp",
        location: str = "Austin, TX",
        salary_max: int | None = 150000,
        salary_period: str = "year",
        posted_at: str = "2026-08-25",
        description: str = "A detailed description with enough text to be informative and deep.",
    ) -> Listing:
        return Listing.from_dict(
            {
                "id": id_val,
                "title": title,
                "company": company,
                "location": location,
                "salary_max": salary_max,
                "salary_period": salary_period,
                "posted_at": posted_at,
                "description": description,
            }
        )

    def test_title_match_signal(self) -> None:
        # Matches prefix (1.5) vs elsewhere (1.0)
        config = Config(
            scoring=ScoringConfig(signals={"title_match": 2.0}),
            rules=[
                ConfiguredRule(
                    rule_id="require_title_patterns",
                    params={"patterns": ["engineer", "software"]},
                )
            ],
        )
        scorer = Scorer(config)

        # "Software Engineer": "software" starts at 0 (1.5), "engineer" matches at 9 (1.0) -> raw = 2.5
        l1 = self._create_listing(title="Software Engineer")
        s1 = scorer.score_listing(l1)
        self.assertAlmostEqual(s1.components["title_match"], 5.0)

        # "Senior Infrastructure Engineer": "engineer" matches at 22 (1.0), "software" doesn't match -> raw = 1.0
        l2 = self._create_listing(title="Senior Infrastructure Engineer")
        s2 = scorer.score_listing(l2)
        self.assertAlmostEqual(s2.components["title_match"], 2.0)

    def test_salary_signal(self) -> None:
        config = Config(
            scoring=ScoringConfig(
                signals={"salary": 3.0},
                salary_ceiling=200000,
            ),
        )
        scorer = Scorer(config)

        # 100k / 200k = 0.5 -> 3.0 * 0.5 = 1.5
        l1 = self._create_listing(salary_max=100000, salary_period="year")
        s1 = scorer.score_listing(l1)
        self.assertAlmostEqual(s1.components["salary"], 1.5)

        # Hourly conversion: $50/hr * 2080 = $104,000 / 200,000 = 0.52 -> 3.0 * 0.52 = 1.56
        l2 = self._create_listing(salary_max=50, salary_period="hour")
        s2 = scorer.score_listing(l2)
        self.assertAlmostEqual(s2.components["salary"], 1.56)

        # Missing salary -> 0.0
        l3 = self._create_listing(salary_max=None)
        s3 = scorer.score_listing(l3)
        self.assertAlmostEqual(s3.components["salary"], 0.0)

        # Exceeds ceiling -> capped at 1.0 -> 3.0 * 1.0 = 3.0
        l4 = self._create_listing(salary_max=300000)
        s4 = scorer.score_listing(l4)
        self.assertAlmostEqual(s4.components["salary"], 3.0)

    def test_freshness_signal(self) -> None:
        config = Config(
            scoring=ScoringConfig(signals={"freshness": 2.0}),
            rules=[
                ConfiguredRule(
                    rule_id="freshness",
                    params={"max_age_days": 40, "reference_date": "2026-09-01"},
                )
            ],
        )
        scorer = Scorer(config)

        # Posted 2026-09-01 (0 days old) -> raw = 1.0 -> 2.0
        l1 = self._create_listing(posted_at="2026-09-01")
        self.assertAlmostEqual(scorer.score_listing(l1).components["freshness"], 2.0)

        # Posted 2026-08-12 (20 days old out of 40) -> raw = 0.5 -> 1.0
        l2 = self._create_listing(posted_at="2026-08-12")
        self.assertAlmostEqual(scorer.score_listing(l2).components["freshness"], 1.0)

        # Posted 2026-07-20 (43 days old, exceeds 40) -> raw = 0.0 -> 0.0
        l3 = self._create_listing(posted_at="2026-07-20")
        self.assertAlmostEqual(scorer.score_listing(l3).components["freshness"], 0.0)

        # Missing date -> 0.0
        l4 = self._create_listing(posted_at="")
        self.assertAlmostEqual(scorer.score_listing(l4).components["freshness"], 0.0)

    def test_description_depth_signal(self) -> None:
        config = Config(
            scoring=ScoringConfig(
                signals={"description_depth": 1.5},
                description_depth_cap=1000,
            ),
        )
        scorer = Scorer(config)

        # 500 chars -> 0.5 * 1.5 = 0.75
        l1 = self._create_listing(description="a" * 500)
        self.assertAlmostEqual(scorer.score_listing(l1).components["description_depth"], 0.75)

        # 1500 chars -> capped at 1.0 -> 1.5
        l2 = self._create_listing(description="b" * 1500)
        self.assertAlmostEqual(scorer.score_listing(l2).components["description_depth"], 1.5)

    def test_location_fit_signal(self) -> None:
        config = Config(
            scoring=ScoringConfig(signals={"location_fit": 2.0}),
            rules=[
                ConfiguredRule(
                    rule_id="location_policy",
                    params={
                        "allowed_locations": ["Austin, TX"],
                        "allow_remote": True,
                    },
                )
            ],
        )
        scorer = Scorer(config)

        # Exact allowed location -> 1.0 -> 2.0
        l_exact = self._create_listing(location="Austin, TX")
        self.assertAlmostEqual(scorer.score_listing(l_exact).components["location_fit"], 2.0)

        # Remote location -> 0.5 -> 1.0
        l_remote = self._create_listing(location="Remote (United States)")
        self.assertAlmostEqual(scorer.score_listing(l_remote).components["location_fit"], 1.0)

        # Neither -> 0.0 -> 0.0
        l_other = self._create_listing(location="Seattle, WA")
        self.assertAlmostEqual(scorer.score_listing(l_other).components["location_fit"], 0.0)

    def test_penalty_overlong_title_signal(self) -> None:
        config = Config(
            scoring=ScoringConfig(signals={"penalty_overlong_title": -2.0}),
        )
        scorer = Scorer(config)

        # Short title (under 50 chars) -> no penalty
        l_short = self._create_listing(title="Software Engineer")
        self.assertAlmostEqual(scorer.score_listing(l_short).components["penalty_overlong_title"], 0.0)

        # Overlong title (75 chars = 25 excess out of 50 -> raw 0.5 -> -2.0 * 0.5 = -1.0)
        title_75 = "A" * 75
        l_long = self._create_listing(title=title_75)
        self.assertAlmostEqual(scorer.score_listing(l_long).components["penalty_overlong_title"], -1.0)

    def test_zero_weights_deterministic_tie_breaking(self) -> None:
        # Setting all weights to 0.0 must still produce a deterministic order:
        # score desc (all 0.0), posted_at desc, id asc
        config = Config(
            scoring=ScoringConfig(
                signals={
                    "title_match": 0.0,
                    "salary": 0.0,
                    "freshness": 0.0,
                    "description_depth": 0.0,
                    "location_fit": 0.0,
                    "penalty_overlong_title": 0.0,
                }
            )
        )
        scorer = Scorer(config)

        l_old = self._create_listing(id_val="job-003", posted_at="2026-08-10")
        l_new_a = self._create_listing(id_val="job-001", posted_at="2026-08-20")
        l_new_b = self._create_listing(id_val="job-002", posted_at="2026-08-20")

        # Reverse input order
        ranked = scorer.rank([l_old, l_new_b, l_new_a])

        # Everyone has score 0.0
        for item in ranked:
            self.assertEqual(item.score, 0.0)

        # Newer dates come first (2026-08-20 before 2026-08-10)
        # Ties on date break by id ascending (job-001 before job-002)
        ranked_ids = [item.listing.id for item in ranked]
        self.assertEqual(ranked_ids, ["job-001", "job-002", "job-003"])

    def test_unknown_scoring_signal_validation(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            validate_scoring_config(
                {"signals": {"unknown_bogus_signal": 1.5}}
            )
        self.assertIn("unknown_bogus_signal", str(ctx.exception))
        self.assertIn("Valid signals", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
