from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from reaper.rules import REGISTRY, RuleSpec


class ConfigError(Exception):
    """Raised when configuration file fails schema or rule validation."""


ALLOWED_TOP_LEVEL_KEYS = {
    "version",
    "target_count",
    "max_rounds",
    "round_page_size",
    "pacing_seconds",
    "dedupe_by",
    "rules",
}


def render_regex_error(rule_id: str, pattern: str, err: re.error) -> str:
    """Format an actionable regex compilation error message."""
    return f"Rule '{rule_id}' has uncompilable regular expression pattern '{pattern}': {err}"


@dataclass
class ConfiguredRule:
    """A validated rule configuration entry."""

    rule_id: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "params": self.params,
        }


@dataclass
class Config:
    """The runtime configuration for Reaper and Simulator."""

    version: int | str = 1
    target_count: int = 10
    max_rounds: int = 5
    round_page_size: int = 10
    pacing_seconds: float = 0.0
    dedupe_by: list[str] = field(default_factory=lambda: ["title", "company"])
    rules: list[ConfiguredRule] = field(default_factory=list)

    def describe(self) -> str:
        """Return a plain-text description of the configuration and active rules."""
        lines = [
            f"Configuration (version {self.version})",
            f"  Target count:     {self.target_count}",
            f"  Max rounds:       {self.max_rounds}",
            f"  Round page size:  {self.round_page_size}",
            f"  Pacing seconds:   {self.pacing_seconds}",
            f"  Dedupe by:        {self.dedupe_by}",
            f"Active Rules ({len(self.rules)} configured):",
        ]
        for idx, rule in enumerate(self.rules, start=1):
            spec = REGISTRY.get(rule.rule_id)
            summary = f" — {spec.summary}" if spec else ""
            lines.append(f"  {idx}. {rule.rule_id}{summary}")
            for p_name, p_val in sorted(rule.params.items()):
                lines.append(f"       {p_name}: {p_val!r}")
        return "\n".join(lines)


def validate_rule_config(rule_dict: dict[str, Any]) -> ConfiguredRule:
    """Validate a single rule configuration entry against the rule registry."""
    if not isinstance(rule_dict, dict):
        raise ConfigError("Each rule entry in 'rules' must be a JSON object.")

    rule_id = rule_dict.get("rule_id") or rule_dict.get("id")
    if not rule_id or not isinstance(rule_id, str):
        raise ConfigError("Rule entry missing required 'rule_id'.")

    if rule_id not in REGISTRY:
        valid_ids = sorted(REGISTRY.keys())
        raise ConfigError(
            f"Unknown rule_id '{rule_id}'. Valid rule ids are: {valid_ids}"
        )

    spec: RuleSpec = REGISTRY[rule_id]

    # Extract parameters: either from 'params' sub-object or top-level keys in rule_dict
    if "params" in rule_dict:
        extra_keys = set(rule_dict.keys()) - {"rule_id", "id", "params"}
        if extra_keys:
            raise ConfigError(
                f"Unknown keys in rule '{rule_id}' entry: {sorted(extra_keys)}"
            )
        raw_params = rule_dict["params"]
        if not isinstance(raw_params, dict):
            raise ConfigError(
                f"The 'params' field for rule '{rule_id}' must be a JSON object."
            )
    else:
        raw_params = {k: v for k, v in rule_dict.items() if k not in ("rule_id", "id")}

    # Validate against unknown parameters (typo check)
    for param_name in raw_params:
        if param_name not in spec.params:
            valid_params = sorted(spec.params.keys())
            raise ConfigError(
                f"Unknown parameter '{param_name}' for rule '{rule_id}'. "
                f"Valid parameters: {valid_params}"
            )

    # Check required parameters
    resolved_params: dict[str, Any] = {}
    for param_name, param_spec in spec.params.items():
        if param_spec.required:
            if param_name not in raw_params or raw_params[param_name] is None:
                raise ConfigError(
                    f"Rule '{rule_id}' is missing required parameter '{param_name}'."
                )
            resolved_params[param_name] = raw_params[param_name]
        else:
            if param_name in raw_params:
                resolved_params[param_name] = raw_params[param_name]
            else:
                resolved_params[param_name] = param_spec.default

    # Rule-specific schema checks and regex compilations
    _validate_rule_semantics(rule_id, resolved_params)

    return ConfiguredRule(rule_id=rule_id, params=resolved_params)


