# listing-reaper

`listing-reaper` is an offline job-listing filter engine featuring an explainable kill log and simulation harness. It applies an ordered pipeline of configurable rules to evaluate job listings, recording specific reasons for every reaped record while tracking complete rule evaluation traces for kept candidates.

This tool makes no network requests of any kind.

## What It Is / What It Is Not

- **What it is**: An offline deterministic filtering engine and batch simulation harness designed for evaluating and refining filter rules against local data you already possess.
- **What it is not**: It is not a scraper, does not connect to external job boards, makes no network calls, and ships with no production candidate data.

## Requirements

- Python 3.11+ (tested on Python 3.12).
- Standard library only.
- No third-party packages, external dependencies, or build installation steps required.

## Quickstart

Run the engine to filter the provided sample listings using the example configuration:

```bash
python3 -m reaper reap --fixtures fixtures/sample_listings.jsonl --config examples/rules.example.json
```

Observed output:

```text
Reap Summary
================================================================
Rule / Category                      Decision            Count
----------------------------------------------------------------
blocked_keywords                     reap                    2
employment_type                      reap                    2
exclude_seniority                    reap                    3
exclude_title_patterns               reap                    2
freshness                            reap                    3
location_policy                      reap                    2
min_salary                           reap                    1
require_description                  reap                    1
----------------------------------------------------------------
Total Reaped                         reap                   16
Total Kept                           keep                    8
Total Processed                                             24
================================================================

Kept Listings (8):
----------------------------------------------------------------
[job-001] Software Engineer @ Acme Widgets Ltd
  Location: Austin, TX | Type: full-time | Salary: $110,000-$130,000/year
  URL: https://example.com/jobs/1

[job-003] Backend Developer @ Nova Dynamics Corp
  Location: Remote (United States) | Type: full-time | Salary: $125,000-$145,000/year
  URL: https://example.com/jobs/3

[job-005] Systems Specialist @ Apex Orbital Systems
  Location: New York, NY | Type: full-time | Salary: $115,000-$135,000/year
  URL: https://example.com/jobs/5

[job-007] Site Reliability Analyst @ Zephyr Logistics Inc
  Location: Remote (Worldwide) | Type: full-time | Salary: $105,000-$120,000/year
  URL: https://example.com/jobs/7

[job-008] Infrastructure Engineer @ Pinnacle Dataworks
  Location: Chicago, IL | Type: full-time | Salary: $120,000-$140,000/year
  URL: https://example.com/jobs/8

[job-011] Data Platform Developer @ Aura Automation Inc
  Location: Remote (United States) | Type: full-time | Salary: $130,000-$150,000/year
  URL: https://example.com/jobs/11

[job-012] Full Stack Application Engineer and Cloud Infrastructure Specialist @ Cascade Computing Group
  Location: Austin, TX | Type: full-time | Salary: $100,000-$120,000/year
  URL: https://example.com/jobs/12

[job-024] Software Engineer @ Acme Widgets Ltd
  Location: Austin, TX | Type: full-time | Salary: $110,000-$130,000/year
  URL: https://example.com/jobs/24
```

Simulate an offline quota hunt stopping at 5 kept listings:

```bash
python3 -m reaper simulate --fixtures fixtures/sample_listings.jsonl --config examples/rules.example.json --target 5
```

Observed output:

```text
Simulation Hunt
================================================================
Target Count: 5 | Rounds Run: 1
----------------------------------------------------------------
Round    Fetched    Kept     Reaped     Dupes    Skipped    Total Kept
----------------------------------------------------------------
1        10         5        3          0        2          5         
================================================================
Filter Statistics:
  - already_seen: 0
  - blocked_keywords: 0
  - employment_type: 0
  - exclude_seniority: 1
  - exclude_title_patterns: 1
  - freshness: 0
  - kept: 5
  - location_policy: 0
  - min_salary: 0
  - require_description: 1

Round Notes:
  - Round 1: Evaluation stopped early because the target was reached.
----------------------------------------------------------------
Outcome: Target reached: 5 listings kept in 1 round(s).
================================================================
```

