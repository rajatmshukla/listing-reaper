# listing-reaper

`listing-reaper` is a complete, offline job search workflow that filters, deduplicates, ranks, and tracks job vacancies on your local machine. It requires no credentials, makes zero network calls, and stores all state locally in transparent, human-readable files.

## The Daily Loop

A real job search runs as an ongoing loop:

1. **Gather**: Collect listings from data you already have (a board export, a CSV download, or a local scrape). See [docs/SOURCES.md](docs/SOURCES.md) for platform export formats and field mapping.
2. **Reap**: Filter out ineligible postings with an explainable audit trail that logs a concrete written reason for every eliminated vacancy.
3. **Dedupe**: Eliminate duplicate postings and drop anything you have already reviewed or acted on, ensuring nothing is offered twice.
4. **Rank**: Score surviving opportunities using weighted match signals so the best fits surface at the top with a full score breakdown.
5. **Report**: Render today's shortlist into clean Markdown, CSV, and JSON files ready for review.
6. **Track**: Record your decisions (`shortlisted`, `applied`, `skipped`, `rejected`) so tomorrow's run picks up where today left off.

For a complete walkthrough of a full daily run, see [docs/WORKFLOW.md](docs/WORKFLOW.md).

## What It Is / What It Is Not

- **What it is**: An offline end-to-end job search workflow runner, filter engine, weighted ranking scorer, and application state tracker.
- **What it is not**: It is not a web scraper, does not connect to external job boards, requires no API tokens or passwords, and makes no network requests.

## Requirements

- Python 3.11+ (tested on Python 3.12).
- Standard library only.
- No external packages or build steps required.

## Quickstart: Your First Run

Run the complete workflow against the shipped sample listings and example configuration in `--dry-run` mode to preview today's shortlist without modifying state files:

```bash
python3 -m reaper run --fixtures fixtures/sample_listings.jsonl --config examples/workflow.example.json --state fixtures/sample_seen.json --out out --dry-run
```

Observed output:

```text
Workflow Run Summary
====================================================================
Reconciliation: 38 ingested (1 duplicate(s) dropped) -> 22 reaped -> 2 already seen -> 13 survived -> 10 shortlisted (target: 10, shortfall: 0)
--------------------------------------------------------------------
Rule / Category                      Decision                Count
--------------------------------------------------------------------
blocked_keywords                     reap                        1
employment_type                      reap                        3
exclude_seniority                    reap                        3
exclude_title_patterns               reap                        1
freshness                            reap                        4
location_policy                      reap                        2
min_salary                           reap                        2
require_description                  reap                        1
require_title_patterns               reap                        5
--------------------------------------------------------------------
Total Reaped                         reap                       22
Already Seen (State)                 drop                        2
Eligible Survivors                   survive                    13
Shortlisted Today                    shortlist                  10
====================================================================

Today's Shortlist (10 listings):
--------------------------------------------------------------------
#1 [job-012] (score: 8.92) Full Stack Application Engineer and Cloud Infrastructure Specialist @ Cascade Computing Group
    Location: Austin, TX | Type: full-time | Salary: $100,000-$120,000/year
    URL: https://example.com/jobs/12

#2 [job-032] (score: 6.92) Systems Software Engineer @ Vanguard Computing LLC
    Location: Chicago, IL | Type: full-time | Salary: $130,000-$150,000/year
    URL: https://example.com/jobs/32

#3 [job-028] (score: 6.75) Data Engineer @ Quantix Digital Systems
    Location: New York, NY | Type: full-time | Salary: $125,000-$145,000/year
    URL: https://example.com/jobs/28

#4 [job-025] (score: 6.60) Cloud Systems Engineer @ Meridian Peak Analytics
    Location: Austin, TX | Type: full-time | Salary: $115,000-$135,000/year
    URL: https://example.com/jobs/25

#5 [job-005] (score: 6.56) Systems Specialist @ Apex Orbital Systems
    Location: New York, NY | Type: full-time | Salary: $115,000-$135,000/year
    URL: https://example.com/jobs/5

#6 [job-029] (score: 6.48) Reliability Engineer @ Northstar Network Systems
    Location: Austin, TX | Type: full-time | Salary: $105,000-$125,000/year
    URL: https://example.com/jobs/29

#7 [job-011] (score: 6.46) Data Platform Developer @ Aura Automation Inc
    Location: Remote (United States) | Type: full-time | Salary: $130,000-$150,000/year
    URL: https://example.com/jobs/11

#8 [job-001] (score: 6.43) Software Engineer @ Acme Widgets Ltd
    Location: Austin, TX | Type: full-time | Salary: $110,000-$130,000/year
    URL: https://example.com/jobs/1

#9 [job-008] (score: 6.41) Infrastructure Engineer @ Pinnacle Dataworks
    Location: Chicago, IL | Type: full-time | Salary: $120,000-$140,000/year
    URL: https://example.com/jobs/8

#10 [job-027] (score: 6.40) Infrastructure Specialist @ Solaria Automation Labs
    Location: Chicago, IL | Type: full-time | Salary: $110,000-$125,000/year
    URL: https://example.com/jobs/27
```

