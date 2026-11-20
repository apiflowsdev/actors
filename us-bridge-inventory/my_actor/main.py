import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from apify import Actor

# FHWA National Bridge Inventory (NBI), 2026 edition — the first edition
# published in the SNBI (Specifications for the National Bridge Inventory)
# format. Per-state JSON files are served from fhwa.dot.gov with no
# registration or API key. The NBI is a work of the U.S. federal government:
# public domain under 17 U.S.C. § 105, and the U.S. DOT Data Management Plan
# for this dataset states the data "are in the public domain, and may be
# re-used without restriction".
#
# This Actor maps ONLY the SNBI items handled in build_item() below. The
# source records describe public structures; owner / maintenance fields are
# agency codes (state DOTs, counties, federal agencies), never individuals,
# and the inventory carries no personal contact data.
DATA_YEAR = 2026
FILE_URL_TEMPLATE = "https://www.fhwa.dot.gov/BRIDGE/nbi/2026/JSON/{code}26.json"
SOURCE_PAGE = "https://www.fhwa.dot.gov/bridge/nbi/nbi_data_2026.cfm"

# State / territory codes offered on the FHWA 2026 download page, in page
# order (Guam did not submit data in 2026 and is not listed).
STATES: Dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands",
}

CONDITION_LABELS = {"G": "Good", "F": "Fair", "P": "Poor"}
CONDITION_FILTER_CODES = {"good": "G", "fair": "F", "poor": "P"}


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    return " ".join(str(val).split()).strip()


def code_str(val: Any) -> str:
    """SNBI code items arrive as strings or numbers; normalize to a string."""
    if val is None:
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return clean_str(val)


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


def format_yyyymmdd(val: Any) -> str:
    text = code_str(val)
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return ""


