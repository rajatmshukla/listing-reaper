from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from typing import Any

from reaper.config import Config, KNOWN_SIGNALS
from reaper.model import Listing


@dataclass(frozen=True)
class ScoredListing:
    """A listing evaluated by the Scorer with its total score and component breakdown."""

    listing: Listing
    score: float
    components: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing": self.listing.to_dict(),
            "score": self.score,
            "components": dict(self.components),
        }


@dataclass(frozen=True)
class _RankingKey:
    """Deterministic tie-breaking key: score desc, posted_at desc, id asc."""

    score: float
    posted_at: str
    listing_id: str

    def __lt__(self, other: _RankingKey) -> bool:
        if self.score != other.score:
            return self.score > other.score
        if self.posted_at != other.posted_at:
            return self.posted_at > other.posted_at
        return self.listing_id < other.listing_id


class Scorer:
    """Calculates weighted, explainable ranking scores for job listings.

    Signals:
      - title_match: Matches against require_title_patterns rule (starts title: 1.5, elsewhere: 1.0)
      - salary: Normalised annualised salary against salary_ceiling [0.0 - 1.0]
      - freshness: Linear freshness score between max_age_days and zero [0.0 - 1.0]
      - description_depth: Description character length normalised to description_depth_cap [0.0 - 1.0]
      - location_fit: Exact allowed_locations match (1.0) outscores remote (0.5), outscores neither (0.0)
      - penalty_overlong_title: Negative penalty proportional to title length exceeding 50 chars [0.0 - 1.0]

    Ties break deterministically by score (desc), posted_at (desc), and listing id (asc).
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.signals = dict(config.scoring.signals)
        self.salary_ceiling = float(config.scoring.salary_ceiling)
        self.description_depth_cap = float(config.scoring.description_depth_cap)

        # Extract rule parameters for signal evaluation
        self.title_patterns: list[str] = []
        self.allowed_locations: list[str] = []
        self.allow_remote: bool = False
        self.max_age_days: int = 30
        self.ref_date: datetime.date = datetime.date.today()

        for rule in config.rules:
            if rule.rule_id == "require_title_patterns":
                self.title_patterns = list(rule.params.get("patterns") or [])
            elif rule.rule_id == "location_policy":
                self.allowed_locations = list(rule.params.get("allowed_locations") or [])
                self.allow_remote = bool(rule.params.get("allow_remote", False))
            elif rule.rule_id == "freshness":
                self.max_age_days = int(rule.params.get("max_age_days", 30))
                ref = rule.params.get("reference_date")
                if ref:
                    try:
                        self.ref_date = datetime.date.fromisoformat(str(ref)[:10])
                    except ValueError:
                        self.ref_date = datetime.date.today()

    def _eval_title_match(self, listing: Listing) -> float:
        """Count matches of require_title_patterns, awarding 1.5 for prefix matches and 1.0 elsewhere."""
        if not self.title_patterns:
            return 0.0

        match_sum = 0.0
        for pattern in self.title_patterns:
            m = re.search(pattern, listing.title, re.IGNORECASE)
            if m:
                if m.start() == 0:
                    match_sum += 1.5
                else:
                    match_sum += 1.0
        return match_sum

    def _eval_salary(self, listing: Listing) -> float:
        """Normalise annualised salary against salary_ceiling, capped at 1.0."""
        val = listing.salary_max if listing.salary_max is not None else listing.salary_min
        if val is None or val <= 0 or self.salary_ceiling <= 0:
            return 0.0

        period = (listing.salary_period or "year").lower().strip()
        if period in ("hour", "hourly"):
            annual = val * 2080
        elif period in ("month", "monthly"):
            annual = val * 12
        else:
            annual = val

        return min(1.0, max(0.0, float(annual) / self.salary_ceiling))

    def _eval_freshness(self, listing: Listing) -> float:
        """Linear freshness score between max_age_days and zero."""
        if not listing.posted_at or self.max_age_days <= 0:
            return 0.0

        try:
            posted_date = datetime.date.fromisoformat(str(listing.posted_at)[:10])
        except ValueError:
            return 0.0

        age_days = (self.ref_date - posted_date).days
        if age_days <= 0:
            return 1.0
        if age_days >= self.max_age_days:
            return 0.0
        return (self.max_age_days - age_days) / float(self.max_age_days)

    def _eval_description_depth(self, listing: Listing) -> float:
        """Measure description detail up to description_depth_cap."""
        if self.description_depth_cap <= 0:
            return 0.0
        length = len(listing.description.strip())
        return min(1.0, max(0.0, float(length) / self.description_depth_cap))

    def _eval_location_fit(self, listing: Listing) -> float:
        """Score location: exact allowed_locations (1.0) > remote (0.5) > neither (0.0)."""
        loc = listing.location.strip().lower()
        is_remote = "remote" in loc or listing.employment_type.lower() == "remote"

        if self.allowed_locations:
            for allowed in self.allowed_locations:
                al_lower = allowed.strip().lower()
                if loc == al_lower:
                    return 1.0
                if al_lower in loc and not is_remote:
                    return 1.0

        if is_remote:
            return 0.5

        if self.allowed_locations:
            for allowed in self.allowed_locations:
                if allowed.strip().lower() in loc:
                    return 1.0

        return 0.0

    def _eval_penalty_overlong_title(self, listing: Listing) -> float:
        """Calculate penalty factor for titles longer than 50 characters [0.0 - 1.0]."""
        title_len = len(listing.title.strip())
        if title_len <= 50:
            return 0.0
        excess = title_len - 50
        return min(1.0, float(excess) / 50.0)

    def score_listing(self, listing: Listing) -> ScoredListing:
        """Compute the weighted score and component breakdown for a listing."""
        components: dict[str, float] = {}

        signal_evaluators = {
            "title_match": self._eval_title_match,
            "salary": self._eval_salary,
            "freshness": self._eval_freshness,
            "description_depth": self._eval_description_depth,
            "location_fit": self._eval_location_fit,
            "penalty_overlong_title": self._eval_penalty_overlong_title,
        }

        for sig_name, evaluator in signal_evaluators.items():
            weight = self.signals.get(sig_name, 0.0)
            if weight != 0.0:
                raw_val = evaluator(listing)
                components[sig_name] = round(weight * raw_val, 4)
            else:
                components[sig_name] = 0.0

        total_score = round(sum(components.values()), 4)
        return ScoredListing(
            listing=listing,
            score=total_score,
            components=components,
        )

    def rank(self, listings: list[Listing]) -> list[ScoredListing]:
        """Score and sort listings in deterministic order."""
        scored = [self.score_listing(l) for l in listings]
        return sorted(
            scored,
            key=lambda s: _RankingKey(s.score, s.listing.posted_at, s.listing.id),
        )
