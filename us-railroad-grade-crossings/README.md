# US Railroad Grade Crossing Inventory — Official FRA Open Data

Extract standardized railroad grade crossing inventory records for the **United States** from the Federal Railroad Administration's official open data, in one clean, fixed JSON schema.

The FRA's Grade Crossing Inventory (Form 71) is the national register of highway-rail crossings: every public and private crossing reported by railroads and state DOTs, with its location, operating railroad, warning devices, train traffic, and highway traffic. This Actor queries the official dataset on data.transportation.gov directly and delivers **one item per crossing** that pipelines, analytics tools, and AI agents can consume without building their own integration.

## What you get

- **Official public records only** — data comes straight from the FRA dataset on the U.S. DOT open-data portal (updated monthly by the FRA); no synthetic or fabricated rows.
- **One item per crossing** — a curated, typed subset of the inventory's 260+ columns: identifiers, location with coordinates, railroad, crossing type/purpose/position, closed status, warning-device code, train movements per day (with a computed daily total), passenger trains, max speed, main tracks, and highway AADT.
- **Useful filters** — state list, railroad code, county keyword, crossing type (Public / Private), active-only, record-revision recency, and a minimum trains-per-day threshold.
- **No contact data** — the source dataset's emergency, railroad, and state contact **phone columns are deliberately excluded**: they are never queried, read, or output.
- **Pay per result** — you are charged per crossing record delivered ($0.005/record), plus a minimal Actor start fee. Set a maximum total charge on the run to cap spend; the Actor stops gracefully when the cap is reached.

## Data source

| Jurisdiction | Publisher | Program | Portal |
| :--- | :--- | :--- | :--- |
| **United States (nationwide)** | Federal Railroad Administration (FRA), U.S. DOT | Grade Crossing Inventory (Form 71) | `data.transportation.gov` dataset `m2f8-22s6` |

## Input parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `states` | Array of strings | State names to include (e.g. `["Texas", "Ohio"]`), matched case-insensitively. Empty = all states. |
| `railroadCode` | String | Optional railroad reporting mark, exactly as published (e.g. `"BNSF"`). |
| `county` | String | Optional county-name keyword (case-insensitive substring). |
| `crossingType` | String | `all`, `Public`, or `Private`. |
| `activeOnly` | Boolean | When true (default), crossings marked closed are excluded. |
| `updatedWithinDays` | Integer | Only records revised within the last N days; `0` (default) = no recency filter. |
| `minTrainsPerDay` | Integer | Only crossings with at least this many total train movements per day. |
| `maxItems` | Integer | Maximum crossing records to extract (default `100`). |

## Output example (normalized JSON)

```json
{
  "crossing_id": "967179D",
  "railroad_code": "BNSF",
  "railroad_name": "BNSF Railway Company",
  "state_name": "TEXAS",
  "county_name": "HEMPHILL",
  "city_name": "CANADIAN",
  "street": "RR USE ONLY",
  "highway_name": "PRIVATE",
  "latitude": 35.84356,
  "longitude": -100.48045,
  "lat_long_source": "Estimated",
  "crossing_type": "Private",
  "crossing_purpose": "Highway",
  "crossing_position": "At Grade",
  "is_closed": false,
  "warning_device_code": "",
  "signs_or_signals": true,
  "train_detection": "None",
  "whistle_ban": "",
  "trains_day_thru": 29,
  "trains_night_thru": 28,
  "trains_switching": 0,
  "trains_transit": 0,
  "trains_per_day_total": 57,
  "passenger_trains_per_day": 0,
  "max_speed_mph": 70,
  "main_tracks": 2,
  "highway_aadt": null,
  "highway_aadt_year": "",
  "revision_date": "2026-03-25",
  "source_endpoint": "https://data.transportation.gov/Railroads/Crossing-Inventory-Data-Form-71-Current/m2f8-22s6",
  "scraped_at": "2026-11-19T00:00:00+00:00"
}
```

## Attribution

Data: **Federal Railroad Administration (FRA), U.S. Department of Transportation**, via data.transportation.gov (dataset "Crossing Inventory Data (Form 71) - Current"). The dataset is designated **Public Domain (U.S. Government Works)** in its official metadata.

## Data notes

- Records are retrieved live from the official dataset at run time; each item carries its `source_endpoint` and retrieval timestamp (`scraped_at`) for provenance.
- State, county, and city names are output exactly as published in the inventory (uppercase). Train counts and speeds are as reported to the FRA by railroads and state DOTs; the U.S. DOT provides the data "as is" and makes no warranty as to accuracy, timeliness, or completeness. Verify critical records against the source portal.
- Inventory coverage, fields, and update cadence are controlled by the FRA and may change without notice.
