from __future__ import annotations

import unittest

from reaper.model import Listing
from reaper.rules import REGISTRY


class TestRules(unittest.TestCase):
    def _create_listing(self, **kwargs) -> Listing:
        base = {
            "id": "test-job-1",
            "title": "Software Engineer",
            "company": "Fictional Tech Labs",
            "location": "Austin, TX",
            "employment_type": "full-time",
            "description": "Standard engineering job description with sufficient length for testing.",
            "posted_at": "2026-08-15",
            "salary_min": 100000,
            "salary_max": 120000,
            "salary_period": "year",
        }
        base.update(kwargs)
        return Listing.from_dict(base)

    # 1. require_description
    def test_require_description(self) -> None:
        rule = REGISTRY["require_description"]
        params = {"min_chars": 40}

        # Keep
        good_l = self._create_listing(description="A" * 50)
        v_keep = rule.evaluate(good_l, params, None)
        self.assertEqual(v_keep.decision, "keep")
        self.assertEqual(
            v_keep.reason,
            "kept: description is 50 characters, meeting the 40-character minimum.",
        )

        # Reap
        short_l = self._create_listing(description="Too short.")
        v_reap = rule.evaluate(short_l, params, None)
        self.assertEqual(v_reap.decision, "reap")
        self.assertEqual(
            v_reap.reason,
            "reaped: description is 10 characters, under the 40-character minimum.",
        )

        # Edge case: empty description
        empty_l = self._create_listing(description="")
        v_empty = rule.evaluate(empty_l, params, None)
        self.assertEqual(v_empty.decision, "reap")
        self.assertEqual(
            v_empty.reason,
            "reaped: description is 0 characters, under the 40-character minimum.",
        )

    # 2. exclude_title_patterns
    def test_exclude_title_patterns(self) -> None:
        rule = REGISTRY["exclude_title_patterns"]
        params = {"patterns": [r"(?i)\bintern\b", r"(?i)\bdirector\b"]}

        # Keep
        good_l = self._create_listing(title="Software Engineer")
        v_keep = rule.evaluate(good_l, params, None)
        self.assertEqual(v_keep.decision, "keep")

        # Reap
        bad_l = self._create_listing(title="Software Engineer Intern")
        v_reap = rule.evaluate(bad_l, params, None)
        self.assertEqual(v_reap.decision, "reap")
        self.assertEqual(
            v_reap.reason,
            "reaped: title 'Software Engineer Intern' matches excluded pattern '(?i)\\bintern\\b'.",
        )

        # Edge case: case insensitivity variant
        cap_l = self._create_listing(title="MANAGING DIRECTOR OF PLATFORM")
        v_cap = rule.evaluate(cap_l, params, None)
        self.assertEqual(v_cap.decision, "reap")

    # 3. require_title_patterns
    def test_require_title_patterns(self) -> None:
        rule = REGISTRY["require_title_patterns"]
        params = {"patterns": [r"(?i)\bengineer\b", r"(?i)\bdeveloper\b"]}

        # Keep
        good_l = self._create_listing(title="Backend Developer")
        v_keep = rule.evaluate(good_l, params, None)
        self.assertEqual(v_keep.decision, "keep")
        self.assertEqual(
            v_keep.reason,
            "kept: title 'Backend Developer' matches required pattern '(?i)\\bdeveloper\\b'.",
        )

        # Reap
        bad_l = self._create_listing(title="Product Manager")
        v_reap = rule.evaluate(bad_l, params, None)
        self.assertEqual(v_reap.decision, "reap")
        self.assertIn("does not match any required pattern", v_reap.reason)

        # Edge case: multiple matches chooses first
        eng_dev = self._create_listing(title="Developer and Engineer")
        v_multi = rule.evaluate(eng_dev, params, None)
        self.assertEqual(v_multi.decision, "keep")

    # 4. exclude_seniority
    def test_exclude_seniority(self) -> None:
        rule = REGISTRY["exclude_seniority"]
        params = {"terms": ["senior", "sr.", "lead", "principal", "staff", "head of"]}

        # Keep
        good_l = self._create_listing(title="Software Engineer")
        v_keep = rule.evaluate(good_l, params, None)
        self.assertEqual(v_keep.decision, "keep")

        # Edge case: word boundary check ('Srl' and 'leaded' must not fire)
        srl_l = self._create_listing(title="Srl Technology Specialist")
        self.assertEqual(rule.evaluate(srl_l, params, None).decision, "keep")

        leaded_l = self._create_listing(title="Leaded Glass Software Analyst")
        self.assertEqual(rule.evaluate(leaded_l, params, None).decision, "keep")

        # Reap cases: 'Sr.' with literal dot, 'Lead', 'Senior'
        sr_l = self._create_listing(title="Sr. Software Developer")
        v_sr = rule.evaluate(sr_l, params, None)
        self.assertEqual(v_sr.decision, "reap")
        self.assertEqual(
            v_sr.reason,
            "reaped: title 'Sr. Software Developer' contains excluded seniority term 'sr.'.",
        )

        lead_l = self._create_listing(title="Team Lead of Infrastructure")
        v_lead = rule.evaluate(lead_l, params, None)
        self.assertEqual(v_lead.decision, "reap")
        self.assertEqual(
            v_lead.reason,
            "reaped: title 'Team Lead of Infrastructure' contains excluded seniority term 'lead'.",
        )

    # 5. employment_type
    def test_employment_type(self) -> None:
        rule = REGISTRY["employment_type"]
        params = {"allowed": ["full-time"], "reject_ambiguous": True}

        # Keep
        good_l = self._create_listing(
            employment_type="full-time",
            description="A regular full-time position with robust engineering duties.",
        )
        v_keep = rule.evaluate(good_l, params, None)
        self.assertEqual(v_keep.decision, "keep")

        # Reap: explicit wrong type
        contract_l = self._create_listing(employment_type="contract")
        v_reap = rule.evaluate(contract_l, params, None)
        self.assertEqual(v_reap.decision, "reap")
        self.assertEqual(
            v_reap.reason,
            "reaped: employment_type 'contract' is not in allowed types ['full-time'].",
        )

        # Reap: ambiguous description
        ambig_l = self._create_listing(
            employment_type="full-time",
            description="We are seeking an individual for a part-time contract arrangement initially.",
        )
        v_ambig = rule.evaluate(ambig_l, params, None)
        self.assertEqual(v_ambig.decision, "reap")
        self.assertIn("description names conflicting employment type", v_ambig.reason)

        # Edge case: empty employment type
        empty_emp = self._create_listing(employment_type="")
        v_empty = rule.evaluate(empty_emp, params, None)
        self.assertEqual(v_empty.decision, "reap")
        self.assertIn("employment_type is missing", v_empty.reason)

    # 6. location_policy
    def test_location_policy(self) -> None:
        rule = REGISTRY["location_policy"]
        params = {
            "allowed_locations": ["Austin, TX", "New York, NY"],
            "allow_remote": True,
            "remote_scopes": ["united states", "worldwide"],
            "reject_remote_other_scope": True,
        }

        # Keep allowed location
        l_loc = self._create_listing(location="Austin, TX")
        self.assertEqual(rule.evaluate(l_loc, params, None).decision, "keep")

        # Keep allowed remote scope
        l_rem = self._create_listing(location="Remote (United States)")
        v_rem = rule.evaluate(l_rem, params, None)
        self.assertEqual(v_rem.decision, "keep")
        self.assertEqual(
            v_rem.reason,
            "kept: remote location 'Remote (United States)' matches allowed remote scope 'united states'.",
        )

        # Reap location outside allowed
        l_seattle = self._create_listing(location="Seattle, WA")
        v_seattle = rule.evaluate(l_seattle, params, None)
        self.assertEqual(v_seattle.decision, "reap")
        self.assertIn("does not match any allowed location", v_seattle.reason)

        # Reap remote outside scope
        l_europe = self._create_listing(location="Remote (Europe)")
        v_europe = rule.evaluate(l_europe, params, None)
        self.assertEqual(v_europe.decision, "reap")
        self.assertEqual(
            v_europe.reason,
            "reaped: remote listing specifies scope 'Europe' outside allowed scopes ['united states', 'worldwide'].",
        )

        # Edge case: empty location
        l_empty = self._create_listing(location="")
        self.assertEqual(rule.evaluate(l_empty, params, None).decision, "reap")

    # 7. freshness
    def test_freshness(self) -> None:
        rule = REGISTRY["freshness"]
        params = {
            "max_age_days": 30,
            "reference_date": "2026-09-01",
            "missing_date_policy": "reap",
        }

        # Keep
        good_l = self._create_listing(posted_at="2026-08-20")  # 12 days old
        v_keep = rule.evaluate(good_l, params, None)
        self.assertEqual(v_keep.decision, "keep")
        self.assertEqual(
            v_keep.reason,
            "kept: listing is 12 days old (posted 2026-08-20), within the 30-day limit.",
        )

        # Reap: too old
        stale_l = self._create_listing(posted_at="2026-07-01")  # 62 days old
        v_reap = rule.evaluate(stale_l, params, None)
        self.assertEqual(v_reap.decision, "reap")
        self.assertEqual(
            v_reap.reason,
            "reaped: listing is 62 days old (posted 2026-07-01), exceeding the 30-day limit.",
        )

        # Edge case: missing date with reap policy
        missing_l = self._create_listing(posted_at="")
        v_missing = rule.evaluate(missing_l, params, None)
        self.assertEqual(v_missing.decision, "reap")
        self.assertEqual(
            v_missing.reason,
            "reaped: posted date is missing and missing_date_policy is 'reap'.",
        )

        # Edge case: missing date with keep policy
        params_keep = dict(params, missing_date_policy="keep")
        v_missing_keep = rule.evaluate(missing_l, params_keep, None)
        self.assertEqual(v_missing_keep.decision, "keep")

        # Edge case: unparseable date
        bad_dt_l = self._create_listing(posted_at="not-a-valid-date")
        v_bad_dt = rule.evaluate(bad_dt_l, params, None)
        self.assertEqual(v_bad_dt.decision, "reap")
        self.assertIn("was unparseable", v_bad_dt.reason)

    # 8. blocked_keywords
    def test_blocked_keywords(self) -> None:
        rule = REGISTRY["blocked_keywords"]
        params = {"patterns": [r"(?i)\bcommission only\b", r"(?i)\btraining fee\b"]}

        # Keep
        good_l = self._create_listing(
            description="Competitive salary with full benefits and paid leave."
        )
        self.assertEqual(rule.evaluate(good_l, params, None).decision, "keep")

        # Reap
        bad_l = self._create_listing(
            description="High earning potential with commission only compensation model."
        )
        v_reap = rule.evaluate(bad_l, params, None)
        self.assertEqual(v_reap.decision, "reap")
        self.assertIn("matches blocked keyword pattern", v_reap.reason)
        self.assertIn("commission only", v_reap.reason)

        # Edge case: keyword appears in title
        bad_title_l = self._create_listing(
            title="Sales Agent (Commission Only)",
            description="Join our team.",
        )
        self.assertEqual(rule.evaluate(bad_title_l, params, None).decision, "reap")

    # 9. min_salary
    def test_min_salary(self) -> None:
        rule = REGISTRY["min_salary"]
        params = {
            "min_annual": 100000,
            "missing_salary_policy": "keep",
            "hours_per_year": 2080,
            "months_per_year": 12,
        }

        # Keep annual
        good_annual = self._create_listing(
            salary_max=120000, salary_period="year"
        )
        v_keep = rule.evaluate(good_annual, params, None)
        self.assertEqual(v_keep.decision, "keep")
        self.assertEqual(
            v_keep.reason,
            "kept: annualised maximum salary of $120,000/year meets the $100,000 minimum.",
        )

        # Keep hourly conversion: $60/hr * 2080 = $124,800
        good_hourly = self._create_listing(salary_max=60, salary_period="hour")
        v_hourly = rule.evaluate(good_hourly, params, None)
        self.assertEqual(v_hourly.decision, "keep")
        self.assertIn("$60/hour annualised to $124,800/year", v_hourly.reason)

        # Reap annual
        low_annual = self._create_listing(
            salary_max=80000, salary_period="year"
        )
        v_low = rule.evaluate(low_annual, params, None)
        self.assertEqual(v_low.decision, "reap")
        self.assertEqual(
            v_low.reason,
            "reaped: annualised maximum salary of $80,000/year is below the $100,000 minimum.",
        )

        # Reap hourly: $30/hr * 2080 = $62,400
        low_hourly = self._create_listing(salary_max=30, salary_period="hour")
        v_low_h = rule.evaluate(low_hourly, params, None)
        self.assertEqual(v_low_h.decision, "reap")
        self.assertIn("$30/hour annualised to $62,400/year", v_low_h.reason)

        # Edge case: missing salary with keep policy
        no_sal = self._create_listing(salary_min=None, salary_max=None)
        v_no_sal = rule.evaluate(no_sal, params, None)
        self.assertEqual(v_no_sal.decision, "keep")

        # Edge case: missing salary with reap policy
        params_reap = dict(params, missing_salary_policy="reap")
        v_no_sal_reap = rule.evaluate(no_sal, params_reap, None)
        self.assertEqual(v_no_sal_reap.decision, "reap")

    # 10. custom_patterns
    def test_custom_patterns(self) -> None:
        rule = REGISTRY["custom_patterns"]
        params = {
            "reap_if_match": [r"(?i)\bunpaid\b"],
            "reap_unless_match": [r"(?i)\bpython\b"],
        }

        # Keep: contains python, does not contain unpaid
        good_l = self._create_listing(
            description="Developing backend services in Python and microservice architectures."
        )
        self.assertEqual(rule.evaluate(good_l, params, None).decision, "keep")

        # Reap: contains unpaid
        unpaid_l = self._create_listing(
            description="Unpaid volunteer position working with Python."
        )
        v_unpaid = rule.evaluate(unpaid_l, params, None)
        self.assertEqual(v_unpaid.decision, "reap")
        self.assertIn("matches reap_if_match pattern", v_unpaid.reason)

        # Reap: does not contain python
        no_python_l = self._create_listing(
            description="Developing services strictly in Go and Rust."
        )
        v_no_py = rule.evaluate(no_python_l, params, None)
        self.assertEqual(v_no_py.decision, "reap")
        self.assertIn("does not match any required reap_unless_match pattern", v_no_py.reason)


if __name__ == "__main__":
    unittest.main()