To see the exact mathematical reasons why each listing received its score, add `--explain-scores`:

```bash
python3 -m reaper run --fixtures fixtures/sample_listings.jsonl --config examples/workflow.example.json --state fixtures/sample_seen.json --out out --dry-run --explain-scores
```

To execute the live run, write reports to `out/`, and track shortlisted vacancies in `state/seen.json`:

```bash
python3 -m reaper run --fixtures fixtures/sample_listings.jsonl --config examples/workflow.example.json --state state/seen.json --out out
```

## How to Use Your Own Listings

The workflow ingests local listing records from `.jsonl` or `.csv` files.

### JSONL Format

Each line is an independent JSON object:

```json
{"id": "dev-101", "title": "Software Engineer", "company": "Acme Widgets Ltd", "location": "Austin, TX", "employment_type": "full-time", "salary_min": 110000, "salary_max": 130000, "salary_period": "year", "posted_at": "2026-08-15", "url": "https://example.com/jobs/101", "description": "Design core backend microservices."}
```

### CSV Format

Standard comma-separated table with a header row matching listing field names:

```csv
id,title,company,location,employment_type,salary_min,salary_max,salary_period,posted_at,url,description
dev-101,Software Engineer,Acme Widgets Ltd,"Austin, TX",full-time,110000,130000,year,2026-08-15,https://example.com/jobs/101,Design core backend microservices.
```

### Field Specification

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `str` | **Yes** | Unique identifier for the listing within the source. |
| `title` | `str` | **Yes** | Job vacancy title. |
| `company` | `str` | **Yes** | Employer or organisation name. |
| `location` | `str` | No | Geographic location or remote eligibility string (default: `""`). |
| `employment_type` | `str` | No | Work arrangement, e.g. `full-time`, `contract` (default: `""`). |
| `description` | `str` | No | Full textual job description (default: `""`). |
| `url` | `str` | No | Web URL pointing to the original posting (default: `""`). |
| `posted_at` | `str` | No | ISO 8601 date string, e.g. `2026-08-15` (default: `""`). |
| `salary_min` | `int` | No | Minimum compensation figure (default: `null`). |
| `salary_max` | `int` | No | Maximum compensation figure (default: `null`). |
| `salary_period` | `str` | No | Compensation timeframe: `year`, `month`, or `hour` (default: `""`). |
| `source` | `str` | No | Origin tag or source identifier (default: `""`). |

### What Happens When Fields Are Missing

- **Required Fields (`id`, `title`, `company`)**: Records missing any of these three fields are rejected with a descriptive error naming the field. Malformed rows are appended to `source.errors` and logged to `stderr`. They are never silently ignored.
- **Optional Text Fields**: Default to empty strings (`""`).
- **Numeric Fields (`salary_min`, `salary_max`)**: Strings with currency symbols and commas (e.g. `"$120,000"`) are automatically coerced to integer values. Empty or invalid numbers default to `null`.
- **Policy Rules**: If a listing has an empty date or salary, rules such as `freshness` and `min_salary` consult their configured policies (`missing_date_policy` and `missing_salary_policy`) to either keep or reap the posting.

### Writing a Custom `Source` Adapter

You can stream listings from any local database, export format, or generator by implementing Python's `Source` protocol:

```python
from typing import Iterator
from reaper.model import Listing
from reaper.sources import Source


class CustomArchiveSource:
    name: str = "archive_source"

    def __init__(self, raw_records: list[dict]) -> None:
        self.raw_records = raw_records
        self.errors: list[tuple[str, int, str]] = []

    def pages(self, page_size: int) -> Iterator[list[Listing]]:
        batch: list[Listing] = []
        for line_no, record in enumerate(self.raw_records, start=1):
            try:
                batch.append(Listing.from_dict(record))
                if len(batch) >= page_size:
                    yield batch
                    batch = []
            except Exception as err:
                self.errors.append((self.name, line_no, str(err)))
        if batch:
            yield batch
```

## Where Your Listings Come From

`listing-reaper` operates strictly offline and never connects to external networks or scrapes web pages. It expects you to provide data files you already have, whether downloaded directly from platforms, retrieved through applicant tracking feeds, or exported from personal archives.

The platform guide in [docs/SOURCES.md](docs/SOURCES.md) details export structures, typical fields, data-quality caveats, and ready-to-paste `field_map` configurations for 22 platforms across large aggregators (Indeed, LinkedIn, Google Jobs, ZipRecruiter, Talent.com, Glassdoor, Monster, SimplyHired, Dice), hourly platforms (Snagajob), remote-first boards (Remotive, Himalayas, Jobicy, Arbeitnow, RemoteOK), applicant tracking systems (Greenhouse, Lever, Ashby, Workable), startup/internship portals (Wellfound, Internshala), and public sector boards (USAJOBS). Sample exports demonstrating various foreign schemas are available in `examples/exports/`.

## Reading the Report

Every live workflow run writes reports into `--out` (default: `out/`):

### 1. Markdown Report (`out/shortlist.md`)

Designed for direct reading and note-taking:
- **Overview**: High-level summary of total ingested, reaped, already seen, survivors, and shortfall counts.
- **Today's Shortlist**: Quick table with rank, score, ID, title, company, location, salary, and direct links.
- **Detailed Profiles**: Individual profile sections for every shortlisted vacancy displaying the full score component breakdown, metadata, and description snippets.
- **Reaping Summary**: Complete audit table listing counts of postings reaped by each configured rule.

### 2. CSV Report (`out/shortlist.csv`)

Flat tabular file suitable for importing into spreadsheet applications:
- `rank`: Relative score position (1 to N).
- `id`: Unique vacancy ID.
- `score`: Four-decimal match score.
- `title`, `company`, `location`, `employment_type`: Standard listing attributes.
- `salary_min`, `salary_max`, `salary_period`: Normalized compensation data.
- `posted_at`, `url`: Publication date and link.

### 3. JSON Report (`out/shortlist.json`)

Machine-readable JSON document containing:
- `date`: Run date (ISO format).
- `reconciliation`: Complete pipeline reconciliation counts.
- `reap_stats`: Breakdown of reaped counts per rule.
- `shortlist`: Array of shortlisted objects with complete listing details and score component dictionaries.

## Tracking What You Did

The state tracker maintains a persistent record of vacancies you have seen and acted on, preventing duplicate reviews on future runs.

### Default State File

The state tracker stores data in JSON format at `state/seen.json` (or a custom path passed via `--state`):

```json
{
  "version": 1,
  "seen": {
    "full stack application engineer and cloud infrastructure specialist::cascade computing group": {
      "listing_id": "job-012",
      "first_seen": "2026-09-12",
      "last_seen": "2026-09-12",
      "status": "applied"
    }
  }
}
```

### Side Effect of Running the Workflow

When you run `python3 -m reaper run`, all listings selected for today's shortlist are automatically recorded in the state file with status `shortlisted`. On subsequent runs, those listings are identified as `already_seen` and dropped before ranking, allowing new opportunities to surface.

To run the workflow without updating the state file, pass `--no-track` or `--dry-run`.

### Updating Status with `track`

When you take action on a vacancy, record your decision using `track`:

```bash
python3 -m reaper track --state state/seen.json --id job-012 --status applied
```

Observed output:

```text
Updated listing 'job-012': status changed from 'shortlisted' to 'applied' (key: full stack application engineer and cloud infrastructure specialist::cascade computing group).
```