## Concepts

- **Listing**: A structured, normalized data record representing a vacancy (`id`, `title`, `company`, `location`, `employment_type`, `description`, `salary_min`, `salary_max`, `salary_period`, `posted_at`, `url`, `source`).
- **Rule**: A registered evaluation unit with defined schema parameters and an evaluation function returning a `Verdict`.
- **Verdict**: An explicit decision (`keep` or `reap`) accompanied by a complete, human-readable sentence stating the exact evidence found. Generic failure messages are prohibited.
- **Kill Log & Trace**: Every evaluated rule appends a `RuleTrace` recording the rule ID, decision, reason, and parameters used.
- **Gate Model (First Reap Wins)**: Configured rules act as an ordered sequence of gates. Evaluation short-circuits on the first rule that rejects a listing; subsequent rules are bypassed, and `rules_evaluated` is logged in verdict details. Kept listings pass through all gates and carry their full pass trace.

## CLI Reference

```text
python3 -m reaper reap     --fixtures FILE --config FILE [--json OUT] [--plugins MODULE[,MODULE...]]
python3 -m reaper explain  --fixtures FILE --config FILE --id LISTING_ID [--plugins MODULE[,MODULE...]]
python3 -m reaper simulate --fixtures FILE --config FILE [--target N] [--rounds N]
                           [--page-size N] [--pacing S] [--seen FILE] [--json OUT] [--seed N]
                           [--plugins MODULE[,MODULE...]]
python3 -m reaper rules    [--plugins MODULE[,MODULE...]]
python3 -m reaper validate --config FILE [--plugins MODULE[,MODULE...]]
```

### Commands and Flags

| Command | Flag | Description |
|---|---|---|
| `reap` | `--fixtures FILE` | Path to `.jsonl` or `.csv` input records (required). |
| `reap` | `--config FILE` | Path to JSON rules configuration (required). |
| `reap` | `--json OUT` | Output path for JSON report, or `-` for stdout. |
| `reap` | `--plugins MODULE[,MODULE...]` | Comma-separated list of plugin modules or `.py` files to load. |
| `explain` | `--fixtures FILE` | Path to fixture file (required). |
| `explain` | `--config FILE` | Path to configuration file (required). |
| `explain` | `--id ID` | Unique listing ID to trace and explain (required). |
| `explain` | `--plugins MODULE[,MODULE...]` | Comma-separated list of plugin modules or `.py` files to load. |
| `simulate` | `--fixtures FILE` | Path to fixture file (required). |
| `simulate` | `--config FILE` | Path to configuration file (required). |
| `simulate` | `--target N` | Target number of kept listings to acquire. |
| `simulate` | `--rounds N` | Maximum page rounds to execute. |
| `simulate` | `--page-size N` | Batch size per simulated fetch round. |
| `simulate` | `--pacing S` | Delay in seconds between round queries. |
| `simulate` | `--seen FILE` | File path to read/write persistent seen dedupe keys. |
| `simulate` | `--seed N` | Integer seed for reproducible pseudo-random shuffling. |
| `simulate` | `--json OUT` | Output path for simulation JSON report, or `-` for stdout. |
| `simulate` | `--plugins MODULE[,MODULE...]` | Comma-separated list of plugin modules or `.py` files to load. |
| `rules` | `--plugins MODULE[,MODULE...]` | Comma-separated list of plugin modules or `.py` files to load. |
| `validate` | `--config FILE` | Validate JSON configuration syntax and parameter schemas. |
| `validate` | `--plugins MODULE[,MODULE...]` | Comma-separated list of plugin modules or `.py` files to load. |

Plugins can also be specified via the `REAPER_PLUGINS` environment variable holding a comma-separated list of module paths or `.py` files, behaving identically to `--plugins`.

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `2` | Configuration, schema, plugin import, or command-line usage error. |
| `3` | Execution completed, but zero listings were kept after filtering. |
| `4` | Fixture file is unreadable or contains zero valid records. |

## Configuration