def _validate_rule_semantics(rule_id: str, params: dict[str, Any]) -> None:
    """Validate specific semantic constraints such as regex compilation and enum values."""
    # Check regex lists
    regex_param_names = []
    if rule_id in ("exclude_title_patterns", "require_title_patterns", "blocked_keywords"):
        regex_param_names.append("patterns")
    elif rule_id == "custom_patterns":
        regex_param_names.extend(["reap_if_match", "reap_unless_match"])

    for p_name in regex_param_names:
        patterns = params.get(p_name)
        if patterns is not None:
            if not isinstance(patterns, list):
                raise ConfigError(
                    f"Parameter '{p_name}' in rule '{rule_id}' must be a list of strings."
                )
            for pat in patterns:
                if not isinstance(pat, str):
                    raise ConfigError(
                        f"Pattern '{pat}' in rule '{rule_id}' must be a string."
                    )
                try:
                    re.compile(pat)
                except re.error as err:
                    raise ConfigError(render_regex_error(rule_id, pat, err)) from err

    # Specific rule constraints
    if rule_id == "freshness":
        policy = params.get("missing_date_policy")
        if policy not in ("keep", "reap"):
            raise ConfigError(
                f"Rule 'freshness' parameter 'missing_date_policy' must be 'keep' or 'reap', got '{policy}'."
            )
        ref = params.get("reference_date")
        if ref:
            try:
                datetime.date.fromisoformat(str(ref)[:10])
            except ValueError:
                raise ConfigError(
                    f"Rule 'freshness' parameter 'reference_date' must be ISO YYYY-MM-DD, got '{ref}'."
                )

    elif rule_id == "min_salary":
        policy = params.get("missing_salary_policy")
        if policy not in ("keep", "reap"):
            raise ConfigError(
                f"Rule 'min_salary' parameter 'missing_salary_policy' must be 'keep' or 'reap', got '{policy}'."
            )
        min_annual = params.get("min_annual")
        if not isinstance(min_annual, (int, float)) or min_annual < 0:
            raise ConfigError(
                f"Rule 'min_salary' parameter 'min_annual' must be a positive number, got {min_annual!r}."
            )

    elif rule_id == "custom_patterns":
        if not params.get("reap_if_match") and not params.get("reap_unless_match"):
            raise ConfigError(
                "Rule 'custom_patterns' requires at least one pattern in 'reap_if_match' or 'reap_unless_match'."
            )

    elif rule_id == "location_policy":
        allowed_locs = params.get("allowed_locations") or []
        allow_remote = params.get("allow_remote", False)
        if not allowed_locs and not allow_remote:
            raise ConfigError(
                "Rule 'location_policy' must have either non-empty 'allowed_locations' or 'allow_remote: true'."
            )


def load_config(path: str | Path) -> Config:
    """Load and validate a Config from a JSON file.

    Raises:
        ConfigError: if JSON is invalid, keys are unknown, or rule params are invalid.
        FileNotFoundError: if the config file does not exist.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        raw_text = path_obj.read_text(encoding="utf-8")
    except Exception as err:
        raise ConfigError(f"Failed to read configuration file: {err}") from err

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as err:
        raise ConfigError(f"Invalid JSON in configuration file: {err}") from err

    if not isinstance(data, dict):
        raise ConfigError("Configuration root must be a JSON object.")

    # Check top-level keys
    for key in data:
        if key not in ALLOWED_TOP_LEVEL_KEYS:
            allowed = sorted(ALLOWED_TOP_LEVEL_KEYS)
            raise ConfigError(
                f"Unknown top-level configuration key: '{key}'. Allowed keys: {allowed}"
            )

    # Validate rules list
    raw_rules = data.get("rules", [])
    if not isinstance(raw_rules, list):
        raise ConfigError("Configuration key 'rules' must be a list of rule specifications.")

    validated_rules = [validate_rule_config(r) for r in raw_rules]

    target_count = int(data.get("target_count", 10))
    max_rounds = int(data.get("max_rounds", 5))
    round_page_size = int(data.get("round_page_size", 10))
    pacing_seconds = float(data.get("pacing_seconds", 0.0))
    dedupe_by = list(data.get("dedupe_by", ["title", "company"]))
    version = data.get("version", 1)

    return Config(
        version=version,
        target_count=target_count,
        max_rounds=max_rounds,
        round_page_size=round_page_size,
        pacing_seconds=pacing_seconds,
        dedupe_by=dedupe_by,
        rules=validated_rules,
    )