Supported statuses:
- `shortlisted`: Chosen for active review.
- `applied`: Application submitted.
- `skipped`: Reviewed and deliberately passed over.
- `rejected`: Received a rejection or archive notification.

If an unrecognized listing ID is passed, `track` fails with exit code `2` rather than creating a corrupt entry. If the state file is corrupt or unreadable, `track` errors cleanly naming the file and never performs a silent reset.

## Tuning the Ranking

Rankings are computed by the `Scorer` based on the `scoring` block in your configuration. Each signal is additive and weighted:

$$\text{Total Score} = \sum (\text{weight}_i \times \text{signal}_i)$$

### Scoring Signals

| Signal | Description | Raw Range | Default Weight |
|---|---|---|---|
| `title_match` | Evaluates patterns from `require_title_patterns`. Awards `1.5` for prefix matches at the start of the title, and `1.0` for matches elsewhere. | $\ge 0.0$ | `3.0` |
| `salary` | Higher annualised maximum salary scores higher, normalised against `salary_ceiling`. | `[0.0, 1.0]` | `2.0` |
| `freshness` | Newer postings score higher, decreasing linearly between `max_age_days` and zero. | `[0.0, 1.0]` | `1.5` |
| `description_depth` | Longer descriptions score higher, capped at `description_depth_cap` characters. | `[0.0, 1.0]` | `1.0` |
| `location_fit` | Exact `allowed_locations` match (`1.0`) outscores remote (`0.5`), which outscores non-matching locations (`0.0`). | `[0.0, 1.0]` | `1.0` |
| `penalty_overlong_title` | Penalizes keyword-stuffed titles exceeding 50 characters, scaling with excess length. | `[0.0, 1.0]` | `-1.0` |

### Deterministic Tie-Breaking

When candidate scores are identical, ties break strictly and deterministically:
1. Higher `score` descending.
2. More recent `posted_at` descending.
3. Lexicographical `id` ascending.

If all scoring weights are set to zero, candidate order is still 100% deterministic and never depends on dictionary or set iteration order.

---

## Concepts

- **Listing**: A structured data record representing a vacancy (`id`, `title`, `company`, `location`, `employment_type`, `description`, `salary_min`, `salary_max`, `salary_period`, `posted_at`, `url`, `source`).
- **Rule**: A registered evaluation unit with defined schema parameters and an evaluation function returning a `Verdict`.
- **Verdict**: An explicit decision (`keep` or `reap`) accompanied by a complete, human-readable sentence stating the exact evidence found. Generic failure messages are prohibited.
- **Kill Log & Trace**: Every evaluated rule appends a `RuleTrace` recording the rule ID, decision, reason, and parameters used.
- **Gate Model (First Reap Wins)**: Configured rules act as an ordered sequence of gates. Evaluation short-circuits on the first rule that rejects a listing; subsequent rules are bypassed, and `rules_evaluated` is logged in verdict details. Kept listings pass through all gates and carry their full pass trace.

## CLI Reference