Configurations are stored in standard JSON files. Typos and unrecognized keys are rejected at load time.

### Schema Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `version` | `int` / `str` | `1` | Configuration schema version identifier. |
| `target_count` | `int` | `10` | Default target count of kept records in simulations. |
| `max_rounds` | `int` | `5` | Maximum round iterations for simulation runs. |
| `round_page_size` | `int` | `10` | Number of listings processed per round page. |
| `pacing_seconds` | `float` | `0.0` | Simulated sleep delay between fetching round pages. |
| `dedupe_by` | `list[str]` | `["title", "company"]` | Normalized listing attributes used for deduplication. |
| `rules` | `list[object]` | `[]` | Ordered list of rule configuration entries. |

See `examples/rules.example.json` for a complete, production-ready example.

## Rule Reference

All 10 built-in rules fail loudly during configuration validation if required parameters are missing or invalid:

| Rule ID | Reaping Condition | Parameters & Defaults |
|---|---|---|
| `require_description` | Reaps when description character count is less than `min_chars`. | `min_chars` (int, default: 40) |
| `exclude_title_patterns` | Reaps when title matches any regex in `patterns`. | `patterns` (list[str], required) |
| `require_title_patterns` | Reaps unless title matches at least one regex in `patterns`. | `patterns` (list[str], required) |
| `exclude_seniority` | Reaps when title contains any term in `terms` as a whole word. The literal dot in `sr.` is matched literally. | `terms` (list[str], default: `["senior", "sr.", "lead", "principal", "staff", "head of"]`) |
| `employment_type` | Reaps when `employment_type` is not in `allowed`. When `reject_ambiguous` is true, reaps if description mentions another employment type. | `allowed` (list[str], required), `reject_ambiguous` (bool, default: true) |
| `location_policy` | Reaps when non-remote location is not in `allowed_locations`. When `allow_remote` is true, requires matching a scope in `remote_scopes` if specified. | `allowed_locations` (list[str], default: `[]`), `allow_remote` (bool, default: false), `remote_scopes` (list[str], default: `[]`), `reject_remote_other_scope` (bool, default: true) |
| `freshness` | Reaps listings older than `max_age_days` relative to `reference_date` (defaults to today). Missing or unparseable dates follow `missing_date_policy`. | `max_age_days` (int, default: 30), `reference_date` (str, default: null), `missing_date_policy` (str: "keep" or "reap", default: "reap") |
| `blocked_keywords` | Reaps when any regex in `patterns` matches combined title and description text. | `patterns` (list[str], required) |
| `min_salary` | Reaps when annualised maximum salary is less than `min_annual`. Hourly (2,080 hrs) and monthly (12 mos) periods are converted. | `min_annual` (int, required), `missing_salary_policy` (str: "keep" or "reap", default: "keep"), `hours_per_year` (int, default: 2080), `months_per_year` (int, default: 12) |
| `custom_patterns` | Reaps if matching any regex in `reap_if_match`, or failing to match any in `reap_unless_match`. | `reap_if_match` (list[str], default: `[]`), `reap_unless_match` (list[str], default: `[]`) |

## Writing Your Own Rule

Custom rules are self-contained classes or functions registered into `REGISTRY`.

### 1. Write the Plugin Module

Create a Python module (e.g. `examples/custom_rule_example.py`):

```python
from reaper.model import Listing, Verdict
from reaper.rules import ParamSpec, RuleSpec, register_rule


def evaluate_max_title_length(listing: Listing, params: dict, ctx: dict | None = None) -> Verdict:
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
```

### 2. Configure the Rule

Add an entry for the custom rule to your configuration file (see `examples/rules.with_custom.example.json`):

```json
{
  "rule_id": "max_title_length",
  "max_chars": 60
}
```

### 3. Validate with `--plugins`

Validate your configuration with the custom rule loaded before validation:

```bash
python3 -m reaper validate --config examples/rules.with_custom.example.json --plugins examples/custom_rule_example.py
```

Observed validation output:

