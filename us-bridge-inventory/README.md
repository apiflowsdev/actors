# US Bridge Inventory — Official FHWA Open Data

Extract standardized bridge inventory records for the **United States** from the Federal Highway Administration's official **National Bridge Inventory (NBI)**, in one clean, fixed JSON schema.

The NBI is the national register of public highway bridges: every bridge and culvert reported to the FHWA by states, federal agencies, and tribal governments under the National Bridge Inspection Standards — 624,939 highway bridges in the 2026 edition. This Actor reads the FHWA's official per-state files in the current **SNBI** (Specifications for the National Bridge Inventory) format and delivers **one item per bridge** that pipelines, analytics tools, and AI agents can consume without building their own integration.

## What you get

- **Official public records only** — data comes straight from the FHWA's published 2026 NBI state files; no synthetic or fabricated rows.
- **One item per bridge** — a curated, typed subset of the SNBI record: bridge number and name, state/county/place codes, coordinates, location description, owner and maintenance agency codes, year built, geometry (lengths, widths, deck area), component condition ratings (deck / superstructure / substructure / culvert), the FHWA Good/Fair/Poor condition classification, load-rating factors, the route carried and feature crossed, average daily traffic, posting status, and the last inspection date.
- **Useful filters** — state / territory list, minimum year built, and bridge condition category (Good / Fair / Poor).
- **No personal data** — the inventory describes public structures. Owner and maintenance fields are **agency codes** (state DOTs, counties, federal agencies), and no individual contact information exists in or is output from these records.
- **Pay per result** — you are charged per bridge record delivered ($0.005/record), plus a minimal Actor start fee. Set a maximum total charge on the run to cap spend; the Actor stops gracefully when the cap is reached.

## Data source

| Jurisdiction | Publisher | Program | Portal |
| :--- | :--- | :--- | :--- |
| **United States (nationwide)** | Federal Highway Administration (FHWA), U.S. DOT | National Bridge Inventory (NBI), 2026 SNBI edition | `fhwa.dot.gov/bridge/nbi/` per-state JSON files |

## Input parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `states` | Array of strings | Two-letter state / territory codes to include (e.g. `["DE", "TX"]`). Empty = all states and territories listed on the FHWA 2026 download page. |
| `minYearBuilt` | Integer | Only bridges built in or after this year; `0` (default) = no year filter. |
| `conditionCategory` | String | `all` (default), `good`, `fair`, or `poor`, using the FHWA condition classification in the source data. |
| `maxItems` | Integer | Maximum bridge records to extract (default `100`). |

## Output example (normalized JSON)

```json
{
  "bridge_number": "000000001494016",
  "bridge_name": "",
  "state_code": 10,
  "state": "DE",
  "state_name": "Delaware",
  "county_code": "3",
  "place_code": "10003",
  "highway_agency_district": "01",
  "latitude": 39.540833,
  "longitude": -75.738333,
  "location": "9 MI W OF REEDY POINT",
  "owner_code": "FL06",
  "maintenance_code": "FL06",
  "toll_code": "N",
  "year_built": 1959,
  "nbis_bridge_length_ft": 2058.1,
  "total_bridge_length_ft": 2058.1,
  "max_span_length_ft": 600.1,
  "deck_width_out_to_out_ft": 64.0,
  "deck_width_curb_to_curb_ft": 58.4,
  "approach_roadway_width_ft": 64.0,
  "deck_area_sqft": 131718.4,
  "deck_condition_rating": "6",
  "superstructure_condition_rating": "5",
  "substructure_condition_rating": "6",
  "culvert_condition_rating": "N",
  "bridge_condition": "Fair",
  "inventory_rating_factor": 0.65,
  "operating_rating_factor": 0.85,
  "route_carried": "DEL 896, US71,301S",
  "feature_crossed": "C&D CANAL",
  "route_number": "896",
  "functional_class_code": "3",
  "average_daily_traffic": 23111,
  "adt_year": 2023,
  "posting_status_code": "PO",
  "last_inspection_date": "2024-06-01",
  "data_year": 2026,
  "source_endpoint": "https://www.fhwa.dot.gov/BRIDGE/nbi/2026/JSON/DE26.json",
  "scraped_at": "2026-11-20T00:00:00+00:00"
}
```

## Attribution

Data: **Federal Highway Administration (FHWA), U.S. Department of Transportation** — National Bridge Inventory, 2026 edition. The NBI is a work of the United States Government and is in the **public domain** (17 U.S.C. § 105); the U.S. DOT's Data Management Plan for this dataset states that the data files "are in the public domain, and can be shared without restriction" and "may be re-used without restriction."

## Data notes

- **Raw data only.** This Actor republishes the official inventory records in a normalized schema. It does not verify, certify, or rate any bridge, and it provides no safety, engineering, or compliance assessment.
- **Do not use NBI data for route clearance purposes.** The FHWA states this explicitly: bridges are generally inspected every 24 months, so clearance and condition data may not be current. Always confirm clearances, postings, and conditions with the bridge owner and posted signs.
- Records are retrieved live from the official FHWA files at run time; each item carries its `source_endpoint` and retrieval timestamp (`scraped_at`) for provenance.
- Condition ratings and traffic counts are as reported to the FHWA by states, federal agencies, and tribal governments; the U.S. DOT provides the data "as is" and makes no warranty as to accuracy, timeliness, or completeness. Verify critical records against the source portal.
- Inventory coverage, fields, and update cadence are controlled by the FHWA and may change without notice. The 2026 edition is the first published in the SNBI format; earlier editions (1992–2025) used the legacy Recording and Coding Guide ASCII format and are not covered by this Actor.
