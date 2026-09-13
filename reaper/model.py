"""Data models and record structures for listing-reaper.

Owns the canonical Listing representation, Verdict, RuleTrace, ReapReport, and field mapping.
Does not own rule evaluation algorithms, persistent state storage, or output formatting.
Called by ingestion sources, the filter engine, scorer, and report generators.
Public exports: Listing, ListingError, ReapReport, RuleTrace, VALID_LISTING_FIELDS,
Verdict, and apply_field_map.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ListingError(Exception):
    """Raised when a listing record is malformed or missing required fields."""


VALID_LISTING_FIELDS = {
    "id",
    "title",
    "company",
    "location",
    "employment_type",
    "description",
    "url",
    "posted_at",
    "salary_min",
    "salary_max",
    "salary_period",
    "source",
}


def apply_field_map(
    record: dict[str, Any], field_map: dict[str, str] | None = None
) -> dict[str, Any]:
    """Map foreign record keys onto canonical Listing field names.

    Keys are source field names; values are target Listing field names.
    A mapped value wins over a same-named source field.
    Unmapped fields and keys not present in the record are preserved.
    """
    if not field_map:
        return dict(record)

    mapped = dict(record)
    for src_key, target_field in field_map.items():
        if src_key in record:
            mapped[target_field] = record[src_key]
    return mapped


def _coerce_int(val: Any) -> int | None:
    """Coerce numeric values or strings to int, returning None if not parseable."""
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        cleaned = val.strip().replace(",", "").replace("$", "")
        if not cleaned:
            return None
        try:
            return int(float(cleaned))
        except (ValueError, OverflowError):
            return None
    return None


@dataclass(frozen=True)
class Listing:
    """Represents a job listing.

    Required fields: id, title, company.
    All other fields are optional with sensible defaults.
    """

    id: str
    title: str
    company: str
    location: str = ""
    employment_type: str = ""
    description: str = ""
    url: str = ""
    posted_at: str = ""
    salary_min: int | None = None
    salary_max: int | None = None
    salary_period: str = ""
    source: str = ""
    raw: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)

    @property
    def text(self) -> str:
        """Combined title and description, lowercased for keyword scans."""
        parts = [self.title, self.description]
        return " ".join(p for p in parts if p).lower()

    @classmethod
    def from_dict(
        cls, d: dict[str, Any], field_map: dict[str, str] | None = None
    ) -> Listing:
        """Construct a Listing from a dictionary.

        Tolerates missing keys and coerces numeric strings.
        Rejects records with no id, no title, or no company by raising ListingError
        naming the offending field.
        """
        if not isinstance(d, dict):
            raise ListingError("Record is not a dictionary")

        if field_map:
            d = apply_field_map(d, field_map)

        raw_id = d.get("id")
        if raw_id is None or not str(raw_id).strip():
            raise ListingError("Missing required field: 'id'")

        raw_title = d.get("title")
        if raw_title is None or not str(raw_title).strip():
            raise ListingError("Missing required field: 'title'")

        raw_company = d.get("company")
        if raw_company is None or not str(raw_company).strip():
            raise ListingError("Missing required field: 'company'")

        return cls(
            id=str(raw_id).strip(),
            title=str(raw_title).strip(),
            company=str(raw_company).strip(),
            location=str(d.get("location") or "").strip(),
            employment_type=str(d.get("employment_type") or "").strip(),
            description=str(d.get("description") or "").strip(),
            url=str(d.get("url") or "").strip(),
            posted_at=str(d.get("posted_at") or "").strip(),
            salary_min=_coerce_int(d.get("salary_min")),
            salary_max=_coerce_int(d.get("salary_max")),
            salary_period=str(d.get("salary_period") or "").strip().lower(),
            source=str(d.get("source") or "").strip(),
            raw=dict(d),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert Listing to a JSON-serializable dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "employment_type": self.employment_type,
            "description": self.description,
            "url": self.url,
            "posted_at": self.posted_at,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_period": self.salary_period,
            "source": self.source,
        }


@dataclass(frozen=True)
class Verdict:
    """The decision made by a rule on a listing."""

    rule_id: str
    decision: str  # "keep" or "reap"
    reason: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert Verdict to a JSON-serializable dictionary."""
        return {
            "rule_id": self.rule_id,
            "decision": self.decision,
            "reason": self.reason,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class RuleTrace:
    """Trace of a single rule evaluated against a listing."""

    rule_id: str
    decision: str
    reason: str
    params_used: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert RuleTrace to a JSON-serializable dictionary."""
        return {
            "rule_id": self.rule_id,
            "decision": self.decision,
            "reason": self.reason,
            "params_used": self.params_used,
        }


@dataclass
class ReapReport:
    """The outcome of running the Reaper over a collection of listings."""

    kept: list[Listing] = field(default_factory=list)
    reaped: list[tuple[Listing, Verdict]] = field(default_factory=list)
    traces: dict[str, list[RuleTrace]] = field(default_factory=dict)
    stats: dict[str, int] = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert ReapReport to a JSON-serializable dictionary."""
        return {
            "kept": [listing.to_dict() for listing in self.kept],
            "reaped": [
                {
                    "listing": listing.to_dict(),
                    "verdict": verdict.to_dict(),
                }
                for listing, verdict in self.reaped
            ],
            "traces": {
                lid: [t.to_dict() for t in trace_list]
                for lid, trace_list in self.traces.items()
            },
            "stats": dict(self.stats),
            "violations": list(self.violations),
        }
