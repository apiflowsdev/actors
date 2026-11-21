# US Dam Inventory — Official USACE Open Data

Extract standardized dam inventory records for the **United States** from the U.S. Army Corps of Engineers' official **National Inventory of Dams (NID)**, in one clean, fixed JSON schema.

The NID is the national register of dams in the United States and its territories that meet the federal definition of a dam — 92,512 dams in the edition this Actor reads — maintained by USACE in cooperation with the Association of State Dam Safety Officials, the states, territories, and federal agencies, and distributed as part of the U.S. DOT / Bureau of Transportation Statistics **National Transportation Atlas Database (NTAD)**. This Actor reads the USACE's official national GeoPackage file, published through the NID public API, and delivers **one item per dam** that pipelines, analytics tools, and AI agents can consume without building their own integration.

## What you get

- **Official public records only** — data comes straight from the USACE's published national inventory file; no synthetic or fabricated rows.
- **One item per dam** — a curated, typed subset of the NID record: dam name and NID ID, state/county, nearest city and distance, river, coordinates, congressional district, owner **type** (never owner names), regulatory status and agencies, purposes, construction types, year completed, dimensions (heights, length), storage and drainage figures, spillway type, the hazard potential classification, the published condition assessment, the last inspection date and frequency, Emergency Action Plan status, and operational status.
- **Useful filters** — state / territory list, hazard potential class (High / Significant / Low), and an "inspection overdue" filter (no recorded inspection, or none in over 5 years).
- **No personal data** — the inventory describes structures. The source file also carries dam owner names, which include private individuals; this Actor **never reads or outputs owner names or designer names** — only owner types. No contact information of any kind is output.
- **Pay per result** — you are charged per dam record delivered ($0.005/record), plus a minimal Actor start fee. Set a maximum total charge on the run to cap spend; the Actor stops gracefully when the cap is reached.

## Data source

| Jurisdiction | Publisher | Program | Portal |
| :--- | :--- | :--- | :--- |
| **United States (nationwide)** | U.S. Army Corps of Engineers (USACE) | National Inventory of Dams (NID), via NTAD | `nid.sec.usace.army.mil` national GeoPackage (`/api/nation/gpkg`) |

## Input parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `states` | Array of strings | Two-letter state / territory codes to include (e.g. `["DE", "TX"]`). Empty = all states and territories in the inventory. |
| `hazardClass` | String | `all` (default), `high`, `significant`, or `low`, using the hazard potential classification published in the source data. Dams classified Undetermined are included only under `all`. |
| `inspectionOverdue` | Boolean | When `true`, only dams with no recorded inspection date, or whose last recorded inspection was more than 5 years before the run date. |
| `maxItems` | Integer | Maximum dam records to extract (default `100`). |

## Output example (normalized JSON)

```json
{
  "dam_name": "Portsville Mill Pond Dam",
  "nid_id": "DE00059",
  "state": "DE",
  "state_name": "Delaware",
  "county": "Sussex",
  "city": "River View Acres",
  "distance_to_city_mi": 0.3,
  "river_name": "Mill Branch",
  "latitude": 38.56149,
  "longitude": -75.63123,
  "congressional_district": "Congressional District 00, Delaware",
  "zip_code": "19956",
  "primary_owner_type": "State",
  "owner_types": "State",
  "source_agency": "Delaware",
  "state_regulated": "No",
  "state_regulatory_agency": "",
  "federal_regulated": "No",
  "primary_purpose": "Fish and Wildlife Pond",
  "purposes": "Fish and Wildlife Pond;Recreation",
  "primary_dam_type": "Gravity",
  "dam_types": "Gravity;Earth",
  "year_completed": null,
  "dam_height_ft": 11.0,
  "hydraulic_height_ft": null,
  "structural_height_ft": null,
  "nid_height_ft": 11.0,
  "dam_length_ft": 195.0,
  "max_storage_acre_ft": 160.0,
  "normal_storage_acre_ft": 72.6,
  "surface_area_acres": 21.11,
  "drainage_area_sq_mi": 8.79,
  "max_discharge_cfs": 1303.0,
  "spillway_type": "Controlled",
  "hazard_potential_class": "Low",
  "condition_assessment": "Fair",
  "condition_assessment_date": "2020-04-23",
  "last_inspection_date": "2020-04-23",
  "inspection_frequency_years": 0,
  "eap_status": "Not Required",
  "eap_last_revision_date": "2016-03-01",
  "operational_status": "Not Applicable",
  "data_updated": "2025-02-12",
  "source_endpoint": "https://nid.sec.usace.army.mil/api/nation/gpkg",
  "scraped_at": "2026-11-21T00:00:00+00:00"
}
```

## Attribution

Data: **U.S. Army Corps of Engineers (USACE)** — National Inventory of Dams, distributed by the **Bureau of Transportation Statistics (BTS), U.S. Department of Transportation**, as part of the National Transportation Atlas Database (NTAD). The NID is a work of the United States Government and is in the **public domain** (17 U.S.C. § 105); the U.S. DOT's Data Management Plan for this dataset states that the data files "are in the public domain, and can be shared without restriction" and "may be re-used without restriction," and the official NTAD metadata states the work "is available for unrestricted public use."

## Data notes

- **Raw data only.** This Actor republishes the official inventory records in a normalized schema. It does not verify, certify, or rate any dam, and it provides no safety, engineering, or compliance assessment.
- **Hazard potential class is not a condition rating.** The classification describes the consequences if a dam failed — potential loss of life and damage downstream — based on what lies below the dam. A "High" hazard dam may be in satisfactory condition, and a "Low" hazard dam may be in poor condition. Read `hazard_potential_class` and `condition_assessment` as the separate facts they are.
- **Currency varies by record.** Reporting agencies update their NID information voluntarily, some more frequently than others; each item carries the source record's own `data_updated` date. Inspection and condition data may therefore be dated. Verify critical records against the source portal.
- Records are retrieved live from the official USACE file at run time; each item carries its `source_endpoint` and retrieval timestamp (`scraped_at`) for provenance.
- The inventory is provided "as is"; USACE and the U.S. DOT make no warranty as to accuracy, timeliness, or completeness. Inventory coverage, fields, and update cadence are controlled by USACE and may change without notice.
