from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any, Callable

from reaper.model import Listing, Verdict


@dataclass(frozen=True)
class ParamSpec:
    """Specification of a rule parameter."""

    description: str
    default: Any = None
    required: bool = False

    def __getitem__(self, key: str) -> Any:
        if key == "description":
            return self.description
        if key == "default":
            return self.default
        if key == "required":
            return self.required
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass(frozen=True)
class RuleSpec:
    """Specification and evaluation function for a filter rule."""

    id: str
    summary: str
    params: dict[str, ParamSpec]
    evaluate: Callable[[Listing, dict[str, Any], dict[str, Any] | None], Verdict]


REGISTRY: dict[str, RuleSpec] = {}


def register_rule(spec: RuleSpec) -> None:
    """Register a rule specification in the global REGISTRY."""
    REGISTRY[spec.id] = spec


# ---------------------------------------------------------------------------
# Built-in Rule Implementations
# ---------------------------------------------------------------------------


def _eval_require_description(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    min_chars = int(params.get("min_chars", 40))
    char_count = len(listing.description.strip())
    if char_count < min_chars:
        return Verdict(
            rule_id="require_description",
            decision="reap",
            reason=f"reaped: description is {char_count} characters, under the {min_chars}-character minimum.",
            detail={"actual_length": char_count, "min_chars": min_chars},
        )
    return Verdict(
        rule_id="require_description",
        decision="keep",
        reason=f"kept: description is {char_count} characters, meeting the {min_chars}-character minimum.",
        detail={"actual_length": char_count, "min_chars": min_chars},
    )


def _eval_exclude_title_patterns(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    patterns = params.get("patterns") or []
    for pattern in patterns:
        if re.search(pattern, listing.title, re.IGNORECASE):
            return Verdict(
                rule_id="exclude_title_patterns",
                decision="reap",
                reason=f"reaped: title '{listing.title}' matches excluded pattern '{pattern}'.",
                detail={"matched_pattern": pattern, "title": listing.title},
            )
    return Verdict(
        rule_id="exclude_title_patterns",
        decision="keep",
        reason=f"kept: title '{listing.title}' does not match any excluded pattern.",
        detail={"title": listing.title},
    )


def _eval_require_title_patterns(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    patterns = params.get("patterns") or []
    for pattern in patterns:
        if re.search(pattern, listing.title, re.IGNORECASE):
            return Verdict(
                rule_id="require_title_patterns",
                decision="keep",
                reason=f"kept: title '{listing.title}' matches required pattern '{pattern}'.",
                detail={"matched_pattern": pattern, "title": listing.title},
            )
    return Verdict(
        rule_id="require_title_patterns",
        decision="reap",
        reason=f"reaped: title '{listing.title}' does not match any required pattern in {patterns}.",
        detail={"patterns": patterns, "title": listing.title},
    )


def _eval_exclude_seniority(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    terms = params.get("terms")
    if terms is None:
        terms = ["senior", "sr.", "lead", "principal", "staff", "head of"]

    for term in terms:
        # Word boundary matching: literal dot in 'sr.' is matched literally via re.escape.
        # (?<!\w) matches when not preceded by a word character.
        # (?!\w) matches when not followed by a word character.
        pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
        if re.search(pattern, listing.title, re.IGNORECASE):
            return Verdict(
                rule_id="exclude_seniority",
                decision="reap",
                reason=f"reaped: title '{listing.title}' contains excluded seniority term '{term}'.",
                detail={"matched_term": term, "title": listing.title},
            )

    return Verdict(
        rule_id="exclude_seniority",
        decision="keep",
        reason=f"kept: title '{listing.title}' does not contain any excluded seniority terms.",
        detail={"title": listing.title},
    )


def _eval_employment_type(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    allowed = params.get("allowed") or []
    reject_ambiguous = params.get("reject_ambiguous", True)

    raw_emp = listing.employment_type.strip()
    if not raw_emp:
        return Verdict(
            rule_id="employment_type",
            decision="reap",
            reason=f"reaped: employment_type is missing, expected one of {allowed}.",
            detail={"field": "employment_type", "allowed": allowed},
        )

    norm_allowed = [a.strip().lower() for a in allowed]
    if raw_emp.lower() not in norm_allowed:
        return Verdict(
            rule_id="employment_type",
            decision="reap",
            reason=f"reaped: employment_type '{listing.employment_type}' is not in allowed types {allowed}.",
            detail={"employment_type": listing.employment_type, "allowed": allowed},
        )

    if reject_ambiguous:
        candidates = [
            "full-time",
            "full time",
            "part-time",
            "part time",
            "contract",
            "contractor",
            "internship",
            "intern",
            "temporary",
            "temp",
            "freelance",
        ]
        desc_lower = listing.description.lower()
        for cand in candidates:
            cand_norm = cand.replace(" ", "-")
            in_allowed = any(
                cand == a or cand_norm == a.replace(" ", "-")
                for a in norm_allowed
            )
            if not in_allowed:
                cand_pattern = rf"(?<!\w){re.escape(cand)}(?!\w)"
                m = re.search(cand_pattern, desc_lower)
                if m:
                    found_text = listing.description[m.start() : m.end()]
                    return Verdict(
                        rule_id="employment_type",
                        decision="reap",
                        reason=(
                            f"reaped: description names conflicting employment type '{found_text}' "
                            f"outside allowed types {allowed}."
                        ),
                        detail={"conflicting_text": found_text, "allowed": allowed},
                    )

    return Verdict(
        rule_id="employment_type",
        decision="keep",
        reason=f"kept: employment_type '{listing.employment_type}' is allowed and no conflicting types were found in description.",
        detail={"employment_type": listing.employment_type},
    )


def _eval_location_policy(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    allowed_locations = params.get("allowed_locations") or []
    allow_remote = bool(params.get("allow_remote", False))
    remote_scopes = params.get("remote_scopes") or []
    reject_remote_other_scope = bool(params.get("reject_remote_other_scope", True))

    loc = listing.location.strip()
    if not loc:
        return Verdict(
            rule_id="location_policy",
            decision="reap",
            reason="reaped: location is empty and does not match allowed locations.",
            detail={"location": ""},
        )

    is_remote = "remote" in loc.lower()
    if is_remote:
        if not allow_remote:
            return Verdict(
                rule_id="location_policy",
                decision="reap",
                reason=f"reaped: remote work is not permitted for location '{loc}'.",
                detail={"location": loc, "allow_remote": False},
            )

        if not remote_scopes:
            return Verdict(
                rule_id="location_policy",
                decision="keep",
                reason=f"kept: remote location '{loc}' is permitted (no remote scopes restricted).",
                detail={"location": loc},
            )

        matched_scope = None
        for scope in remote_scopes:
            if scope.lower() in loc.lower():
                matched_scope = scope
                break

        if matched_scope:
            return Verdict(
                rule_id="location_policy",
                decision="keep",
                reason=f"kept: remote location '{loc}' matches allowed remote scope '{matched_scope}'.",
                detail={"location": loc, "matched_scope": matched_scope},
            )

        scope_found = re.sub(r"(?i)\bremote\b", "", loc).strip(" ()-–—,/:;")
        if not scope_found:
            scope_found = "unspecified"

        if reject_remote_other_scope:
            return Verdict(
                rule_id="location_policy",
                decision="reap",
                reason=f"reaped: remote listing specifies scope '{scope_found}' outside allowed scopes {remote_scopes}.",
                detail={
                    "location": loc,
                    "scope_found": scope_found,
                    "remote_scopes": remote_scopes,
                },
            )
        else:
            return Verdict(
                rule_id="location_policy",
                decision="reap",
                reason=f"reaped: remote listing '{loc}' does not match allowed remote scopes {remote_scopes}.",
                detail={"location": loc, "remote_scopes": remote_scopes},
            )
    else:
        for allowed_loc in allowed_locations:
            if allowed_loc.lower() in loc.lower():
                return Verdict(
                    rule_id="location_policy",
                    decision="keep",
                    reason=f"kept: location '{loc}' matches allowed location '{allowed_loc}'.",
                    detail={"location": loc, "matched_location": allowed_loc},
                )
        return Verdict(
            rule_id="location_policy",
            decision="reap",
            reason=f"reaped: location '{loc}' does not match any allowed location {allowed_locations}.",
            detail={"location": loc, "allowed_locations": allowed_locations},
        )


def _eval_freshness(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    max_age_days = int(params.get("max_age_days", 30))
    missing_date_policy = str(params.get("missing_date_policy", "reap")).lower()
    ref_date_param = params.get("reference_date")

    if ref_date_param:
        try:
            ref_date = datetime.date.fromisoformat(str(ref_date_param)[:10])
        except ValueError:
            ref_date = datetime.date.today()
    else:
        ref_date = datetime.date.today()

    raw_posted = listing.posted_at.strip()
    if not raw_posted:
        if missing_date_policy == "keep":
            return Verdict(
                rule_id="freshness",
                decision="keep",
                reason="kept: posted date is missing and missing_date_policy is 'keep'.",
                detail={"missing_date": True},
            )
        return Verdict(
            rule_id="freshness",
            decision="reap",
            reason="reaped: posted date is missing and missing_date_policy is 'reap'.",
            detail={"missing_date": True},
        )

    try:
        posted_date = datetime.date.fromisoformat(raw_posted[:10])
    except ValueError:
        if missing_date_policy == "keep":
            return Verdict(
                rule_id="freshness",
                decision="keep",
                reason=f"kept: posted date '{raw_posted}' was unparseable and missing_date_policy is 'keep'.",
                detail={"unparseable_date": raw_posted},
            )
        return Verdict(
            rule_id="freshness",
            decision="reap",
            reason=f"reaped: posted date '{raw_posted}' was unparseable and missing_date_policy is 'reap'.",
            detail={"unparseable_date": raw_posted},
        )

    age_days = (ref_date - posted_date).days
    if age_days > max_age_days:
        return Verdict(
            rule_id="freshness",
            decision="reap",
            reason=f"reaped: listing is {age_days} days old (posted {raw_posted}), exceeding the {max_age_days}-day limit.",
            detail={
                "age_days": age_days,
                "max_age_days": max_age_days,
                "posted_at": raw_posted,
                "reference_date": ref_date.isoformat(),
            },
        )
    return Verdict(
        rule_id="freshness",
        decision="keep",
        reason=f"kept: listing is {age_days} days old (posted {raw_posted}), within the {max_age_days}-day limit.",
        detail={
            "age_days": age_days,
            "max_age_days": max_age_days,
            "posted_at": raw_posted,
            "reference_date": ref_date.isoformat(),
        },
    )


def _eval_blocked_keywords(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    patterns = params.get("patterns") or []
    for pattern in patterns:
        m = re.search(pattern, listing.text, re.IGNORECASE)
        if m:
            snippet = listing.text[m.start() : m.end()]
            return Verdict(
                rule_id="blocked_keywords",
                decision="reap",
                reason=f"reaped: listing text matches blocked keyword pattern '{pattern}' (found '{snippet}').",
                detail={"pattern": pattern, "matched_text": snippet},
            )
    return Verdict(
        rule_id="blocked_keywords",
        decision="keep",
        reason="kept: listing does not match any blocked keyword patterns.",
        detail={},
    )


def _eval_min_salary(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    min_annual = int(params["min_annual"])
    missing_salary_policy = str(params.get("missing_salary_policy", "keep")).lower()
    hours_per_year = int(params.get("hours_per_year", 2080))
    months_per_year = int(params.get("months_per_year", 12))

    raw_val = (
        listing.salary_max
        if listing.salary_max is not None
        else listing.salary_min
    )
    if raw_val is None:
        if missing_salary_policy == "reap":
            return Verdict(
                rule_id="min_salary",
                decision="reap",
                reason="reaped: salary is missing and missing_salary_policy is 'reap'.",
                detail={"missing_salary": True},
            )
        return Verdict(
            rule_id="min_salary",
            decision="keep",
            reason="kept: salary is missing and missing_salary_policy is 'keep'.",
            detail={"missing_salary": True},
        )

    period = (listing.salary_period or "year").lower().strip()
    if period in ("hour", "hourly"):
        annualised = int(raw_val * hours_per_year)
        conv = f"${raw_val}/hour annualised to ${annualised:,}/year ({raw_val} * {hours_per_year} hrs)"
    elif period in ("month", "monthly"):
        annualised = int(raw_val * months_per_year)
        conv = f"${raw_val}/month annualised to ${annualised:,}/year ({raw_val} * {months_per_year} mos)"
    else:
        annualised = int(raw_val)
        conv = f"${annualised:,}/year"

    if annualised < min_annual:
        return Verdict(
            rule_id="min_salary",
            decision="reap",
            reason=f"reaped: annualised maximum salary of {conv} is below the ${min_annual:,} minimum.",
            detail={"annualised": annualised, "min_annual": min_annual, "conversion": conv},
        )
    return Verdict(
        rule_id="min_salary",
        decision="keep",
        reason=f"kept: annualised maximum salary of {conv} meets the ${min_annual:,} minimum.",
        detail={"annualised": annualised, "min_annual": min_annual, "conversion": conv},
    )


def _eval_custom_patterns(
    listing: Listing,
    params: dict[str, Any],
    ctx: dict[str, Any] | None = None,
) -> Verdict:
    reap_if_match = params.get("reap_if_match") or []
    reap_unless_match = params.get("reap_unless_match") or []

    for pattern in reap_if_match:
        m = re.search(pattern, listing.text, re.IGNORECASE)
        if m:
            snippet = listing.text[m.start() : m.end()]
            return Verdict(
                rule_id="custom_patterns",
                decision="reap",
                reason=f"reaped: listing text matches reap_if_match pattern '{pattern}' (found '{snippet}').",
                detail={"pattern": pattern, "matched_text": snippet},
            )

    if reap_unless_match:
        matched = False
        for pattern in reap_unless_match:
            if re.search(pattern, listing.text, re.IGNORECASE):
                matched = True
                break
        if not matched:
            return Verdict(
                rule_id="custom_patterns",
                decision="reap",
                reason=f"reaped: listing text does not match any required reap_unless_match pattern in {reap_unless_match}.",
                detail={"reap_unless_match": reap_unless_match},
            )

    return Verdict(
        rule_id="custom_patterns",
        decision="keep",
        reason="kept: listing satisfies custom patterns.",
        detail={},
    )


# ---------------------------------------------------------------------------
# Registry Initialization
# ---------------------------------------------------------------------------

register_rule(
    RuleSpec(
        id="require_description",
        summary="Reaps listings whose description is shorter than min_chars.",
        params={
            "min_chars": ParamSpec(
                description="Minimum required character length for the description.",
                default=40,
                required=False,
            ),
        },
        evaluate=_eval_require_description,
    )
)

register_rule(
    RuleSpec(
        id="exclude_title_patterns",
        summary="Reaps listings whose title matches any excluded regex pattern.",
        params={
            "patterns": ParamSpec(
                description="List of regular expressions to exclude (case-insensitive).",
                default=None,
                required=True,
            ),
        },
        evaluate=_eval_exclude_title_patterns,
    )
)

register_rule(
    RuleSpec(
        id="require_title_patterns",
        summary="Reaps listings unless the title matches at least one required regex pattern.",
        params={
            "patterns": ParamSpec(
                description="List of regular expressions, at least one of which must match the title.",
                default=None,
                required=True,
            ),
        },
        evaluate=_eval_require_title_patterns,
    )
)

register_rule(
    RuleSpec(
        id="exclude_seniority",
        summary="Reaps listings whose title contains excluded seniority terms as whole words.",
        params={
            "terms": ParamSpec(
                description="List of seniority terms to match as whole words (e.g. 'sr.', 'lead').",
                default=["senior", "sr.", "lead", "principal", "staff", "head of"],
                required=False,
            ),
        },
        evaluate=_eval_exclude_seniority,
    )
)

register_rule(
    RuleSpec(
        id="employment_type",
        summary="Keeps listings whose employment_type is in allowed, rejecting ambiguous descriptions.",
        params={
            "allowed": ParamSpec(
                description="List of allowed employment types (e.g. ['full-time']).",
                default=None,
                required=True,
            ),
            "reject_ambiguous": ParamSpec(
                description="When true, reaps listings whose description mentions a conflicting employment type.",
                default=True,
                required=False,
            ),
        },
        evaluate=_eval_employment_type,
    )
)

register_rule(
    RuleSpec(
        id="location_policy",
        summary="Enforces allowed location substrings and remote work scope policies.",
        params={
            "allowed_locations": ParamSpec(
                description="List of allowed location substrings (case-insensitive).",
                default=[],
                required=False,
            ),
            "allow_remote": ParamSpec(
                description="Whether remote listings are permitted.",
                default=False,
                required=False,
            ),
            "remote_scopes": ParamSpec(
                description="List of allowed remote scopes (e.g. ['united states', 'worldwide']).",
                default=[],
                required=False,
            ),
            "reject_remote_other_scope": ParamSpec(
                description="When true, reaps remote listings specifying scopes outside remote_scopes.",
                default=True,
                required=False,
            ),
        },
        evaluate=_eval_location_policy,
    )
)

register_rule(
    RuleSpec(
        id="freshness",
        summary="Reaps listings older than max_age_days relative to a reference date.",
        params={
            "max_age_days": ParamSpec(
                description="Maximum age of listings in days.",
                default=30,
                required=False,
            ),
            "reference_date": ParamSpec(
                description="ISO reference date (YYYY-MM-DD) for age calculation (defaults to today).",
                default=None,
                required=False,
            ),
            "missing_date_policy": ParamSpec(
                description="Policy when posted date is missing or unparseable ('keep' or 'reap').",
                default="reap",
                required=False,
            ),
        },
        evaluate=_eval_freshness,
    )
)

register_rule(
    RuleSpec(
        id="blocked_keywords",
        summary="Reaps listings matching blocked keyword patterns across title and description.",
        params={
            "patterns": ParamSpec(
                description="List of regular expression patterns to reject (scanned across listing text).",
                default=None,
                required=True,
            ),
        },
        evaluate=_eval_blocked_keywords,
    )
)

register_rule(
    RuleSpec(
        id="min_salary",
        summary="Reaps listings whose annualised maximum salary is below a specified threshold.",
        params={
            "min_annual": ParamSpec(
                description="Minimum annualised salary required.",
                default=None,
                required=True,
            ),
            "missing_salary_policy": ParamSpec(
                description="Policy when salary is missing ('keep' or 'reap').",
                default="keep",
                required=False,
            ),
            "hours_per_year": ParamSpec(
                description="Working hours per year for hourly conversion.",
                default=2080,
                required=False,
            ),
            "months_per_year": ParamSpec(
                description="Months per year for monthly conversion.",
                default=12,
                required=False,
            ),
        },
        evaluate=_eval_min_salary,
    )
)

register_rule(
    RuleSpec(
        id="custom_patterns",
        summary="Custom pattern matcher: reaps if matching reap_if_match or failing reap_unless_match.",
        params={
            "reap_if_match": ParamSpec(
                description="List of regex patterns; matches result in reaping.",
                default=[],
                required=False,
            ),
            "reap_unless_match": ParamSpec(
                description="List of regex patterns; failure to match at least one results in reaping.",
                default=[],
                required=False,
            ),
        },
        evaluate=_eval_custom_patterns,
    )
)