```text
Valid configuration: 'examples/rules.with_custom.example.json'
Active rules (9 configured):
  1. require_description
  2. max_title_length
  3. exclude_seniority
  4. exclude_title_patterns
  5. blocked_keywords
  6. employment_type
  7. location_policy
  8. freshness
  9. min_salary
```

### 4. Execute Filtering

Run the filter engine with your plugin active:

```bash
python3 -m reaper reap --fixtures fixtures/sample_listings.jsonl --config examples/rules.with_custom.example.json --plugins examples/custom_rule_example.py
```

Observed reap summary showing the custom rule reaped candidate records:

```text
Reap Summary
================================================================
Rule / Category                      Decision            Count
----------------------------------------------------------------
blocked_keywords                     reap                    2
employment_type                      reap                    2
exclude_seniority                    reap                    3
exclude_title_patterns               reap                    2
freshness                            reap                    3
location_policy                      reap                    2
max_title_length                     reap                    1
min_salary                           reap                    1
require_description                  reap                    1
----------------------------------------------------------------
Total Reaped                         reap                   17
Total Kept                           keep                    7
Total Processed                                             24
================================================================
```

### Using `REAPER_PLUGINS`

Alternatively, configure the `REAPER_PLUGINS` environment variable to load plugins without the CLI flag:

```bash
REAPER_PLUGINS=examples/custom_rule_example.py python3 -m reaper validate --config examples/rules.with_custom.example.json
```

## Output Formats

Using `--json OUT` (or `--json -` for stdout) produces a machine-readable JSON log containing `kept`, `reaped`, `traces`, `stats`, and `violations`. Below is an annotated excerpt:

```json
{
  "kept": [
    {
      "id": "job-001",
      "title": "Software Engineer",
      "company": "Acme Widgets Ltd",
      "location": "Austin, TX",
      "employment_type": "full-time",
      "salary_min": 110000,
      "salary_max": 130000,
      "salary_period": "year",
      "posted_at": "2026-08-15"
    }
  ],
  "reaped": [
    {
      "listing": {
        "id": "job-004",
        "title": "Developer",
        "company": "Cobalt Synthetics"
      },
      "verdict": {
        "rule_id": "require_description",
        "decision": "reap",
        "reason": "reaped: description is 10 characters, under the 40-character minimum.",
        "detail": {
          "actual_length": 10,
          "min_chars": 40,
          "rules_evaluated": 1
        }
      }
    }
  ],
  "traces": {
    "job-001": [
      {
        "rule_id": "require_description",
        "decision": "keep",
        "reason": "kept: description is 104 characters, meeting the 40-character minimum.",
        "params_used": {
          "min_chars": 40
        }
      }
    ]
  },
  "stats": {
    "require_description": 1,
    "exclude_seniority": 3,
    "kept": 8
  },
  "violations": []
}
```

## The Simulator's Model

The simulator orchestrates offline hunts over local fixtures:

- **Rounds and Paging**: Fetches up to `max_rounds` pages of size `round_page_size`.
- **Deduplication**: Keys are constructed from `dedupe_by` attributes (default: `title` and `company`) normalized by casefolding and collapsing internal whitespace. Listings previously encountered in the session or in `--seen` are counted in `stats["already_seen"]` and bypassed without error.
- **Pacing**: `pacing_seconds` introduces a deliberate pause between rounds to simulate polite pacing against rate limits.
- **Shortfall Honesty**: If the source exhausts all records before reaching `target_count`, the simulator reports the exact shortfall count and a plain note. It never invents records or claims a target was met when it was not.

## Testing

The comprehensive test suite uses Python's built-in `unittest` runner:

```bash
python3 -m unittest discover -s tests -t . -v
```

Observed test suite output:

