# Toronto DineSafe Restaurant Inspections — Official Open Data

Extract standardized food-premises inspection records for **Toronto, Canada** from the City of Toronto's official open data, in one clean, fixed JSON schema.

DineSafe is Toronto Public Health's food safety inspection and disclosure system. This Actor queries the City of Toronto's official open-data datastore directly, groups every infraction row into **one item per inspection**, normalizes severity levels, and delivers dataset items that pipelines, analytics tools, and AI agents can consume without building their own integration.

## What you get

- **Official public records only** — data comes straight from the City of Toronto Open Data datastore (refreshed daily by the City); no synthetic or fabricated rows.
- **One item per inspection** — infractions are nested in a single `infractions` array with category, detail, published severity, and a normalized `severity_level` (Minor / Significant / Crucial), instead of one scattered row per infraction.
- **Useful filters** — lookback window, inspection status (Pass / Conditional Pass / Closed), minimum infraction severity, and establishment-name keyword.
- **Business data only** — output includes establishment names, addresses, inspection results, and outcomes. The source dataset's phone column is **deliberately excluded** from the output.
- **Pay per result** — you are charged per inspection record delivered ($0.005/record), plus a minimal Actor start fee. Set a maximum total charge on the run to cap spend; the Actor stops gracefully when the cap is reached.

## Data source

| Jurisdiction | Publisher | Program | Portal |
| :--- | :--- | :--- | :--- |
| **Toronto, ON** | Toronto Public Health | DineSafe | `open.toronto.ca/dataset/dinesafe` |

## Input parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `daysBack` | Integer | Inspections performed within the last N days (default `90`, max `3650`). |
| `statusFilter` | String | `all`, `pass`, `conditional_pass`, or `closed`. |
| `keyword` | String | Optional case-insensitive keyword matched against the establishment name (e.g. `"SUSHI"`). |
| `minSeverity` | String | `all`, `minor`, `significant`, or `crucial` — only inspections with at least one infraction at this severity or higher. |
| `maxItems` | Integer | Maximum inspection records to extract (default `100`). |

## Output example (normalized JSON)

```json
{
  "establishment_id": "001Vo000013QjdPIAS",
  "establishment_name": "EXAMPLE RESTAURANT",
  "address": "1871 O'Connor Dr",
  "postal_code": "M4A 1X1",
  "inspection_date": "2026-04-21",
  "status": "Pass",
  "latitude": 43.72198563,
  "longitude": -79.30349182,
  "infraction_count": 2,
  "infractions": [
    {
      "category": "05. MAINTENANCE / SANITATION OF NON-FOOD CONTACT SURFACES / EQUIPMENT",
      "detail": "FAIL TO ENSURE EQUIPMENT SURFACE SANITIZED AS NECESSARY - SEC. 22",
      "severity": "M - Minor",
      "severity_level": "Minor"
    }
  ],
  "observation": "One or more minor infractions were observed under the Food Premises Regulation during an inspection.",
  "outcome_date": "",
  "outcome_description": "",
  "amount_fined": null,
  "source_endpoint": "https://open.toronto.ca/dataset/dinesafe/",
  "scraped_at": "2026-11-19T00:00:00+00:00"
}
```

## Attribution

Contains information licensed under the **Open Government Licence – Toronto**. Data: **City of Toronto — Toronto Public Health (DineSafe)**, via Toronto Open Data (https://open.toronto.ca/dataset/dinesafe/).

## Data notes

- Records are retrieved live from the official datastore at run time; each item carries its `source_endpoint` and retrieval timestamp (`scraped_at`) for provenance.
- The City of Toronto provides the data "as is" and makes no warranty as to accuracy, timeliness, or completeness. Verify critical records against the source portal.
- Inspection coverage, fields, and update cadence are controlled by the City and may change without notice.
