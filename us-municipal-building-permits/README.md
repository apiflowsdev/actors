# US Municipal Building Permits

Extract standardized municipal building permit records from official US city open-data APIs — **Seattle, Austin, and Los Angeles** — in one clean, fixed JSON schema.

Each city portal publishes permits with different column names (`estprojectcost` vs. `total_job_valuation` vs. `valuation`), date formats, and address structures. This Actor queries the official Socrata APIs directly, normalizes every record into the same schema, classifies the construction trade, deduplicates, and delivers dataset items that pipelines, analytics tools, and AI agents can consume without per-city parsing code.

## What you get

- **Official public records only** — data comes straight from the cities' open-data endpoints; no synthetic or fabricated rows.
- **One schema for every city** — the same 14 fields regardless of source portal.
- **Built-in trade classification** — filter by Solar, Roofing, Pool, ADU, HVAC, Electrical, or New Construction, or add your own keyword.
- **Business data only** — output includes permit IDs, property addresses, valuations, work descriptions, and contractor *business* names. Individual homeowner/applicant names, phone numbers, and emails are never included.
- **Pay per result** — you are charged per permit record delivered ($0.005/record), plus a minimal Actor start fee. Set a maximum total charge on the run to cap spend; the Actor stops gracefully when the cap is reached.

## Supported cities & official sources

| City | State | Official open-data portal | Endpoint ID |
| :--- | :--- | :--- | :--- |
| **Seattle** | WA | `data.seattle.gov` | `76t5-zqzr` |
| **Austin** | TX | `data.austintexas.gov` | `3syk-w9eu` |
| **Los Angeles** | CA | `data.lacity.org` | `pi9x-tg5x` |

## Input parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `cities` | Array | One or more of `seattle`, `austin`, `los_angeles`. |
| `tradeFilter` | String | `all`, `solar`, `roofing`, `pool`, `adu`, `hvac`, `electrical`, or `new_construction`. |
| `customKeyword` | String | Optional case-insensitive keyword matched against the work description (e.g. `"EV CHARGER"`, `"SIDING"`, `"REMODEL"`). |
| `daysBack` | Integer | Fetch permits issued within the last N days (default `30`, max `365`). |
| `minValuationUsd` | Integer | Only return permits at or above this estimated project cost (default `0`). |
| `maxItemsPerCity` | Integer | Maximum matching records per city (default `100`). |

## Output example (normalized JSON)

```json
{
  "city": "Seattle",
  "state": "WA",
  "permit_id": "24-101234",
  "issued_date": "2026-11-12",
  "permit_type": "Construction Permit",
  "trade_category": "roofing",
  "status": "Issued",
  "estimated_value_usd": 24500.0,
  "address": "2410 10TH AVE E",
  "zip_code": "98102",
  "contractor_name": "EXAMPLE ROOFING CO LLC",
  "work_description": "TEAR OFF AND RE-ROOF EXISTING SINGLE-FAMILY RESIDENCE.",
  "source_endpoint": "https://data.seattle.gov/resource/76t5-zqzr.json",
  "scraped_at": "2026-11-17T00:00:00+00:00"
}
```

## Data notes

- Records are retrieved live from the official endpoints at run time; each item carries its `source_endpoint` and retrieval timestamp (`scraped_at`) for provenance.
- Source data is published by each city under its own open-data terms and is provided "as is"; the cities make no warranty as to accuracy, timeliness, or completeness. Verify critical records against the source portal.
- Permit coverage, fields, and update cadence are controlled by the cities and may change without notice.
