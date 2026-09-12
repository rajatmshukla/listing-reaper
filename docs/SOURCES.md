# Job Search Platform Guide & Field Mapping Reference

`listing-reaper` is strictly an offline analysis engine and application tracker. **It does not fetch anything.** It makes zero network requests, connects to no APIs, and contains no web drivers or scrapers. All data processed by this tool comes from files you produce and store locally on your own machine.

Where a platform provides an export or download mechanism (such as public data feeds, career center downloads, or account archive files), you can ingest those files directly. Where a platform does not provide an automated file download, you assemble a `.jsonl` or `.csv` file from listings you have opened and saved during your search sessions. The table below and the configuration reference in [README.md](../README.md#field-specification) describe the expected schema and how to map foreign field names using `field_map`.

---

## Platform Summary

| Platform | What you get | How the data reaches you | Data-quality notes |
|---|---|---|---|
| **Large Aggregators** | | | |
| **Indeed** | Broad cross-industry corporate, commercial, and technical job postings. | User-assembled CSV or JSONL export from saved listing records. | Stale postings frequently re-list with refreshed timestamps; location strings vary between hybrid, city-only, and regional remote; job types are often missing. |
| **LinkedIn** | Professional, white-collar, and tech postings with company profiles. | Exported data archives or user-assembled CSV/JSONL records. | Search URL filters are frequently ignored by backend query expansion; sponsored postings recur across searches; expired vacancies persist. |
| **Google Jobs** | Index of postings aggregated across corporate career portals and job sites. | Extracted schema.org structured data assembled into JSONL or CSV. | High rate of cross-board duplicates; salary figures are frequently third-party statistical estimates rather than employer numbers. |
| **ZipRecruiter** | Direct employer and syndicated agency postings across SMB and enterprise. | User-assembled CSV or tabular export from job notifications. | Syndicated descriptions often truncate or replace original text with generic snippets; posting dates may reflect syndication rather than publication. |
| **Talent.com** | Aggregated listings from job boards, staffing firms, and career portals. | User-assembled CSV or JSONL from job alert digests. | High concentration of third-party recruitment agencies masking true company identities; location metadata frequently lacks state disambiguation. |
| **Glassdoor** | Job postings coupled with company review and salary survey metadata. | User-assembled CSV or JSONL from search results. | Underlying job feed mirrors aggregator syndication; listings often redirect to third-party portals; salary estimates reflect site aggregates. |
| **Monster** | Enterprise, healthcare, engineering, and commercial vacancies. | User-assembled CSV or JSONL from saved job folders. | Extended listing lifecycles result in expired requisitions lingering; descriptions carry heavy legal disclaimer and boilerplate padding. |
| **SimplyHired** | High-volume syndicated listings across corporate and public boards. | User-assembled CSV or JSONL from saved search alerts. | Heavy duplication with sister aggregator networks; remote designations are frequently inferred rather than explicit. |
| **Dice** | Technology, software development, and technical contracting vacancies. | User-assembled CSV or JSONL from technical job searches. | Heavy recruiter and staffing agency volume; multi-posting of identical requisitions across geographic tags; contract durations lumped into pay text. |
| **Hourly & Part-Time** | | | |
| **Snagajob** | Hourly, shift, retail, hospitality, and customer service positions. | User-assembled CSV or tabular export from local search feeds. | Descriptions are often generic position summaries; compensation is hourly (`salary_period: hour`); locations frequently specify store numbers or addresses. |
| **Remote-First Boards** | | | |
| **Remotive** | Curated remote software engineering, product, and tech roles worldwide. | Public board download, open data feeds, or exported JSONL. | Geographic restrictions vary ("Worldwide", "US Only", "Europe / Americas"); cleaner formatting than aggregators, but filled roles linger unless pruned. |
| **Himalayas** | Comprehensive remote technology, design, and operations positions. | Public download or user-assembled JSONL from public board pages. | Detailed structured tags when provided; location rules must handle multi-region eligibility arrays and international time-zone constraints. |
| **Jobicy** | Global remote technical and digital professional job postings. | Public feed download or user-assembled JSONL/CSV. | Uses camelCase schema attributes; geographic tags often use broad region abbreviations (`APAC`, `EMEA`, `Americas`). |
| **Arbeitnow** | European and international remote jobs with visa and location tags. | Community feed download or user-assembled JSONL. | Timestamps use ISO format; mixes fully remote roles with on-site European metropolitan listings requiring clear location rules. |
| **RemoteOK** | Community-aggregated remote engineering, support, and design listings. | Public board download or user-assembled JSONL records. | Uses `position` for title; tags contain technology stacks rather than standardized employment types; date stamps require normalization. |
| **Applicant Tracking Feeds** | | | |
| **Greenhouse** | Direct primary job requisitions published by hiring companies. | Public career board feed or user-assembled JSONL. | Cleanest primary source; zero aggregator rewrites; requisitions are removed immediately when closed; location names vary by company convention. |
| **Lever** | Direct employer postings hosted on organization career sites. | Public employer career feed or user-assembled JSONL. | Direct primary feed; titles appear under `text`; explicit `workplaceType` distinguishes remote from on-site; highly dependable data fidelity. |
| **Ashby** | High-growth software and technology organization career postings. | Public employer career board feed or user-assembled JSONL. | Modern, structured primary data; reliable compensation bands when disclosed; descriptions may include HTML tags. |
| **Workable** | Mid-market and international business career site job postings. | Public employer career feed or user-assembled JSONL. | Direct primary listings; location is frequently broken across separate `city`, `state`, and `country` fields; clear publication dates. |
| **Startup & Internships** | | | |
| **Wellfound** | Early-stage, venture-backed startup roles with compensation visibility. | User-assembled CSV or JSONL from saved job lists. | Roles provide equity and salary ranges; titles are specialized; startup requisition turnover is rapid; verify baseline cash salary. |
| **Internshala** | Internships, apprentice roles, and early-career postings. | User-assembled CSV or JSONL from search folders. | Uses `profile` for title and `stipend_amount` for pay; compensation is monthly or fixed stipend; high proportion of temporary/part-time roles. |
| **Government & Public** | | | |
| **USAJOBS** | Official United States federal government civil service positions. | Open data downloads or user-assembled JSONL/CSV records. | PascalCase schema fields; explicit closing dates (`ApplicationCloseDate`); multiple duty stations or "Negotiable Upon Selection" in locations. |

---

## Platform Details & Field Maps

### Indeed

Indeed carries general commercial, industrial, and technical listings across all experience tiers.

| Indeed Field | Listing Field | Notes |
|---|---|---|
| `job_key` | `id` | Unique posting identifier. |
| `job_title` | `title` | Job vacancy title. |
| `company_name` | `company` | Employer or organization name. |
| `formatted_location` | `location` | Geographic location or remote text. |
| `job_description` | `description` | Full text of the vacancy. |
| `job_url` | `url` | Direct application link. |
| `pub_date` | `posted_at` | Publication date string. |
| `job_type` | `employment_type` | Work arrangement (e.g. full-time). |

```json
{
  "field_map": {
    "job_key": "id",
    "job_title": "title",
    "company_name": "company",
    "formatted_location": "location",
    "job_description": "description",
    "job_url": "url",
    "pub_date": "posted_at",
    "job_type": "employment_type"
  }
}
```

**Data-Quality Notes**:
- **Re-listing and Recurrence**: Indeed frequently refreshes publication timestamps on existing postings to maintain search visibility. The persistent tracker (`state/seen.json`) is designed specifically to prevent these recurring vacancies from reappearing on your shortlist.
- **Inconsistent Locations**: Location strings vary across "Remote in Chicago, IL", "Remote", "Chicago, IL (Hybrid)", and bare city names without state codes. Configure `location_policy` with multiple pattern matches.
- **Missing Job Types**: The `job_type` field is frequently omitted or defaulted to full-time even when the description specifies contract terms. Use the `employment_type` rule's `reject_ambiguous` flag to catch discrepancies in the description.

---

### LinkedIn

LinkedIn carries white-collar professional, corporate, and technology postings worldwide.

| LinkedIn Field | Listing Field | Notes |
|---|---|---|
| `job_id` | `id` | Unique listing ID. |
| `title` | `title` | Canonical title. |
| `company_name` | `company` | Employer organization name. |
| `location` | `location` | Workplace location or remote scope. |
| `description` | `description` | Full position description. |
| `job_url` | `url` | Canonical web URL. |
| `listed_at` | `posted_at` | Listing timestamp or ISO date. |
| `employment_type` | `employment_type` | Full-time, contract, or part-time. |

```json
{
  "field_map": {
    "job_id": "id",
    "company_name": "company",
    "job_url": "url",
    "listed_at": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Ignored Search Filters**: LinkedIn search queries frequently ignore query parameters (such as "Past 24 hours" or "Remote") and return broader matching roles. Do not trust search filters; verify criteria locally using `freshness` and `location_policy`.
- **Sponsored Duplicates**: Promoted postings recur across separate search queries. Deduplication by `title` and `company` (`dedupe_by`) prevents multiple entries from cluttering your run.
- **Expired Postings**: Vacancies often remain listed days after the role has closed. Always check target links before applying.

---

### Google Jobs

Google Jobs indexes structured job postings crawled across corporate career websites and third-party boards.

| Google Jobs Field | Listing Field | Notes |
|---|---|---|
| `id` | `id` | Identifier extracted from microdata. |
| `title` | `title` | Role title. |
| `company_name` | `company` | Hiring employer. |
| `location` | `location` | Address, city, or remote descriptor. |
| `description` | `description` | Body text parsed from HTML. |
| `share_link` | `url` | Redirect URL or source link. |
| `posted_at` | `posted_at` | Date published from schema.org metadata. |

```json
{
  "field_map": {
    "company_name": "company",
    "share_link": "url"
  }
}
```

**Data-Quality Notes**:
- **Cross-Platform Duplication**: Google Jobs aggregates identical job requisitions syndicated across multiple job boards. Ensure `dedupe_by` includes both `title` and `company` to collapse duplicates into a single entry.
- **Third-Party Salary Estimates**: Google Jobs frequently injects estimated salary ranges from external benchmarks rather than employer-stated compensation. Treat unverified salary figures cautiously.

---

### ZipRecruiter

ZipRecruiter carries small business, commercial, and enterprise opportunities across diverse sectors.

| ZipRecruiter Field | Listing Field | Notes |
|---|---|---|
| `job_id` | `id` | Vacancy tracking ID. |
| `name` | `title` | Position title. |
| `hiring_company` | `company` | Organization name. |
| `location` | `location` | City, state, or remote tag. |
| `job_description` | `description` | Full text of the listing. |
| `job_url` | `url` | Application link. |
| `posted_time` | `posted_at` | Syndication timestamp. |

```json
{
  "field_map": {
    "job_id": "id",
    "name": "title",
    "hiring_company": "company",
    "job_description": "description",
    "job_url": "url",
    "posted_time": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Syndicated Description Rewrites**: Automated feeds often replace or append boilerplate summaries to descriptions. Inspect `min_chars` thresholds to avoid filtering out valid truncated listings.
- **Timestamp Drifts**: `posted_time` may represent when ZipRecruiter ingested the syndicate feed rather than when the employer opened the position.

---

### Talent.com

Talent.com aggregates employment postings from staffing firms, direct career portals, and partner job sites.

| Talent.com Field | Listing Field | Notes |
|---|---|---|
| `job_id` | `id` | Unique listing ID. |
| `job_title` | `title` | Position name. |
| `company` | `company` | Employer or recruitment firm. |
| `city` | `location` | Geographic location. |
| `description` | `description` | Listing text. |
| `link` | `url` | Outbound listing link. |
| `date` | `posted_at` | Date string. |

```json
{
  "field_map": {
    "job_id": "id",
    "job_title": "title",
    "city": "location",
    "link": "url",
    "date": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Recruitment Agency Masking**: Many listings are submitted by staffing agencies that omit the underlying employer's name, making company-based research impossible without opening the listing.
- **Interpolated Locations**: The `city` field may provide a bare locality without a state or country code.

---

### Glassdoor

Glassdoor pairs employer reviews and culture feedback with an integrated job search board.

| Glassdoor Field | Listing Field | Notes |
|---|---|---|
| `listing_id` | `id` | Listing numerical identifier. |
| `job_title` | `title` | Vacancy title. |
| `employer` | `company` | Company name. |
| `location` | `location` | Location text. |
| `description` | `description` | Full job overview. |
| `job_url` | `url` | Application URL. |
| `posted_date` | `posted_at` | Publication date. |

```json
{
  "field_map": {
    "listing_id": "id",
    "job_title": "title",
    "employer": "company",
    "job_url": "url",
    "posted_date": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Partner Syndication**: Much of Glassdoor's inventory mirrors syndicated partner exchanges. Deduplication is essential when combining Glassdoor exports with Indeed or LinkedIn files.
- **Estimated Compensation**: Salary figures listed alongside postings are often site-wide averages rather than employer-defined ranges.

---

### Monster

Monster carries traditional enterprise, corporate, engineering, and commercial positions.

| Monster Field | Listing Field | Notes |
|---|---|---|
| `req_id` | `id` | Requisition ID. |
| `title` | `title` | Position title. |
| `company` | `company` | Organization name. |
| `location` | `location` | Job location. |
| `body` | `description` | Full job posting body text. |
| `url` | `url` | Direct vacancy link. |
| `date_posted` | `posted_at` | Posting date. |

```json
{
  "field_map": {
    "req_id": "id",
    "body": "description",
    "date_posted": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Stale Requisitions**: Vacancies may linger in active feeds for weeks after hiring teams have stopped reviewing applications.
- **Boilerplate Inflation**: Descriptions often feature extensive EEO statements, company history, and legal clauses that inflate description length.

---

### SimplyHired

SimplyHired operates as a high-volume aggregator indexing corporate career pages and job boards.

| SimplyHired Field | Listing Field | Notes |
|---|---|---|
| `job_key` | `id` | Vacancy key. |
| `title` | `title` | Role title. |
| `company` | `company` | Hiring employer. |
| `location_name` | `location` | Locality or remote indicator. |
| `description` | `description` | Listing text. |
| `url` | `url` | Outbound link. |
| `date` | `posted_at` | Publication date. |

```json
{
  "field_map": {
    "job_key": "id",
    "location_name": "location",
    "date": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Syndication Overlap**: Heavy overlap with other major aggregators. Use unified `dedupe_by: ["title", "company"]` across multi-source runs.
- **Inferred Remote Flags**: Remote work tags are sometimes inferred by automated parsers and may conflict with actual text requirements in the description.

---

### Dice

Dice is a specialized board focused on software engineering, technical infrastructure, and IT contracting.

| Dice Field | Listing Field | Notes |
|---|---|---|
| `dice_id` | `id` | Unique Dice listing ID. |
| `title` | `title` | Technical job title. |
| `company` | `company` | Employer or technical staffing firm. |
| `location` | `location` | Work location or remote scope. |
| `description` | `description` | Job details and requirements. |
| `job_url` | `url` | Application link. |
| `posted_date` | `posted_at` | Date posted. |
| `employment_type` | `employment_type` | Full-time, contract, or C2C. |

```json
{
  "field_map": {
    "dice_id": "id",
    "job_url": "url",
    "posted_date": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Recruiter Re-postings**: Multiple recruitment agencies frequently post identical requisitions for the same underlying client. Deduplication by title and agency only prevents agency-level dupes; cross-agency postings require inspecting description keywords.
- **Contract Ambiguity**: Hourly contract roles ("W2", "C2C", "1099") frequently omit conversion rates or lump travel per-diems into salary fields.

---

### Snagajob

Snagajob specializes in hourly, shift, retail, hospitality, and customer service employment opportunities.

| Snagajob Field | Listing Field | Notes |
|---|---|---|
| `posting_id` | `id` | Unique vacancy ID. |
| `job_name` | `title` | Position name. |
| `brand_name` | `company` | Store or corporate employer. |
| `store_location` | `location` | Physical store or city location. |
| `job_summary` | `description` | Job duties summary. |
| `apply_link` | `url` | Direct application link. |
| `date_added` | `posted_at` | Date added to feed. |
| `shift_type` | `employment_type` | Part-time, full-time, or seasonal. |

```json
{
  "field_map": {
    "posting_id": "id",
    "job_name": "title",
    "brand_name": "company",
    "store_location": "location",
    "job_summary": "description",
    "apply_link": "url",
    "date_added": "posted_at",
    "shift_type": "employment_type"
  }
}
```

**Data-Quality Notes**:
- **Generic Role Titles**: Postings often use broad titles such as "Team Member" or "Associate" that provide little specificity. Filter on description content with `custom_patterns` or `blocked_keywords`.
- **Hourly Compensation**: Pay is quoted per hour. Ensure `salary_period: "hour"` is passed or converted when using `min_salary`.

---

### Remotive

Remotive curates remote software engineering, product, and digital positions across international organizations.

| Remotive Field | Listing Field | Notes |
|---|---|---|
| `id` | `id` | Unique vacancy ID. |
| `title` | `title` | Role title. |
| `company_name` | `company` | Organization name. |
| `candidate_required_location` | `location` | Remote geographic requirement. |
| `description` | `description` | Full position description. |
| `url` | `url` | Direct application link. |
| `publication_date` | `posted_at` | Publication ISO date. |
| `job_type` | `employment_type` | Employment category. |

```json
{
  "field_map": {
    "company_name": "company",
    "candidate_required_location": "location",
    "publication_date": "posted_at",
    "job_type": "employment_type"
  }
}
```

**Data-Quality Notes**:
- **Geographic Restrictions**: Even though all listings are remote, `candidate_required_location` often restricts candidates to specific countries ("USA Only", "Europe Only", "Worldwide"). Configure `remote_scopes` in `location_policy` to match your eligibility.
- **Listing Longevity**: High-quality listings, but postings can remain published for weeks without automatic expiration.

---

### Himalayas

Himalayas hosts remote software development, design, sales, and operations roles at technology companies.

| Himalayas Field | Listing Field | Notes |
|---|---|---|
| `id` | `id` | Listing ID. |
| `title` | `title` | Vacancy title. |
| `company_name` | `company` | Hiring company. |
| `location_restrictions` | `location` | Eligible countries or regional scope. |
| `description` | `description` | Comprehensive description. |
| `application_url` | `url` | Application link. |
| `pub_date` | `posted_at` | Date published. |

```json
{
  "field_map": {
    "company_name": "company",
    "location_restrictions": "location",
    "application_url": "url",
    "pub_date": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Complex Eligibility Lists**: Location restrictions often contain arrays or comma-separated lists of multiple countries (e.g. "US, Canada, UK").
- **Structured Compensation**: Salary bands are often included, but currencies may vary across USD, EUR, and GBP.

---

### Jobicy

Jobicy features worldwide and regional remote job openings for software developers, engineers, and digital professionals.

| Jobicy Field | Listing Field | Notes |
|---|---|---|
| `id` | `id` | Identifier. |
| `jobTitle` | `title` | Position title. |
| `companyName` | `company` | Employer name. |
| `jobGeo` | `location` | Geographic eligibility. |
| `jobDescription` | `description` | Position requirements. |
| `url` | `url` | Direct link. |
| `pubDate` | `posted_at` | Publication timestamp. |
| `jobType` | `employment_type` | Work type. |

```json
{
  "field_map": {
    "jobTitle": "title",
    "companyName": "company",
    "jobGeo": "location",
    "jobDescription": "description",
    "pubDate": "posted_at",
    "jobType": "employment_type"
  }
}
```

**Data-Quality Notes**:
- **camelCase Fields**: JSON exports from Jobicy use camelCase naming conventions that must be mapped to snake_case Listing fields.
- **Regional Abbreviations**: `jobGeo` frequently uses regional abbreviations (`Americas`, `EMEA`, `APAC`) requiring broad substring matching in `location_policy`.

---

### Arbeitnow

Arbeitnow carries remote and European technology positions with structured tags for visa sponsorship and remote flexibility.

| Arbeitnow Field | Listing Field | Notes |
|---|---|---|
| `slug` | `id` | Unique URL slug as identifier. |
| `title` | `title` | Job title. |
| `company_name` | `company` | Hiring organization. |
| `location` | `location` | Physical city or remote indicator. |
| `description` | `description` | HTML or plain description. |
| `url` | `url` | Requisition link. |
| `created_at` | `posted_at` | Creation timestamp. |
| `job_types` | `employment_type` | Array or string of types. |

```json
{
  "field_map": {
    "slug": "id",
    "company_name": "company",
    "created_at": "posted_at",
    "job_types": "employment_type"
  }
}
```

**Data-Quality Notes**:
- **Mixed Locations**: Remote postings appear alongside on-site roles in European tech hubs (Berlin, London, Amsterdam). Explicit location rules are necessary to filter out non-remote on-site roles.
- **Date Formatting**: `created_at` may contain Unix epoch integers or full ISO timestamps; `freshness` parses the leading `YYYY-MM-DD` portion.

---

### RemoteOK

RemoteOK is a community-driven board indexing remote software engineering, DevOps, and customer support listings.

| RemoteOK Field | Listing Field | Notes |
|---|---|---|
| `id` | `id` | Listing ID. |
| `position` | `title` | Job title. |
| `company` | `company` | Employer name. |
| `location` | `location` | Geographic eligibility. |
| `description` | `description` | Markdown or HTML description. |
| `url` | `url` | Listing URL. |
| `date` | `posted_at` | ISO date string. |

```json
{
  "field_map": {
    "position": "title",
    "date": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Non-standard Key for Title**: The title appears under `position` rather than `title`.
- **Tag Stacking**: Tags often combine technical stacks, seniority levels, and employment arrangements into a single array.

---

### Greenhouse

Greenhouse is an enterprise applicant tracking system publishing primary job board feeds directly from employers.

| Greenhouse Field | Listing Field | Notes |
|---|---|---|
| `id` | `id` | Internal requisition ID. |
| `title` | `title` | Role title. |
| `company_name` | `company` | Employer organization name. |
| `location_name` | `location` | Office location or remote status. |
| `content` | `description` | Unmodified employer job description. |
| `absolute_url` | `url` | Direct application portal link. |
| `updated_at` | `posted_at` | Last updated ISO timestamp. |

```json
{
  "field_map": {
    "company_name": "company",
    "location_name": "location",
    "content": "description",
    "absolute_url": "url",
    "updated_at": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Cleanest Available Source**: ATS feeds are primary data sources directly managed by the employer's talent acquisition team. They carry no aggregator rewrites or third-party syndication artifacts.
- **Immediate De-listing**: Vacancies are removed immediately when closed, reducing the risk of applying to dead listings.

---

### Lever

Lever is an applicant tracking system utilized widely by high-growth venture and mid-market organizations.

| Lever Field | Listing Field | Notes |
|---|---|---|
| `id` | `id` | Requisition ID. |
| `text` | `title` | Position title. |
| `org_name` | `company` | Employer name. |
| `workplaceType` | `location` | Remote, hybrid, or on-site descriptor. |
| `descriptionPlain` | `description` | Clean plain-text description. |
| `hostedUrl` | `url` | Direct Lever application URL. |
| `createdAt` | `posted_at` | Millisecond timestamp or ISO date. |

```json
{
  "field_map": {
    "text": "title",
    "org_name": "company",
    "workplaceType": "location",
    "descriptionPlain": "description",
    "hostedUrl": "url",
    "createdAt": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Title in `text`**: Lever standard schemas place the role title under `text` rather than `title`.
- **Explicit Workplace Classification**: The `workplaceType` field cleanly categorizes roles into `remote`, `hybrid`, or `onsite`.

---

### Ashby

Ashby is an all-in-one recruiting and ATS platform favored by modern technology and software companies.

| Ashby Field | Listing Field | Notes |
|---|---|---|
| `id` | `id` | Vacancy unique ID. |
| `title` | `title` | Position title. |
| `organizationName` | `company` | Employer organization. |
| `locationName` | `location` | Location or remote tier. |
| `descriptionHtml` | `description` | Full vacancy description. |
| `jobUrl` | `url` | Direct application URL. |
| `publishedAt` | `posted_at` | Publication ISO timestamp. |
| `employmentType` | `employment_type` | Full-time, contract, or intern. |

```json
{
  "field_map": {
    "organizationName": "company",
    "locationName": "location",
    "descriptionHtml": "description",
    "jobUrl": "url",
    "publishedAt": "posted_at",
    "employmentType": "employment_type"
  }
}
```

**Data-Quality Notes**:
- **Reliable Primary Feed**: High fidelity directly from corporate recruiting pipelines.
- **Accurate Compensation Bands**: When companies report compensation, Ashby provides structured numerical minimum and maximum values that map cleanly to `salary_min` and `salary_max`.

---

### Workable

Workable is a recruitment platform and career site provider used by international and mid-market employers.

| Workable Field | Listing Field | Notes |
|---|---|---|
| `shortcode` | `id` | Unique requisition shortcode. |
| `title` | `title` | Position title. |
| `company` | `company` | Employer name. |
| `city` | `location` | Locality or city name. |
| `description` | `description` | Position overview and requirements. |
| `url` | `url` | Canonical application link. |
| `published_on` | `posted_at` | Publication date string. |
| `employment_type` | `employment_type` | Standard employment type. |

```json
{
  "field_map": {
    "shortcode": "id",
    "city": "location",
    "published_on": "posted_at"
  }
}
```

**Data-Quality Notes**:
- **Deconstructed Location**: Workable often splits locations across `city`, `state`, and `country` fields. Map the most specific relevant key to `location`.
- **Zero Aggregator Drift**: Directly published by the employer; closed roles vanish upon requisition closure.

---

### Wellfound

Wellfound (formerly AngelList Talent) specializes in early-stage, seed, and venture-backed startup employment opportunities.

| Wellfound Field | Listing Field | Notes |
|---|---|---|
| `listing_id` | `id` | Unique listing ID. |
| `role_title` | `title` | Startup job title. |
| `startup_name` | `company` | Company or venture name. |
| `location` | `location` | Office location or remote flexibility. |
| `role_description` | `description` | Detailed role requirements. |
| `job_link` | `url` | Direct listing link. |
| `created_at` | `posted_at` | Creation date. |
| `job_type` | `employment_type` | Full-time, contract, or co-founder. |

```json
{
  "field_map": {
    "listing_id": "id",
    "role_title": "title",
    "startup_name": "company",
    "role_description": "description",
    "job_link": "url",
    "created_at": "posted_at",
    "job_type": "employment_type"
  }
}
```

**Data-Quality Notes**:
- **Broad Compensation Ranges**: Startup postings frequently pair equity grants with wide cash salary ranges; verify baseline figures against `min_salary`.
- **Rapid Requisition Churn**: Early-stage hiring needs change rapidly; positions can be filled quickly without formal de-indexing.

---

### Internshala

Internshala provides internships, trainee positions, and entry-level career opportunities for students and graduates.

| Internshala Field | Listing Field | Notes |
|---|---|---|
| `internship_id` | `id` | Opportunity ID. |
| `profile` | `title` | Role or internship profile title. |
| `company_name` | `company` | Employer name. |
| `location_names` | `location` | City or virtual/work-from-home tag. |
| `about_job` | `description` | Position responsibilities. |
| `link` | `url` | Application link. |
| `posted_on` | `posted_at` | Posting date string. |
| `stipend_amount` | `salary_min` | Minimum monthly stipend. |

```json
{
  "field_map": {
    "internship_id": "id",
    "profile": "title",
    "company_name": "company",
    "location_names": "location",
    "about_job": "description",
    "link": "url",
    "posted_on": "posted_at",
    "stipend_amount": "salary_min"
  }
}
```

**Data-Quality Notes**:
- **Field Nomenclature**: The vacancy title is named `profile`, and the description is named `about_job`.
- **Monthly Stipends**: Pay is typically structured as a monthly stipend rather than an annual salary figure. Ensure downstream rules take timeframe conversions into account.

---

### USAJOBS

USAJOBS is the official job portal and open-data provider for United States federal government civil service positions.

| USAJOBS Field | Listing Field | Notes |
|---|---|---|
| `PositionID` | `id` | Federal position control number. |
| `PositionTitle` | `title` | Civil service position title. |
| `OrganizationName` | `company` | Agency or department name. |
| `PositionLocationDisplay` | `location` | Duty location or telework eligibility. |
| `JobSummary` | `description` | Official position summary. |
| `ApplyURI` | `url` | Application gateway URL. |
| `PublicationStartDate` | `posted_at` | Opening date string. |
| `PositionOfferingType` | `employment_type` | Permanent, term, or temporary. |

```json
{
  "field_map": {
    "PositionID": "id",
    "PositionTitle": "title",
    "OrganizationName": "company",
    "PositionLocationDisplay": "location",
    "JobSummary": "description",
    "ApplyURI": "url",
    "PublicationStartDate": "posted_at",
    "PositionOfferingType": "employment_type"
  }
}
```

**Data-Quality Notes**:
- **PascalCase Attribute Names**: Federal open-data schemas use PascalCase attribute keys.
- **Multiple Duty Stations**: The `PositionLocationDisplay` string may list multiple military bases, administrative centers, or regional field offices.
- **Strict Filing Deadlines**: Federal announcements close strictly on their stated application deadline (`ApplicationCloseDate`). Postings cannot accept applications once closed.

---

## Adding a Platform That Is Not Listed Here

When working with a new job board, internal company export, or custom archive format, follow this straightforward recipe:

### 1. Obtain Your Local Export
Save your listings into a local `.csv` or `.jsonl` file. For example, suppose you have an export named `custom_export.csv`.

### 2. Inspect Column Names
Inspect the header row of your CSV file or the first line of your JSONL file:

```bash
head -n 1 custom_export.csv
```

Example header:
```csv
requisition_num,headline,hiring_firm,work_city,published_date,career_page
```

### 3. Write the `field_map` Configuration
Create or edit your configuration JSON file (e.g. `config.custom.json`) mapping the foreign column names to canonical `Listing` field names:

```json
{
  "version": 1,
  "target_count": 5,
  "field_map": {
    "requisition_num": "id",
    "headline": "title",
    "hiring_firm": "company",
    "work_city": "location",
    "published_date": "posted_at",
    "career_page": "url"
  },
  "rules": [
    {
      "rule_id": "require_description",
      "min_chars": 40
    }
  ]
}
```

### 4. Validate the Configuration
Run `validate` to verify that all mapped targets are recognized `Listing` fields:

```bash
python3 -m reaper validate --config config.custom.json
```

Output:
```text
Valid configuration: 'config.custom.json'
Field map (6 mapping(s)):
  career_page -> url
  headline -> title
  hiring_firm -> company
  published_date -> posted_at
  requisition_num -> id
  work_city -> location
Active rules (1 configured):
  1. require_description
```

### 5. Run a Dry-Run Test
Run the workflow in `--dry-run` mode to confirm records load and rules evaluate without modifying state:

```bash
python3 -m reaper run --fixtures custom_export.csv --config config.custom.json --dry-run
```

### 6. Read the Summary and Tune
Review the reap summary and reconciliation line in the CLI output. If records were reaped unexpectedly, run `explain` on a specific listing ID to see the exact gate and reason:

```bash
python3 -m reaper explain --fixtures custom_export.csv --config config.custom.json --id req-001
```