```text
python3 -m reaper run      --fixtures FILE [--fixtures FILE ...] --config FILE
                           [--out DIR] [--format md|csv|json] [--target N] [--limit N]
                           [--since-days N] [--state FILE] [--no-track] [--dry-run]
                           [--explain-scores] [--plugins MODULE[,MODULE...]]
python3 -m reaper track    --state FILE --id ID --status applied|skipped|rejected
                           [--fixtures FILE] [--config FILE] [--plugins MODULE[,MODULE...]]
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
| `run` | `--fixtures FILE ...` | One or more paths to `.jsonl` or `.csv` fixture exports (required). |
| `run` | `--config FILE` | Path to JSON rules configuration (required). |
| `run` | `--out DIR` | Directory to write report outputs (default: `out`). |
| `run` | `--format FMT` | Output format override (`markdown`, `csv`, `json`). |
| `run` | `--target N` | Shortlist target size (overrides config). |
| `run` | `--limit N` | Maximum shortlist cap independent of target count. |
| `run` | `--since-days N` | Filter postings older than N days. |
| `run` | `--state FILE` | Path to persistent tracking JSON file (default: `state/seen.json`). |
| `run` | `--no-track` | Run workflow without persisting shortlisted listings to state. |
| `run` | `--dry-run` | Run workflow without writing reports or modifying state. |
| `run` | `--explain-scores` | Print per-listing score component breakdown in CLI summary. |
| `track` | `--state FILE` | Path to state tracking JSON file (required). |
| `track` | `--id ID` | Unique listing ID to update (required). |
| `track` | `--status STATUS` | New status: `shortlisted`, `applied`, `skipped`, `rejected` (required). |
| `reap` | `--fixtures FILE` | Filter records and print reap summary table. |
| `explain` | `--id ID` | Trace gate evaluation step-by-step for a single listing. |
| `simulate` | `--target N` | Simulate offline hunt in batch rounds. |
| `rules` | | List all registered filter rules and parameters. |
| `validate` | `--config FILE` | Validate configuration schema and parameters. |

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `2` | Configuration, schema, state error, unknown ID in tracking, plugin import, or usage error. |
| `3` | Execution completed, but zero listings survived reaping or made the shortlist. |
| `4` | Fixture file is unreadable or contains zero valid records. |

## Configuration

Configurations are stored in standard JSON files. Typos and unrecognized keys are rejected at load time.

```json
{
  "version": 1,
  "target_count": 10,
  "max_rounds": 5,
  "round_page_size": 10,
  "pacing_seconds": 0.0,
  "dedupe_by": ["title", "company"],
  "field_map": {
    "job_title": "title",
    "employer_name": "company",
    "job_location": "location",
    "date_posted": "posted_at",
    "apply_url": "url"
  },
  "scoring": {
    "signals": {
      "title_match": 3.0,
      "salary": 2.0,
      "freshness": 1.5,
      "description_depth": 1.0,
      "location_fit": 1.0,
      "penalty_overlong_title": -1.0
    },
    "salary_ceiling": 200000,
    "description_depth_cap": 2000,
    "shortlist_size": 10
  },
  "output": {
    "formats": ["markdown", "csv", "json"],
    "directory": "out"
  },
  "rules": [
    {
      "rule_id": "require_description",
      "min_chars": 40
    }
  ]
}
```

### Top-Level Configuration Schema

| Key | Type | Default | Description |
|---|---|---|---|
| `version` | `int` or `str` | `1` | Configuration schema version. |
| `target_count` | `int` | `10` | Desired shortlist count for a run. |
| `max_rounds` | `int` | `5` | Maximum simulation rounds. |
| `round_page_size` | `int` | `10` | Number of listings per round page. |
| `pacing_seconds` | `float` | `0.0` | Pacing delay in seconds between rounds. |
| `dedupe_by` | `list[str]` | `["title", "company"]` | Listing fields used for deduplication. |
| `field_map` | `dict[str, str]` | `{}` | Optional mapping of source column names to canonical Listing fields. |
| `scoring` | `object` | `{}` | Weighted signal scoring configuration. |
| `output` | `object` | `{}` | Report generation output settings (`formats`, `directory`). |
| `rules` | `list[object]` | `[]` | Ordered filter rule definitions evaluated as sequential gates. |

### Foreign Export Field Mapping (`field_map`)

The optional `field_map` block allows you to ingest files whose column names differ from the canonical `Listing` model without editing the file:
- **Keys**: Foreign source field names as they appear in your CSV header or JSONL objects.
- **Values**: Canonical `Listing` field names (`id`, `title`, `company`, `location`, `employment_type`, `description`, `url`, `posted_at`, `salary_min`, `salary_max`, `salary_period`, `source`).
- **Timing**: Applied during ingest, before validation and rule execution.
- **Precedence**: A mapped value wins over a same-named source field. If a source record lacks both the mapped key and canonical name, it behaves as a missing field.
- **Validation**: Any target value not in the list of valid `Listing` fields fails configuration validation with exit code `2`.

See `examples/workflow.example.json` and `examples/workflow.aggregator.example.json` for complete configurations.

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

Custom rules are self-contained functions registered into `REGISTRY`.

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
employment_type                      reap                    3
exclude_seniority                    reap                    5
exclude_title_patterns               reap                    2
freshness                            reap                    4
location_policy                      reap                    3
max_title_length                     reap                    1
min_salary                           reap                    2
require_description                  reap                    1
----------------------------------------------------------------
Total Reaped                         reap                   23
Total Kept                           keep                   15
Total Processed                                             38
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
test_description_depth_signal (tests.test_scoring.TestScoring.test_description_depth_signal) ... ok
test_freshness_signal (tests.test_scoring.TestScoring.test_freshness_signal) ... ok
test_location_fit_signal (tests.test_scoring.TestScoring.test_location_fit_signal) ... ok
test_penalty_overlong_title_signal (tests.test_scoring.TestScoring.test_penalty_overlong_title_signal) ... ok
test_salary_signal (tests.test_scoring.TestScoring.test_salary_signal) ... ok
test_title_match_signal (tests.test_scoring.TestScoring.test_title_match_signal) ... ok
test_unknown_scoring_signal_validation (tests.test_scoring.TestScoring.test_unknown_scoring_signal_validation) ... ok
test_zero_weights_deterministic_tie_breaking (tests.test_scoring.TestScoring.test_zero_weights_deterministic_tie_breaking) ... ok
test_csv_fixture_loading (tests.test_simulator.TestSimulator.test_csv_fixture_loading) ... ok
test_dedupe_within_batch_and_seen_set (tests.test_simulator.TestSimulator.test_dedupe_within_batch_and_seen_set) ... ok
test_exhaustion_shortfall_honesty (tests.test_simulator.TestSimulator.test_exhaustion_shortfall_honesty) ... ok
test_fixture_error_collection (tests.test_simulator.TestSimulator.test_fixture_error_collection) ... ok
test_mid_page_stop_accounting (tests.test_simulator.TestSimulator.test_mid_page_stop_accounting) ... ok
test_quota_stop (tests.test_simulator.TestSimulator.test_quota_stop) ... ok
test_round_trace_invariant_pinned (tests.test_simulator.TestSimulator.test_round_trace_invariant_pinned) ... ok
test_seed_determinism (tests.test_simulator.TestSimulator.test_seed_determinism) ... ok
test_atomic_state_save_and_load (tests.test_tracker.TestTracker.test_atomic_state_save_and_load) ... ok
test_corrupt_state_file_raises_cleanly (tests.test_tracker.TestTracker.test_corrupt_state_file_raises_cleanly) ... ok
test_nonexistent_state_file (tests.test_tracker.TestTracker.test_nonexistent_state_file) ... ok
test_record_and_has (tests.test_tracker.TestTracker.test_record_and_has) ... ok
test_status_transitions (tests.test_tracker.TestTracker.test_status_transitions) ... ok
test_track_unknown_id_raises_key_error (tests.test_tracker.TestTracker.test_track_unknown_id_raises_key_error) ... ok
test_dry_run_writes_nothing (tests.test_workflow.TestWorkflow.test_dry_run_writes_nothing) ... ok
test_limit_caps_shortlist_independently (tests.test_workflow.TestWorkflow.test_limit_caps_shortlist_independently) ... ok
test_no_track_does_not_modify_state (tests.test_workflow.TestWorkflow.test_no_track_does_not_modify_state) ... ok
test_reconciliation_counts_and_multi_fixture_dedupe (tests.test_workflow.TestWorkflow.test_reconciliation_counts_and_multi_fixture_dedupe) ... ok
test_since_days_filter (tests.test_workflow.TestWorkflow.test_since_days_filter) ... ok

----------------------------------------------------------------------
Ran 51 tests in 0.231s

OK
```

## Design Notes

- **Why JSON configuration**: Standard, human-readable format that is easy to version-control, audit, and validate with informative schema error messages.
- **Why standard library only**: Eliminates dependency churn, supply-chain vulnerabilities, and installation friction. Runs out-of-the-box on standard Python 3.11+ distributions.
- **Why strictly offline**: Keeps filtering logic isolated, deterministic, and safe to execute against historical fixtures without side effects or latency.
- **Why first-reap-wins**: Short-circuit evaluation minimizes wasted compute cycles and provides clear causality by identifying the exact primary reason a listing was rejected.
- **Why reasons are full sentences**: Specific evidence-backed reasons (e.g. citing character counts, matching terms, or conversion calculations) make filter logs directly actionable and debuggable.

## License

MIT. See [LICENSE](LICENSE).