```text
test_config_describe (tests.test_config.TestConfigValidation.test_config_describe) ... ok
test_missing_required_param (tests.test_config.TestConfigValidation.test_missing_required_param) ... ok
test_uncompilable_regex (tests.test_config.TestConfigValidation.test_uncompilable_regex) ... ok
test_unknown_param_on_known_rule_typo (tests.test_config.TestConfigValidation.test_unknown_param_on_known_rule_typo) ... ok
test_unknown_rule_id (tests.test_config.TestConfigValidation.test_unknown_rule_id) ... ok
test_unknown_top_level_key (tests.test_config.TestConfigValidation.test_unknown_top_level_key) ... ok
test_valid_config_loading (tests.test_config.TestConfigValidation.test_valid_config_loading) ... ok
test_honesty_checks (tests.test_engine.TestEngine.test_honesty_checks) ... ok
test_honesty_violation_detection (tests.test_engine.TestEngine.test_honesty_violation_detection) ... ok
test_kept_listing_complete_trace (tests.test_engine.TestEngine.test_kept_listing_complete_trace) ... ok
test_short_circuit_and_gate_model (tests.test_engine.TestEngine.test_short_circuit_and_gate_model) ... ok
test_load_plugin_from_file (tests.test_plugins.TestPlugins.test_load_plugin_from_file) ... ok
test_load_plugin_nonexistent_fails_and_rolls_back (tests.test_plugins.TestPlugins.test_load_plugin_nonexistent_fails_and_rolls_back) ... ok
test_resolve_plugin_entries (tests.test_plugins.TestPlugins.test_resolve_plugin_entries) ... ok
test_blocked_keywords (tests.test_rules.TestRules.test_blocked_keywords) ... ok
test_custom_patterns (tests.test_rules.TestRules.test_custom_patterns) ... ok
test_employment_type (tests.test_rules.TestRules.test_employment_type) ... ok
test_exclude_seniority (tests.test_rules.TestRules.test_exclude_seniority) ... ok
test_exclude_title_patterns (tests.test_rules.TestRules.test_exclude_title_patterns) ... ok
test_freshness (tests.test_rules.TestRules.test_freshness) ... ok
test_location_policy (tests.test_rules.TestRules.test_location_policy) ... ok
test_min_salary (tests.test_rules.TestRules.test_min_salary) ... ok
test_require_description (tests.test_rules.TestRules.test_require_description) ... ok
test_require_title_patterns (tests.test_rules.TestRules.test_require_title_patterns) ... ok
test_csv_fixture_loading (tests.test_simulator.TestSimulator.test_csv_fixture_loading) ... ok
test_dedupe_within_batch_and_seen_set (tests.test_simulator.TestSimulator.test_dedupe_within_batch_and_seen_set) ... ok
test_exhaustion_shortfall_honesty (tests.test_simulator.TestSimulator.test_exhaustion_shortfall_honesty) ... ok
test_fixture_error_collection (tests.test_simulator.TestSimulator.test_fixture_error_collection) ... ok
test_mid_page_stop_accounting (tests.test_simulator.TestSimulator.test_mid_page_stop_accounting) ... ok
test_quota_stop (tests.test_simulator.TestSimulator.test_quota_stop) ... ok
test_round_trace_invariant_pinned (tests.test_simulator.TestSimulator.test_round_trace_invariant_pinned) ... ok
test_seed_determinism (tests.test_simulator.TestSimulator.test_seed_determinism) ... ok

----------------------------------------------------------------------
Ran 32 tests in 0.054s

OK
```

## Design Notes

- **Why JSON configuration**: Standard, human-readable format that is easy to version-control, audit, and validate with informative schema error messages.
- **Why standard library only**: Eliminates dependency churn, supply-chain vulnerabilities, and installation friction. Runs out-of-the-box on standard Python 3.11+ distributions.
- **Why strictly offline**: Keeps filtering logic isolated, deterministic, and safe to execute against historical fixtures without side effects or latency.
- **Why first-reap-wins**: Short-circuit evaluation minimizes wasted compute cycles and provides clear causality by identifying the exact primary reason a listing was rejected.
- **Why reasons are full sentences**: Specific evidence-backed reasons (e.g. citing character counts, matching terms, or conversion calculations) make filter logs directly actionable and debuggable.

## License

No license has been chosen yet; all rights are reserved.
