import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from apify import Actor

# USACE National Inventory of Dams (NID). The complete national inventory is
# published by the U.S. Army Corps of Engineers as a single GeoPackage file
# through the NID public API — no registration or API key. The NID is a work
# of the U.S. federal government: public domain under 17 U.S.C. § 105. The
# U.S. DOT / BTS Data Management Plan for this dataset (DOI 10.21949/1520844)
# states the data "are in the public domain, and can be shared without
# restriction" and "may be re-used without restriction", and the official
# NTAD metadata states the work "is available for unrestricted public use".
#
# Personal-data design: the source file's ownerNames column contains the
# names of private dam owners, including private individuals, and its
# designerNames column contains individual names with license numbers.
# This Actor NEVER selects those columns (see COLUMNS below) — it outputs
# owner TYPES only. The source carries no phone, email, or address columns,
# and the NID API's contact-person endpoints are never used. Dam names are
# facility names, as with bridge names in the NBI.
SOURCE_URL = "https://nid.sec.usace.army.mil/api/nation/gpkg"
SOURCE_PAGE = "https://nid.sec.usace.army.mil/"

# State / territory keys present in the source file (stateKey), with the
# state names the source itself publishes (state).
STATES: Dict[str, str] = {
    "AK": "Alaska",
    "AL": "Alabama",
    "AR": "Arkansas",
    "AZ": "Arizona",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "GU": "Guam",
    "HI": "Hawaii",
    "IA": "Iowa",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "MA": "Massachusetts",
    "MD": "Maryland",
    "ME": "Maine",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MO": "Missouri",
    "MS": "Mississippi",
    "MT": "Montana",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "NE": "Nebraska",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NV": "Nevada",
    "NY": "New York",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "PR": "Puerto Rico",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VA": "Virginia",
    "VT": "Vermont",
    "WA": "Washington",
    "WI": "Wisconsin",
    "WV": "West Virginia",
    "WY": "Wyoming",
}

HAZARD_FILTER_LABELS = {"high": "High", "significant": "Significant", "low": "Low"}

# The ONLY source columns this Actor reads. ownerNames and designerNames are
# deliberately absent (see the header comment); every other unlisted column
# is likewise never read or output.
COLUMNS = [
    "name",
    "nidId",
    "stateKey",
    "state",
    "county",
    "city",
    "distance",
    "riverName",
    "latitude",
    "longitude",
    "congDist",
    "zipcode",
    "primaryOwnerTypeId",
    "ownerTypeIds",
    "sourceAgency",
    "stateRegulatedId",
    "stateRegulatoryAgency",
    "fedRegulatedId",
    "primaryPurposeId",
    "purposeIds",
    "primaryDamTypeId",
    "damTypeIds",
    "yearCompleted",
    "damHeight",
    "hydraulicHeight",
    "structuralHeight",
    "nidHeight",
    "damLength",
    "maxStorage",
    "normalStorage",
    "surfaceArea",
    "drainageArea",
    "maxDischarge",
    "spillwayTypeId",
    "publicHazardId",
    "conditionAssessId",
    "conditionAssessDate",
    "inspectionDate",
    "inspectionFrequency",
    "eapId",
    "eapLastRevDate",
    "operationalStatusId",
    "dataUpdated",
]


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    return " ".join(str(val).split()).strip()


