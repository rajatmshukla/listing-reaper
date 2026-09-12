from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from reaper.config import Config
from reaper.engine import Reaper
from reaper.model import Listing, Verdict
from reaper.scoring import ScoredListing, Scorer
from reaper.simulator import make_dedupe_key
from reaper.sources import FixtureSource
from reaper.templates import (
    render_csv_report,
    render_json_report,
    render_markdown_report,
    render_workflow_summary,
)
from reaper.tracker import Tracker


@dataclass
class WorkflowResult:
    """The outcome of a complete workflow execution."""

    shortlist: list[ScoredListing]
    reconciliation: dict[str, Any]
    reap_stats: dict[str, int]
    summary: str
    written_files: list[Path] = field(default_factory=list)


def run_workflow(
    fixtures: list[str | Path],
    config: Config,
    state_path: str | Path = "state/seen.json",
    out_dir: str | Path | None = None,
    formats: list[str] | None = None,
    target_count: int | None = None,
    limit: int | None = None,
    since_days: int | None = None,
    no_track: bool = False,
    dry_run: bool = False,
    explain_scores: bool = False,
    overwrite: bool = False,
    today: str | None = None,
) -> WorkflowResult:
    """Execute the end-to-end job search workflow.

    Pipeline:
      1. Ingest fixture file(s)
      2. Deduplicate cross-fixture by dedupe_by fields
      3. Filter / reap via configured rules (+ since_days if requested)
      4. Drop already_seen listings recorded in state
      5. Rank survivors with Scorer
      6. Shortlist top target_count (capped by limit if set)
      7. Render and write reports (unless dry_run)
      8. Persist shortlisted records into state (unless no_track or dry_run)
      9. Reconcile all pipeline metrics
    """
    date_str = today or datetime.date.today().isoformat()

    # 1. Load fixtures
    all_listings: list[Listing] = []
    source_errors: list[tuple[str, int, str]] = []

    for f_path in fixtures:
        src = FixtureSource(f_path, field_map=config.field_map)
        if src.errors:
            source_errors.extend(src.errors)
        all_listings.extend(src.listings)

    if not all_listings:
        msg = "No valid listings found across provided fixture(s)."
        if source_errors:
            msg += f" Encountered {len(source_errors)} error(s), e.g. {source_errors[0][2]}"
        raise ValueError(msg)

    total_ingested = len(all_listings)

    # 2. Ingest-time deduplication
    unique_listings: list[Listing] = []
    seen_ingest_keys: set[str] = set()
    duplicates_dropped = 0

    for listing in all_listings:
        key = make_dedupe_key(listing, config.dedupe_by)
        if key in seen_ingest_keys:
            duplicates_dropped += 1
            continue
        seen_ingest_keys.add(key)
        unique_listings.append(listing)

    # 3. Filter by since_days if requested, then reap with engine
    reap_candidates: list[Listing] = []
    since_days_reaped: list[tuple[Listing, Verdict]] = []

    ref_date = datetime.date.today()
    for rule in config.rules:
        if rule.rule_id == "freshness" and rule.params.get("reference_date"):
            try:
                ref_date = datetime.date.fromisoformat(str(rule.params["reference_date"])[:10])
            except ValueError:
                pass

    if since_days is not None:
        for listing in unique_listings:
            if not listing.posted_at:
                verdict = Verdict(
                    rule_id="since_days",
                    decision="reap",
                    reason=f"reaped: missing posted_at with --since-days {since_days}.",
                )
                since_days_reaped.append((listing, verdict))
                continue
            try:
                posted_date = datetime.date.fromisoformat(str(listing.posted_at)[:10])
                age = (ref_date - posted_date).days
                if age > since_days:
                    verdict = Verdict(
                        rule_id="since_days",
                        decision="reap",
                        reason=f"reaped: listing is {age} days old (posted {listing.posted_at}), exceeding --since-days limit of {since_days}.",
                    )
                    since_days_reaped.append((listing, verdict))
                else:
                    reap_candidates.append(listing)
            except ValueError:
                verdict = Verdict(
                    rule_id="since_days",
                    decision="reap",
                    reason=f"reaped: unparseable posted_at '{listing.posted_at}' with --since-days {since_days}.",
                )
                since_days_reaped.append((listing, verdict))
    else:
        reap_candidates = unique_listings

    reaper = Reaper(config)
    report = reaper.reap_many(reap_candidates)

    reap_stats = dict(report.stats)
    if since_days_reaped:
        reap_stats["since_days"] = len(since_days_reaped)

    total_reaped = (len(unique_listings) - len(report.kept))

    # 4. Drop listings already present in state
    tracker = Tracker.load_or_empty(state_path)

    survivors: list[Listing] = []
    already_seen_count = 0

    for listing in report.kept:
        key = make_dedupe_key(listing, config.dedupe_by)
        if tracker.has(key):
            already_seen_count += 1
        else:
            survivors.append(listing)

    # 5. Rank survivors
    scorer = Scorer(config)
    ranked = scorer.rank(survivors)

    # 6. Shortlist selection
    effective_target = target_count if target_count is not None else config.target_count
    if limit is not None:
        shortlist_size = min(effective_target, limit)
    else:
        shortlist_size = effective_target

    shortlist = ranked[:shortlist_size]
    shortfall = max(0, effective_target - len(shortlist))

    # Reconciliation metrics
    reconciliation: dict[str, Any] = {
        "ingested": total_ingested,
        "duplicates": duplicates_dropped,
        "reaped": total_reaped,
        "already_seen": already_seen_count,
        "survived": len(survivors),
        "shortlisted": len(shortlist),
        "target": effective_target,
        "shortfall": shortfall,
    }

    # 7. Write reports
    written_files: list[Path] = []
    target_out_dir = Path(out_dir or config.output.directory or "out")
    active_formats = formats or config.output.formats or ["markdown"]

    if not dry_run:
        if len(shortlist) > 0 or overwrite:
            target_out_dir.mkdir(parents=True, exist_ok=True)
            if "markdown" in active_formats:
                md_path = target_out_dir / "shortlist.md"
                md_path.write_text(
                    render_markdown_report(shortlist, reconciliation, reap_stats, date_str),
                    encoding="utf-8",
                )
                written_files.append(md_path)

            if "csv" in active_formats:
                csv_path = target_out_dir / "shortlist.csv"
                csv_path.write_text(render_csv_report(shortlist), encoding="utf-8")
                written_files.append(csv_path)

            if "json" in active_formats:
                json_path = target_out_dir / "shortlist.json"
                json_path.write_text(
                    render_json_report(shortlist, reconciliation, reap_stats, date_str),
                    encoding="utf-8",
                )
                written_files.append(json_path)

    # 8. State update
    if not no_track and not dry_run:
        for item in shortlist:
            k = make_dedupe_key(item.listing, config.dedupe_by)
            tracker.record(k, status="shortlisted", date=date_str, listing_id=item.listing.id)
        tracker.save(state_path)

    # 9. Format summary
    summary = render_workflow_summary(
        shortlist,
        reconciliation,
        reap_stats,
        explain_scores=explain_scores,
    )

    return WorkflowResult(
        shortlist=shortlist,
        reconciliation=reconciliation,
        reap_stats=reap_stats,
        summary=summary,
        written_files=written_files,
    )
