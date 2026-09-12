from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from reaper.config import Config
from reaper.engine import Reaper
from reaper.model import Listing, Verdict
from reaper.sources import Source


def make_dedupe_key(listing: Listing, fields: list[str]) -> str:
    """Construct a normalized deduplication key from specified listing fields.

    Normalizes by casefolding and collapsing internal whitespace.
    """
    parts: list[str] = []
    for field_name in fields:
        raw_val = getattr(listing, field_name, "")
        normalized = " ".join(str(raw_val or "").casefold().split())
        parts.append(normalized)
    return "::".join(parts)


@dataclass
class RoundTrace:
    """Metrics recorded for a single simulation round."""

    round_index: int
    fetched: int
    kept: int
    reaped: int
    duplicates: int
    unevaluated: int
    running_kept_total: int
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "fetched": self.fetched,
            "kept": self.kept,
            "reaped": self.reaped,
            "duplicates": self.duplicates,
            "unevaluated": self.unevaluated,
            "running_kept_total": self.running_kept_total,
            "note": self.note,
        }


@dataclass
class SimulationResult:
    """The complete result of an offline simulation hunt."""

    rounds_run: int
    target_count: int
    kept: list[Listing]
    reaped: list[tuple[Listing, Verdict]]
    stats: dict[str, int]
    shortfall: int
    note: str
    round_traces: list[RoundTrace] = field(default_factory=list)
    errors: list[tuple[str, int, str]] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    seen_keys: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rounds_run": self.rounds_run,
            "target_count": self.target_count,
            "kept_count": len(self.kept),
            "reaped_count": len(self.reaped),
            "shortfall": self.shortfall,
            "note": self.note,
            "stats": dict(self.stats),
            "round_traces": [r.to_dict() for r in self.round_traces],
            "kept": [listing.to_dict() for listing in self.kept],
            "reaped": [
                {
                    "listing": listing.to_dict(),
                    "verdict": verdict.to_dict(),
                }
                for listing, verdict in self.reaped
            ],
            "errors": [
                {"file": e[0], "line": e[1], "message": e[2]}
                for e in self.errors
            ],
            "violations": list(self.violations),
        }


def simulate(
    config: Config,
    source: Source,
    seen_keys: set[str] | None = None,
) -> SimulationResult:
    """Execute an offline simulation hunt against a listing source.

    Pages through listings in rounds, dedupes against seen_keys and within the run,
    stops when target_count is satisfied or source is exhausted, and honestly
    reports shortfalls.
    """
    seen = set(seen_keys) if seen_keys is not None else set()
    reaper = Reaper(config)

    kept: list[Listing] = []
    reaped: list[tuple[Listing, Verdict]] = []
    stats: dict[str, int] = {r.rule_id: 0 for r in config.rules}
    stats["kept"] = 0
    stats["already_seen"] = 0

    round_traces: list[RoundTrace] = []
    rounds_run = 0
    page_iter = source.pages(config.round_page_size)
    exhausted = False

    while rounds_run < config.max_rounds and len(kept) < config.target_count:
        try:
            page = next(page_iter)
        except StopIteration:
            exhausted = True
            break

        rounds_run += 1
        if config.pacing_seconds > 0.0 and rounds_run > 1:
            time.sleep(config.pacing_seconds)

        round_kept = 0
        round_reaped = 0
        round_dupes = 0

        for listing in page:
            dedupe_key = make_dedupe_key(listing, config.dedupe_by)
            if dedupe_key in seen:
                stats["already_seen"] += 1
                round_dupes += 1
                continue
            seen.add(dedupe_key)

            verdict, _ = reaper.reap(listing)
            if verdict.decision == "keep":
                kept.append(listing)
                stats["kept"] = stats.get("kept", 0) + 1
                round_kept += 1
            else:
                reaped.append((listing, verdict))
                stats[verdict.rule_id] = stats.get(verdict.rule_id, 0) + 1
                round_reaped += 1

            if len(kept) >= config.target_count:
                break

        round_unevaluated = len(page) - (round_kept + round_reaped + round_dupes)
        round_note = (
            "Evaluation stopped early because the target was reached."
            if round_unevaluated > 0
            else ""
        )

        trace = RoundTrace(
            round_index=rounds_run,
            fetched=len(page),
            kept=round_kept,
            reaped=round_reaped,
            duplicates=round_dupes,
            unevaluated=round_unevaluated,
            running_kept_total=len(kept),
            note=round_note,
        )

        round_traces.append(trace)

    shortfall = max(0, config.target_count - len(kept))
    if shortfall > 0:
        if exhausted or rounds_run < config.max_rounds:
            note = (
                f"Source exhausted after {rounds_run} round(s) with shortfall of {shortfall} "
                f"(kept {len(kept)} of target {config.target_count})."
            )
        else:
            note = (
                f"Max rounds ({config.max_rounds}) reached with shortfall of {shortfall} "
                f"(kept {len(kept)} of target {config.target_count})."
            )
    else:
        note = f"Target reached: {len(kept)} listings kept in {rounds_run} round(s)."

    source_errors = getattr(source, "errors", [])

    # Honesty invariant check
    violations: list[str] = []

    # Round trace accounting invariant: fetched == kept + reaped + duplicates + unevaluated
    for rt in round_traces:
        if rt.fetched != rt.kept + rt.reaped + rt.duplicates + rt.unevaluated:
            violations.append(
                f"Honesty violation: round {rt.round_index} fetched ({rt.fetched}) != "
                f"kept ({rt.kept}) + reaped ({rt.reaped}) + duplicates ({rt.duplicates}) + unevaluated ({rt.unevaluated})."
            )

    for listing, verdict in reaped:
        if not verdict.reason or not verdict.reason.strip():
            violations.append(
                f"Honesty violation: reaped listing '{listing.id}' has empty reap reason."
            )

    kept_ids = {l.id for l in kept}
    reaped_ids = {l.id for l, _ in reaped}
    overlap = kept_ids & reaped_ids
    if overlap:
        violations.append(
            f"Honesty violation: listings appear in both kept and reaped: {sorted(overlap)}"
        )

    return SimulationResult(
        rounds_run=rounds_run,
        target_count=config.target_count,
        kept=kept,
        reaped=reaped,
        stats=stats,
        shortfall=shortfall,
        note=note,
        round_traces=round_traces,
        errors=list(source_errors),
        violations=violations,
        seen_keys=seen,
    )
