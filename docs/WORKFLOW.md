# Daily Job Search Walkthrough

This guide walks through a complete daily job search cycle using `listing-reaper`. The entire workflow runs offline on your local machine with zero credentials and no network requests.

---

## 1. The Daily Lifecycle

A complete cycle consists of six steps:

1. **Gather**: Collect local exports (JSONL or CSV) from searches or board downloads.
2. **Reap**: Filter out ineligible postings against strict criteria with an explainable audit trail.
3. **Dedupe**: Eliminate duplicate listings and postings previously seen or acted upon.
4. **Rank**: Score surviving candidates using weighted match signals to surface the best fits.
5. **Report**: Generate actionable shortlist files in Markdown, CSV, and JSON formats.
6. **Track**: Record status changes (`shortlisted`, `applied`, `skipped`, `rejected`) so subsequent runs start fresh.

---

## 2. Day 1: Ingest, Rank, and Generate Shortlist

### Step 2.1 — Dry-Run Preview

Before writing output files or persisting tracking records, run a `--dry-run` against your listings export to inspect the pipeline metrics:

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

### Step 2.2 — Score Inspection

To understand why specific roles ranked higher, pass `--explain-scores` to inspect the weighted component breakdown:

```bash
python3 -m reaper run --fixtures fixtures/sample_listings.jsonl --config examples/workflow.example.json --state fixtures/sample_seen.json --out out --dry-run --explain-scores
```

Example breakdown from output:

```text
#1 [job-012] (score: 8.92) Full Stack Application Engineer and Cloud Infrastructure Specialist @ Cascade Computing Group
    Location: Austin, TX | Type: full-time | Salary: $100,000-$120,000/year
    URL: https://example.com/jobs/12
    Score Breakdown:
      - description_depth        +0.0580
      - freshness                +1.0000
      - location_fit             +1.0000
      - penalty_overlong_title   -0.3400
      - salary                   +1.2000
      - title_match              +6.0000
```

### Step 2.3 — Live Execution

Execute the run to write reports to `out/` and record the shortlisted candidates to `state/seen.json`:

```bash
python3 -m reaper run --fixtures fixtures/sample_listings.jsonl --config examples/workflow.example.json --state state/seen.json --out out
```

Generated reports:
- `out/shortlist.md`: Detailed Markdown summary with candidate profiles and rule audit.
- `out/shortlist.csv`: Flat table suitable for spreadsheets or local tracking tables.
- `out/shortlist.json`: Structured machine-readable data.

---

## 3. Reviewing Reports and Taking Action

Open `out/shortlist.md` to review the candidates. Suppose you decide to apply to `job-012` and `job-032`, and skip `job-028`.

---

## 4. Day 2: Updating Status and Re-Running

### Step 4.1 — Record Actions

Update each listing status using the `track` command:

```bash
python3 -m reaper track --state state/seen.json --id job-012 --status applied
```

Observed output:

```text
Updated listing 'job-012': status changed from 'shortlisted' to 'applied' (key: full stack application engineer and cloud infrastructure specialist::cascade computing group).
```

```bash
python3 -m reaper track --state state/seen.json --id job-032 --status applied
```

Observed output:

```text
Updated listing 'job-032': status changed from 'shortlisted' to 'applied' (key: systems software engineer::vanguard computing llc).
```

### Step 4.2 — Day 2 Workflow Run

Now run the workflow for the next day. The engine loads `state/seen.json`, detects that the previously shortlisted postings have already been seen, and surfaces new opportunities from the remaining pool:

```bash
python3 -m reaper run --fixtures fixtures/sample_listings.jsonl --config examples/workflow.example.json --state state/seen.json --out out
```

Observed output:

```text
Workflow Run Summary
====================================================================
Reconciliation: 38 ingested (1 duplicate(s) dropped) -> 22 reaped -> 10 already seen -> 5 survived -> 5 shortlisted (target: 10, shortfall: 5)
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
Already Seen (State)                 drop                       10
Eligible Survivors                   survive                     5
Shortlisted Today                    shortlist                   5
====================================================================

Today's Shortlist (5 listings):
--------------------------------------------------------------------
#1 [job-026] (score: 6.25) Backend Software Engineer @ Helios Software Works
    Location: Remote (United States) | Type: full-time | Salary: $120,000-$140,000/year
    URL: https://example.com/jobs/26

#2 [job-031] (score: 6.22) Platform Specialist @ Crestline Robotics Group
    Location: Austin, TX | Type: full-time | Salary: $98,000-$112,000/year
    URL: https://example.com/jobs/31

#3 [job-003] (score: 6.20) Backend Developer @ Nova Dynamics Corp
    Location: Remote (United States) | Type: full-time | Salary: $125,000-$145,000/year
    URL: https://example.com/jobs/3

#4 [job-030] (score: 6.20) Software Applications Developer @ Blue Harbor Technologies
    Location: Remote (Worldwide) | Type: full-time | Salary: $110,000-$130,000/year
    URL: https://example.com/jobs/30

#5 [job-007] (score: 6.09) Site Reliability Analyst @ Zephyr Logistics Inc
    Location: Remote (Worldwide) | Type: full-time | Salary: $105,000-$120,000/year
    URL: https://example.com/jobs/7

Notice: Shortfall of 5 listings below target count (10).
```

Notice that none of the listings shortlisted on Day 1 are repeated.