def pick_carried_feature(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """SNBI feature records: BF02 = 'C' is the feature carried on the bridge,
    'B' is a feature passing below it."""
    for feature in features:
        if code_str(feature.get("BF02")) == "C":
            return feature
    return features[0] if features else {}


def pick_highway_feature(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The feature record carrying the highway traffic (ADT) fields."""
    carried = pick_carried_feature(features)
    if carried.get("BH09") is not None:
        return carried
    for feature in features:
        if feature.get("BH09") is not None:
            return feature
    return carried


def build_item(rec: Dict[str, Any], state_abbr: str, source_url: str) -> Dict[str, Any]:
    """One raw SNBI bridge record -> one normalized bridge item. Only the
    SNBI items mapped here are read; nothing else in the record is output."""
    features: List[Dict[str, Any]] = rec.get("Features") or []
    carried = pick_carried_feature(features)
    highway = pick_highway_feature(features)
    crossed_names = [
        clean_str(f.get("BF03")) for f in features if code_str(f.get("BF02")) == "B" and clean_str(f.get("BF03"))
    ]
    routes = carried.get("Routes") or []
    route_number = code_str(routes[0].get("BRT02")) if routes else ""

    posting_statuses: List[Dict[str, Any]] = rec.get("PostingStatuses") or []
    posting_status = ""
    if posting_statuses:
        latest = max(posting_statuses, key=lambda p: code_str(p.get("BPS02")))
        posting_status = code_str(latest.get("BPS01"))

    inspections: List[Dict[str, Any]] = rec.get("Inspections") or []
    inspection_dates = [code_str(i.get("BIE02")) for i in inspections if code_str(i.get("BIE02"))]
    last_inspection = format_yyyymmdd(max(inspection_dates)) if inspection_dates else ""

    condition_code = code_str(rec.get("BC12"))

    return {
        "bridge_number": clean_str(rec.get("BID01")),
        "bridge_name": clean_str(rec.get("BID02")),
        "state_code": safe_int_or_none(rec.get("BL01")),
        "state": state_abbr,
        "state_name": STATES[state_abbr],
        "county_code": code_str(rec.get("BL02")),
        "place_code": code_str(rec.get("BL03")),
        "highway_agency_district": code_str(rec.get("BL04")),
        "latitude": safe_float_or_none(rec.get("BL05")),
        "longitude": safe_float_or_none(rec.get("BL06")),
        "location": clean_str(rec.get("BL11")),
        "owner_code": code_str(rec.get("BCL01")),
        "maintenance_code": code_str(rec.get("BCL02")),
        "toll_code": code_str(rec.get("BCL05")),
        "year_built": safe_int_or_none(rec.get("BW01")),
        "nbis_bridge_length_ft": safe_float_or_none(rec.get("BG01")),
        "total_bridge_length_ft": safe_float_or_none(rec.get("BG02")),
        "max_span_length_ft": safe_float_or_none(rec.get("BG03")),
        "deck_width_out_to_out_ft": safe_float_or_none(rec.get("BG05")),
        "deck_width_curb_to_curb_ft": safe_float_or_none(rec.get("BG06")),
        "approach_roadway_width_ft": safe_float_or_none(rec.get("BG09")),
        "deck_area_sqft": safe_float_or_none(rec.get("BG16")),
        "deck_condition_rating": code_str(rec.get("BC01")),
        "superstructure_condition_rating": code_str(rec.get("BC02")),
        "substructure_condition_rating": code_str(rec.get("BC03")),
        "culvert_condition_rating": code_str(rec.get("BC04")),
        "bridge_condition": CONDITION_LABELS.get(condition_code, condition_code),
        "inventory_rating_factor": safe_float_or_none(rec.get("BLR05")),
        "operating_rating_factor": safe_float_or_none(rec.get("BLR06")),
        "route_carried": clean_str(carried.get("BF03")),
        "feature_crossed": "; ".join(crossed_names),
        "route_number": route_number,
        "functional_class_code": code_str(highway.get("BH01")),
        "average_daily_traffic": safe_int_or_none(highway.get("BH09")),
        "adt_year": safe_int_or_none(highway.get("BH11")),
        "posting_status_code": posting_status,
        "last_inspection_date": last_inspection,
        "data_year": DATA_YEAR,
        "source_endpoint": source_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_state_records(client: httpx.AsyncClient, state_abbr: str) -> List[Dict[str, Any]]:
    url = FILE_URL_TEMPLATE.format(code=state_abbr)
    headers = {
        "User-Agent": "Apify-BridgeInventoryCollector/1.0 (+https://apify.com)",
        "Accept": "application/json",
    }
    response = await client.get(url, headers=headers, timeout=180.0)
    response.raise_for_status()
    payload = json.loads(response.content)
    return payload if isinstance(payload, list) else []


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        raw_states: List[str] = actor_input.get("states") or []
        min_year_built: int = int(actor_input.get("minYearBuilt", 0))
        condition_category: str = clean_str(actor_input.get("conditionCategory", "all")).lower()
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
        condition_code_filter = CONDITION_FILTER_CODES.get(condition_category, "")

        Actor.log.info(
            "Querying FHWA National Bridge Inventory 2026 (SNBI) "
            f"(states={state_codes}, minYearBuilt={min_year_built}, "
            f"conditionCategory={condition_category}, maxItems={max_items})..."
        )

        pushed = 0

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for state_abbr in state_codes:
                if pushed >= max_items:
                    break
                url = FILE_URL_TEMPLATE.format(code=state_abbr)
                try:
                    records = await fetch_state_records(client, state_abbr)
                except Exception as exc:
                    Actor.log.error(f"Failed to fetch NBI file for {state_abbr}: {exc}")
                    continue
                Actor.log.info(f"{state_abbr}: {len(records)} bridge records in source file.")

                for rec in records:
                    item = build_item(rec, state_abbr, url)
                    if not item["bridge_number"]:
                        continue
                    if min_year_built > 0 and (item["year_built"] is None or item["year_built"] < min_year_built):
                        continue
                    if condition_code_filter and code_str(rec.get("BC12")) != condition_code_filter:
                        continue
                    charge_result = await Actor.push_data(item, charged_event_name="bridge-record")
                    pushed += 1
                    if charge_result and getattr(charge_result, "event_charge_limit_reached", False):
                        Actor.log.info("User spending limit reached. Stopping gracefully.")
                        await Actor.exit()
                        return
                    if pushed >= max_items:
                        break

        if pushed == 0:
            Actor.log.warning("No matching bridges found for the selected filters.")
        else:
            Actor.log.info(f"Run completed successfully. Total normalized bridges saved: {pushed}")
