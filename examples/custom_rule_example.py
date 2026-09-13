"""Example custom filter rule plugin demonstrating rule definition and registration.

Defines the max_title_length rule to reap listings with titles exceeding a configured
character limit, and registers it with the global reaper rule registry upon import.
"""
from reaper.model import Listing, Verdict
from reaper.rules import ParamSpec, RuleSpec, register_rule


def evaluate_max_title_length(listing: Listing, params: dict, ctx: dict | None = None) -> Verdict:
    """Evaluate whether listing title length exceeds the max_chars threshold."""
    max_chars = int(params.get("max_chars", 80))
    title_len = len(listing.title)
    if title_len > max_chars:
        return Verdict(
            rule_id="max_title_length",
            decision="reap",
            reason=f"reaped: title length is {title_len} characters, exceeding the {max_chars}-character maximum.",
            detail={"title_length": title_len, "max_chars": max_chars},
        )
    return Verdict(
        rule_id="max_title_length",
        decision="keep",
        reason=f"kept: title length is {title_len} characters, within the {max_chars}-character limit.",
        detail={"title_length": title_len, "max_chars": max_chars},
    )


# Register the custom rule specification
register_rule(
    RuleSpec(
        id="max_title_length",
        summary="Reaps listings whose title exceeds max_chars in length.",
        params={
            "max_chars": ParamSpec(
                description="Maximum permitted title character length.",
                default=80,
                required=False,
            )
        },
        evaluate=evaluate_max_title_length,
    )
)
