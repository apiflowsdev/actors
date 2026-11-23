# US Offshore Well Inventory — Official BSEE Open Data

Extract standardized offshore well inventory records for **U.S. federal waters** from the Bureau of Safety and Environmental Enforcement's official **API List**, in one clean, fixed JSON schema.

The API List is the federal register of wells drilled in the Outer Continental Shelf — 57,520 wells in the edition this Actor reads — maintained by the **BSEE Data Center** and updated daily. It covers the Gulf of Mexico, Pacific, Alaska, and Atlantic OCS regions. This Actor reads BSEE's official raw data file (the same file behind the API List Online Query) and delivers **one item per well** that pipelines, analytics tools, and AI agents can consume without building their own integration.

## What you get

- **Official public records only** — data comes straight from BSEE's published raw data file; no synthetic or fabricated rows.
- **One item per well** — a curated, typed subset of the API List record: API well number, well name and suffix, well type, operator (company) name, borehole status and status date, field code, surface and bottom-hole lease numbers, area and block, spud and total-depth dates, bottom-hole measured depth, and region — plus a folded summary of the well's completion records (count, latest completion date and status, production intervals).
- **Useful filters** — OCS region list, surface area code (e.g. `MC`), operator name substring, and borehole status codes.
- **No personal data** — the inventory describes wells and the companies that operate them. No individual names or contact information of any kind are output.
- **Pay per result** — you are charged per well record delivered ($0.005/record), plus a minimal Actor start fee. Set a maximum total charge on the run to cap spend; the Actor stops gracefully when the cap is reached.

## Data source

| Jurisdiction | Publisher | Program | Portal |
| :--- | :--- | :--- | :--- |
| **United States (federal offshore waters)** | Bureau of Safety and Environmental Enforcement (BSEE) | API List (Well API / API List Online Query) | `data.bsee.gov` raw data file (`APIRawData.zip`) |

## Input parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `regions` | Array of strings | BSEE OCS region codes to include: `G` (Gulf of Mexico), `P` (Pacific), `Y` (Alaska), `A` (Atlantic). Empty = all regions. |
| `areaCode` | String | Surface area code to include (e.g. `"MC"` for Mississippi Canyon). Empty = all areas. |
| `operatorContains` | String | Case-insensitive substring matched against the operator (company) name, e.g. `"Shell"`. Empty = all operators. |
| `statusCodes` | Array of strings | Borehole status codes to include, as published (e.g. `["COM", "PA"]`). Empty = all statuses. |
| `maxItems` | Integer | Maximum well records to extract (default `100`). |

## Output example (normalized JSON)

```json
{
  "api_well_number": "608184001701",
  "well_name": "SS001",
  "well_name_suffix": "ST00BP01",
  "well_type_code": "E",
  "operator_name": "Apache Deepwater LLC",
  "borehole_status_code": "PA",
  "borehole_status_date": "2016-10-08",
  "field_name_code": "AT426",
  "surface_area_code": "AT",
  "surface_block_number": "426",
  "surface_lease_number": "G18603",
  "bottom_area_code": "AT",
  "bottom_block_number": "426",
  "bottom_lease_number": "G18603",
  "well_spud_date": "2007-02-08",
  "total_depth_date": "2007-02-16",
  "bottom_hole_total_md_ft": 13445,
  "region_code": "G",
  "region_name": "Gulf of Mexico",
  "completions_count": 3,
  "latest_completion_date": "2013-02-28",
  "latest_completion_status_code": "GSI",
  "production_intervals": "S01",
  "source_endpoint": "https://www.data.bsee.gov/Well/Files/APIRawData.zip",
  "scraped_at": "2026-11-23T04:11:27+00:00"
}
```

## Attribution

Data: **Bureau of Safety and Environmental Enforcement (BSEE)**, U.S. Department of the Interior — API List, distributed through the BSEE Data Center. The data is a work of the United States Government and is in the **public domain** (17 U.S.C. § 105); the BSEE Disclaimer states: "Information presented on this website is considered public information and may be distributed or copied."

## Data notes

- **Raw data only.** This Actor republishes the official inventory records in a normalized schema. It does not verify, certify, or rate any well, operator, or lease, and it provides no safety, engineering, or compliance assessment.
- **Status codes are BSEE's own codes**, delivered as published (e.g. `COM` completed, `PA` permanently abandoned, `TA` temporarily abandoned, `ST` shut-in, `CNL` cancelled). Consult BSEE's API List field definitions for the full code tables.
- **Masked depths.** BSEE masks some measured depths in the source file as `*****`; those records are delivered with `bottom_hole_total_md_ft` set to `null`.
- **Currency.** The source file is refreshed daily by BSEE; the inventory is a live register, so well counts and statuses change between editions. Each item carries its `source_endpoint` and retrieval timestamp (`scraped_at`) for provenance.
- **Mirror.** The identical file is mirrored on `data.boem.gov` (BOEM and BSEE share the Data Center). If the primary host does not serve the file, the Actor falls back to the mirror; `source_endpoint` records the URL that actually served the file.
- The inventory is provided "as is"; BSEE makes no warranty as to accuracy, timeliness, or completeness. Inventory coverage, fields, and update cadence are controlled by BSEE and may change without notice.
