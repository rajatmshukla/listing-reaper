from __future__ import annotations

from typing import Iterable

from reaper.config import Config
from reaper.model import Listing, ReapReport, RuleTrace, Verdict
from reaper.rules import REGISTRY


class Reaper:
    """The filter engine: applies ordered rules to listings using a short-circuit gate model.

    The first rule that rejects a listing reaps it, and evaluation stops immediately.
    Kept listings carry a complete trace of every rule they passed.
    """

    def __init__(self, config: Config) -> None:
        self.config = config

    def reap(self, listing: Listing) -> tuple[Verdict, list[RuleTrace]]:
        """Evaluate a single listing against the configured rule pipeline.

        Returns:
            A tuple of (final_verdict, list_of_rule_traces).
            The verdict carries 'rules_evaluated' in its detail dict.
        """
        traces: list[RuleTrace] = []
        rules_evaluated = 0

        for rule in self.config.rules:
            rules_evaluated += 1
            spec = REGISTRY.get(rule.rule_id)
            if spec is None:
                raise RuntimeError(f"Unregistered rule id encountered during execution: {rule.rule_id}")

            verdict = spec.evaluate(listing, rule.params, None)
            trace = RuleTrace(
                rule_id=rule.rule_id,
                decision=verdict.decision,
                reason=verdict.reason,
                params_used=rule.params,
            )
            traces.append(trace)

            if verdict.decision == "reap":
                detail = dict(verdict.detail)
                detail["rules_evaluated"] = rules_evaluated
                final_verdict = Verdict(
                    rule_id=verdict.rule_id,
                    decision="reap",
                    reason=verdict.reason,
                    detail=detail,
                )
                return final_verdict, traces

        # Passed all rule gates
        final_verdict = Verdict(
            rule_id="",
            decision="keep",
            reason=f"kept: passed all {rules_evaluated} configured rule gates.",
            detail={"rules_evaluated": rules_evaluated},
        )
        return final_verdict, traces

    def reap_many(self, listings: Iterable[Listing]) -> ReapReport:
        """Run the Reaper over multiple listings and return a full ReapReport.

        Verifies honesty invariants after evaluation:
        (a) every reaped listing has a non-empty reason.
        (b) no listing appears in both kept and reaped.
        (c) reaping is total (sum of rule reaps == len(reaped)).
        """
        kept: list[Listing] = []
        reaped: list[tuple[Listing, Verdict]] = []
        traces: dict[str, list[RuleTrace]] = {}
        stats: dict[str, int] = {r.rule_id: 0 for r in self.config.rules}
        stats["kept"] = 0

        for listing in listings:
            verdict, listing_traces = self.reap(listing)
            traces[listing.id] = listing_traces

            if verdict.decision == "keep":
                kept.append(listing)
                stats["kept"] = stats.get("kept", 0) + 1
            else:
                reaped.append((listing, verdict))
                stats[verdict.rule_id] = stats.get(verdict.rule_id, 0) + 1

        # Honesty check
        violations: list[str] = []

        # (a) Every reaped listing must have a non-empty reason
        for listing, verdict in reaped:
            if not verdict.reason or not verdict.reason.strip():
                violations.append(
                    f"Honesty violation: reaped listing '{listing.id}' has an empty reap reason."
                )

        # (b) No listing appears in both kept and reaped
        kept_ids = {l.id for l in kept}
        reaped_ids = {l.id for l, _ in reaped}
        overlap = kept_ids & reaped_ids
        if overlap:
            violations.append(
                f"Honesty violation: listings appear in both kept and reaped: {sorted(overlap)}"
            )

        # (c) Reaping is total: sum of per-rule reaps equals total reaped
        sum_rule_reaps = sum(v for k, v in stats.items() if k != "kept")
        if sum_rule_reaps != len(reaped):
            violations.append(
                f"Honesty violation: per-rule reap sum ({sum_rule_reaps}) does not match len(reaped) ({len(reaped)})."
            )

        return ReapReport(
            kept=kept,
            reaped=reaped,
            traces=traces,
            stats=stats,
            violations=violations,
        )
