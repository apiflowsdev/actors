# Austin, TX Building Permits — Official Open Data

Extract standardized building permit records for **Austin, Texas** from the City of Austin's official open data API, in one clean, fixed JSON schema.

The City of Austin publishes issued construction permits through its open data portal. This Actor queries the official Socrata API directly, normalizes every record into a fixed schema, classifies the construction trade, deduplicates, and delivers dataset items that pipelines, analytics tools, and AI agents can consume without writing their own Socrata integration.

## What you get

- **Official public records only** — data comes straight from the City of Austin's open data endpoint; no synthetic or fabricated rows.
- **Public domain data** — the City of Austin offers its open data free and without restriction; datasets are in the public domain unless otherwise noted (see Attribution below).
- **Built-in trade classification** — filter by Solar, Roofing, Pool, ADU, HVAC, Electrical, or New Construction, or add your own keyword.
- **Business data only** — output includes permit IDs, property addresses, valuations, work descriptions, and contractor *business* names. Individual homeowner/applicant names, phone numbers, and emails are never included.
- **Pay per result** — you are charged per permit record delivered ($0.005/record), plus a minimal Actor start fee. Set a maximum total charge on the run to cap spend; the Actor stops gracefully when the cap is reached.

## Data source

| City | State | Official open-data portal | Dataset | Endpoint ID |
| :--- | :--- | :--- | :--- | :--- |
| **Austin** | TX | `data.austintexas.gov` | Issued Construction Permits | `3syk-w9eu` |

## Input parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `cities` | Array | Currently `austin` only. |
| `tradeFilter` | String | `all`, `solar`, `roofing`, `pool`, `adu`, `hvac`, `electrical`, or `new_construction`. |
| `customKeyword` | String | Optional case-insensitive keyword matched against the work description (e.g. `"EV CHARGER"`, `"SIDING"`, `"REMODEL"`). |
| `daysBack` | Integer | Fetch permits issued within the last N days (default `30`, max `365`). |
| `minValuationUsd` | Integer | Only return permits at or above this estimated project cost (default `0`). |
| `maxItemsPerCity` | Integer | Maximum matching records (default `100`). |

## Output example (normalized JSON)

```json
{
  "city": "Austin",
  "state": "TX",
  "permit_id": "2026-123456 BP",
  "issued_date": "2026-11-12",
  "permit_type": "Building Permit",
  "trade_category": "roofing",
  "status": "Issued",
  "estimated_value_usd": 24500.0,
  "address": "2410 EXAMPLE ST",
  "zip_code": "78704",
  "contractor_name": "EXAMPLE ROOFING CO LLC",
  "work_description": "Residential roofing replacement.",
  "source_endpoint": "https://data.austintexas.gov/resource/3syk-w9eu.json",
  "scraped_at": "2026-11-17T00:00:00+00:00"
}
```

## Attribution

Permit data: **City of Austin, Texas — Austin Development Services**, via the City of Austin Open Data Portal (https://data.austintexas.gov). Per the City of Austin Open Data Terms of Use, data on the portal are offered free and without restriction and are in the public domain unless otherwise noted.

## Data notes

- Records are retrieved live from the official endpoint at run time; each item carries its `source_endpoint` and retrieval timestamp (`scraped_at`) for provenance.
- The City of Austin provides the data "as is" and makes no warranty as to accuracy, timeliness, or completeness. Verify critical records against the source portal.
- Permit coverage, fields, and update cadence are controlled by the City and may change without notice.