def safe_int_or_none(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


def safe_float_or_none(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def build_item(row: sqlite3.Row) -> Dict[str, Any]:
    """One raw NID dam record -> one normalized dam item. Only the columns
    in COLUMNS are read; nothing else in the record is output."""
    city = clean_str(row["city"])
    if city.lower() == "none":
        city = ""
    return {
        "dam_name": clean_str(row["name"]),
        "nid_id": clean_str(row["nidId"]),
        "state": clean_str(row["stateKey"]),
        "state_name": clean_str(row["state"]),
        "county": clean_str(row["county"]),
        "city": city,
        "distance_to_city_mi": safe_float_or_none(row["distance"]) if city else None,
        "river_name": clean_str(row["riverName"]),
        "latitude": safe_float_or_none(row["latitude"]),
        "longitude": safe_float_or_none(row["longitude"]),
        "congressional_district": clean_str(row["congDist"]),
        "zip_code": clean_str(row["zipcode"]),
        "primary_owner_type": clean_str(row["primaryOwnerTypeId"]),
        "owner_types": clean_str(row["ownerTypeIds"]),
        "source_agency": clean_str(row["sourceAgency"]),
        "state_regulated": clean_str(row["stateRegulatedId"]),
        "state_regulatory_agency": clean_str(row["stateRegulatoryAgency"]),
        "federal_regulated": clean_str(row["fedRegulatedId"]),
        "primary_purpose": clean_str(row["primaryPurposeId"]),
        "purposes": clean_str(row["purposeIds"]),
        "primary_dam_type": clean_str(row["primaryDamTypeId"]),
        "dam_types": clean_str(row["damTypeIds"]),
        "year_completed": safe_int_or_none(row["yearCompleted"]),
        "dam_height_ft": safe_float_or_none(row["damHeight"]),
        "hydraulic_height_ft": safe_float_or_none(row["hydraulicHeight"]),
        "structural_height_ft": safe_float_or_none(row["structuralHeight"]),
        "nid_height_ft": safe_float_or_none(row["nidHeight"]),
        "dam_length_ft": safe_float_or_none(row["damLength"]),
        "max_storage_acre_ft": safe_float_or_none(row["maxStorage"]),
        "normal_storage_acre_ft": safe_float_or_none(row["normalStorage"]),
        "surface_area_acres": safe_float_or_none(row["surfaceArea"]),
        "drainage_area_sq_mi": safe_float_or_none(row["drainageArea"]),
        "max_discharge_cfs": safe_float_or_none(row["maxDischarge"]),
        "spillway_type": clean_str(row["spillwayTypeId"]),
        "hazard_potential_class": clean_str(row["publicHazardId"]),
        "condition_assessment": clean_str(row["conditionAssessId"]),
        "condition_assessment_date": clean_str(row["conditionAssessDate"]),
        "last_inspection_date": clean_str(row["inspectionDate"]),
        "inspection_frequency_years": safe_int_or_none(row["inspectionFrequency"]),
        "eap_status": clean_str(row["eapId"]),
        "eap_last_revision_date": clean_str(row["eapLastRevDate"]),
        "operational_status": clean_str(row["operationalStatusId"]),
        "data_updated": clean_str(row["dataUpdated"]),
        "source_endpoint": SOURCE_URL,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def download_inventory(dest_path: str) -> None:
    headers = {
        "User-Agent": "Apify-DamInventoryCollector/1.0 (+https://apify.com)",
        "Accept": "application/octet-stream",
    }
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async with client.stream("GET", SOURCE_URL, headers=headers, timeout=600.0) as response:
            response.raise_for_status()
            with open(dest_path, "wb") as fh:
                async for chunk in response.aiter_bytes(chunk_size=1 << 20):
                    fh.write(chunk)


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        raw_states: List[str] = actor_input.get("states") or []
        hazard_class: str = clean_str(actor_input.get("hazardClass", "all")).lower()
        inspection_overdue: bool = bool(actor_input.get("inspectionOverdue", False))
        max_items: int = int(actor_input.get("maxItems", 100))

        requested: List[str] = []
        for entry in raw_states:
            code = clean_str(entry).upper()
            if code in STATES:
                if code not in requested:
                    requested.append(code)
            elif code:
                Actor.log.warning(f"Ignoring unknown state code: {entry!r}")
        state_codes = requested if requested else list(STATES.keys())
        hazard_label = HAZARD_FILTER_LABELS.get(hazard_class, "")

        today = datetime.now(timezone.utc).date()
        try:
            overdue_cutoff = today.replace(year=today.year - 5).isoformat()
        except ValueError:
            overdue_cutoff = today.replace(year=today.year - 5, day=28).isoformat()

        Actor.log.info(
            "Querying USACE National Inventory of Dams "
            f"(states={state_codes}, hazardClass={hazard_class}, "
            f"inspectionOverdue={inspection_overdue}, maxItems={max_items})..."
        )

        pushed = 0
        tmp = tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            await download_inventory(tmp_path)
            Actor.log.info(f"Downloaded national inventory file ({os.path.getsize(tmp_path)} bytes).")

            connection = sqlite3.connect(tmp_path)
            connection.row_factory = sqlite3.Row
            try:
                select_sql = f"SELECT {', '.join(COLUMNS)} FROM dams"
                for state_abbr in state_codes:
                    if pushed >= max_items:
                        break
                    cursor = connection.execute(
                        select_sql + " WHERE stateKey = ? ORDER BY fid",
                        (state_abbr,),
                    )
                    state_seen = 0
                    for row in cursor:
                        item = build_item(row)
                        if not item["nid_id"]:
                            continue
                        state_seen += 1
                        if hazard_label and item["hazard_potential_class"] != hazard_label:
                            continue
                        if inspection_overdue:
                            last = item["last_inspection_date"]
                            if last and last >= overdue_cutoff:
                                continue
                        charge_result = await Actor.push_data(item, charged_event_name="dam-record")
                        pushed += 1
                        if charge_result and getattr(charge_result, "event_charge_limit_reached", False):
                            Actor.log.info("User spending limit reached. Stopping gracefully.")
                            await Actor.exit()
                            return
                        if pushed >= max_items:
                            break
                    Actor.log.info(f"{state_abbr}: scanned {state_seen} dam records.")
            finally:
                connection.close()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if pushed == 0:
            Actor.log.warning("No matching dams found for the selected filters.")
        else:
            Actor.log.info(f"Run completed successfully. Total normalized dams saved: {pushed}")
