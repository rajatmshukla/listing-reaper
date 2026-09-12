from __future__ import annotations

import json
from typing import Any

from reaper.model import Listing, ReapReport, RuleTrace, Verdict
from reaper.rules import REGISTRY
from reaper.simulator import SimulationResult


def render_json(data: Any) -> str:
    """Format any object or dict as pretty-printed JSON."""
    if hasattr(data, "to_dict"):
        data = data.to_dict()
    return json.dumps(data, indent=2)


def render_reap_summary(report: ReapReport) -> str:
    """Format a human-readable summary table of the reaping run."""
    lines: list[str] = [
        "Reap Summary",
        "=" * 64,
        f"{'Rule / Category':<36} {'Decision':<12} {'Count':>12}",
        "-" * 64,
    ]

    total_reaped = 0
    for rule_id, count in sorted(report.stats.items()):
        if rule_id == "kept":
            continue
        total_reaped += count
        lines.append(f"{rule_id:<36} {'reap':<12} {count:>12}")

    kept_count = report.stats.get("kept", len(report.kept))
    total_processed = total_reaped + kept_count

    lines.append("-" * 64)
    lines.append(f"{'Total Reaped':<36} {'reap':<12} {total_reaped:>12}")
    lines.append(f"{'Total Kept':<36} {'keep':<12} {kept_count:>12}")
    lines.append(f"{'Total Processed':<36} {'':<12} {total_processed:>12}")
    lines.append("=" * 64)
    lines.append("")

    if report.kept:
        lines.append(f"Kept Listings ({len(report.kept)}):")
        lines.append("-" * 64)
        for listing in report.kept:
            lines.append(f"[{listing.id}] {listing.title} @ {listing.company}")
            meta_parts: list[str] = []
            if listing.location:
                meta_parts.append(f"Location: {listing.location}")
            if listing.employment_type:
                meta_parts.append(f"Type: {listing.employment_type}")
            if listing.salary_min or listing.salary_max:
                period = f"/{listing.salary_period}" if listing.salary_period else ""
                if listing.salary_min and listing.salary_max:
                    meta_parts.append(f"Salary: ${listing.salary_min:,}-${listing.salary_max:,}{period}")
                elif listing.salary_max:
                    meta_parts.append(f"Salary: up to ${listing.salary_max:,}{period}")
                else:
                    meta_parts.append(f"Salary: from ${listing.salary_min:,}{period}")
            if meta_parts:
                lines.append(f"  {' | '.join(meta_parts)}")
            if listing.url:
                lines.append(f"  URL: {listing.url}")
            lines.append("")
    else:
        lines.append("No listings were kept.")
        lines.append("")

    if report.violations:
        lines.append("HONESTY VIOLATIONS DETECTED:")
        for v in report.violations:
            lines.append(f"  ! {v}")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_explain(
    listing: Listing,
    traces: list[RuleTrace],
    verdict: Verdict,
) -> str:
    """Render an in-depth, step-by-step rule trace explaining the verdict on a listing."""
    lines: list[str] = [
        f"Listing Explanation: {listing.id}",
        "=" * 64,
        f"Title:       {listing.title}",
        f"Company:     {listing.company}",
        f"Location:    {listing.location or '(not specified)'}",
        f"Type:        {listing.employment_type or '(not specified)'}",
    ]
    if listing.salary_min or listing.salary_max:
        period = f" ({listing.salary_period})" if listing.salary_period else ""
        if listing.salary_min and listing.salary_max:
            sal_str = f"${listing.salary_min:,} - ${listing.salary_max:,}{period}"
        elif listing.salary_max:
            sal_str = f"up to ${listing.salary_max:,}{period}"
        else:
            sal_str = f"from ${listing.salary_min:,}{period}"
        lines.append(f"Salary:      {sal_str}")
    if listing.posted_at:
        lines.append(f"Posted:      {listing.posted_at}")
    if listing.description:
        desc_preview = listing.description.replace("\n", " ")
        if len(desc_preview) > 80:
            desc_preview = desc_preview[:77] + "..."
        lines.append(f"Description: {desc_preview} ({len(listing.description)} chars)")

    lines.append("=" * 64)
    lines.append("Rule Evaluation Trace (Gate Model):")
    lines.append("-" * 64)

    for idx, trace in enumerate(traces, start=1):
        status = "REAP [GATE STOP]" if trace.decision == "reap" else "PASS"
        lines.append(f"  [{idx}] {trace.rule_id} -> {status}")
        lines.append(f"      {trace.reason}")

    lines.append("-" * 64)
    if verdict.decision == "reap":
        lines.append("FINAL VERDICT: REAPED")
        lines.append(f"Stopping Rule: {verdict.rule_id}")
        lines.append(f"Reason:        {verdict.reason}")
    else:
        lines.append("FINAL VERDICT: KEPT")
        lines.append(f"Reason:        {verdict.reason}")
    lines.append("=" * 64)

    return "\n".join(lines)


def render_simulation(result: SimulationResult) -> str:
    """Format a human-readable report of a simulation hunt."""
    lines: list[str] = [
        "Simulation Hunt",
        "=" * 64,
        f"Target Count: {result.target_count} | Rounds Run: {result.rounds_run}",
        "-" * 64,
        f"{'Round':<8} {'Fetched':<10} {'Kept':<8} {'Reaped':<10} {'Dupes':<8} {'Skipped':<10} {'Total Kept':<10}",
        "-" * 64,
    ]

    for rt in result.round_traces:
        lines.append(
            f"{rt.round_index:<8} {rt.fetched:<10} {rt.kept:<8} {rt.reaped:<10} "
            f"{rt.duplicates:<8} {rt.unevaluated:<10} {rt.running_kept_total:<10}"
        )

    lines.append("=" * 64)
    lines.append("Filter Statistics:")
    for k, v in sorted(result.stats.items()):
        lines.append(f"  - {k}: {v}")

    round_notes = [rt for rt in result.round_traces if rt.note]
    if round_notes:
        lines.append("")
        lines.append("Round Notes:")
        for rt in round_notes:
            lines.append(f"  - Round {rt.round_index}: {rt.note}")

    if result.errors:
        lines.append("")
        lines.append(f"Source Errors ({len(result.errors)} encountered):")
        for err in result.errors:
            lines.append(f"  - {err[0]}:{err[1]} -> {err[2]}")

    if result.violations:
        lines.append("")
        lines.append("Honesty Violations:")
        for v in result.violations:
            lines.append(f"  ! {v}")

    lines.append("-" * 64)
    lines.append(f"Outcome: {result.note}")
    lines.append("=" * 64)

    return "\n".join(lines)


def render_rules_catalog() -> str:
    """Format a human-readable catalog of all registered built-in rules."""
    lines: list[str] = [
        "Available Filter Rules",
        "=" * 64,
    ]

    for rule_id, spec in sorted(REGISTRY.items()):
        lines.append("")
        lines.append(f"Rule: {spec.id}")
        lines.append(f"  Summary: {spec.summary}")
        if spec.params:
            lines.append("  Parameters:")
            for p_name, p_spec in sorted(spec.params.items()):
                req = "required" if p_spec.required else f"default: {p_spec.default!r}"
                lines.append(f"    - {p_name} ({req}): {p_spec.description}")
        else:
            lines.append("  Parameters: (none)")

    lines.append("")
    lines.append("=" * 64)
    return "\n".join(lines)
