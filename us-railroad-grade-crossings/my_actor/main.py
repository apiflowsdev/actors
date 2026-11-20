from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from apify import Actor

# US DOT / FRA Grade Crossing Inventory (Form 71) — Socrata SODA API on
# data.transportation.gov. Dataset licenseId is PUBLIC_DOMAIN (U.S. Government
# Works). The $select list is deliberately restricted to the fields below:
# the source dataset also carries emergency / railroad / state CONTACT PHONE
# columns, which are never selected, read, or output by this Actor.
SODA_URL = "https://data.transportation.gov/resource/m2f8-22s6.json"
SOURCE_PAGE = "https://data.transportation.gov/Railroads/Crossing-Inventory-Data-Form-71-Current/m2f8-22s6"

SELECT_FIELDS = [
    "revisiondate",
    "railroadcode",
    "railroadname",
    "crossingid",
    "statename",
    "countyname",
    "cityname",
    "street",
    "highwayname",
    "crossingtype",
    "crossingpurpose",
    "crossingposition",
    "latitude",
    "longitude",
    "latlongsource",
    "totaldaylightthrutrains",
    "totalnighttimethrutrains",
    "totalswitchingtrains",
    "totaltransittrains",
    "numberpassengertrainperday",
    "maximumtimetablespeed",
    "numberofmaintracks",
    "signsorsignals",
    "traindetection1",
    "whistleban",
    "annualaveragedailytrafficcount",
    "annualaveragedailytrafficyear",
    "crossingclosed",
    "wdcode",
]

PAGE_SIZE = 1000
MAX_ROWS_SCANNED = 200000


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    return " ".join(str(val).split()).strip()


def safe_int(val: Any, default: int = 0) -> int:
    if val is None or val == "":
        return default
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


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


def soql_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def build_where(
    states: List[str],
    railroad_code: str,
    county: str,
    crossing_type: str,
    active_only: bool,
    cutoff_iso: str,
) -> str:
    clauses: List[str] = []
    state_values = [clean_str(s).upper() for s in states if clean_str(s)]
    if state_values:
        clauses.append("upper(statename) in(" + ",".join(soql_quote(s) for s in state_values) + ")")
    if railroad_code:
        clauses.append("railroadcode = " + soql_quote(railroad_code.upper()))
    if county:
        clauses.append("upper(countyname) like " + soql_quote("%" + county.upper() + "%"))
    if crossing_type in ("Public", "Private"):
        clauses.append("crossingtype = " + soql_quote(crossing_type))
    if active_only:
        clauses.append("crossingclosed = 'No'")
    if cutoff_iso:
        clauses.append(f"revisiondate >= '{cutoff_iso}T00:00:00'")
    return " AND ".join(clauses)


async def fetch_rows(
    client: httpx.AsyncClient,
    where: str,
    offset: int,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "$select": ",".join(SELECT_FIELDS),
        "$order": "revisiondate DESC",
        "$limit": PAGE_SIZE,
        "$offset": offset,
    }
    if where:
        params["$where"] = where
    headers = {
        "User-Agent": "Apify-RailroadCrossingCollector/1.0 (+https://apify.com)",
        "Accept": "application/json",
    }
    response = await client.get(SODA_URL, params=params, headers=headers, timeout=60.0)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def build_item(row: Dict[str, Any]) -> Dict[str, Any]:
    """One raw SODA row -> one normalized crossing item (no phone fields exist
    in the selected columns, so nothing phone-related can leak into output)."""
    day_thru = safe_int(row.get("totaldaylightthrutrains"))
    night_thru = safe_int(row.get("totalnighttimethrutrains"))
    switching = safe_int(row.get("totalswitchingtrains"))
    transit = safe_int(row.get("totaltransittrains"))
    return {
        "crossing_id": clean_str(row.get("crossingid")),
        "railroad_code": clean_str(row.get("railroadcode")),
        "railroad_name": clean_str(row.get("railroadname")),
        "state_name": clean_str(row.get("statename")),
        "county_name": clean_str(row.get("countyname")),
        "city_name": clean_str(row.get("cityname")),
        "street": clean_str(row.get("street")),
        "highway_name": clean_str(row.get("highwayname")),
        "latitude": safe_float_or_none(row.get("latitude")),
        "longitude": safe_float_or_none(row.get("longitude")),
        "lat_long_source": clean_str(row.get("latlongsource")),
        "crossing_type": clean_str(row.get("crossingtype")),
        "crossing_purpose": clean_str(row.get("crossingpurpose")),
        "crossing_position": clean_str(row.get("crossingposition")),
        "is_closed": clean_str(row.get("crossingclosed")) == "Yes",
        "warning_device_code": clean_str(row.get("wdcode")),
        "signs_or_signals": clean_str(row.get("signsorsignals")) == "Yes",
        "train_detection": clean_str(row.get("traindetection1")),
        "whistle_ban": clean_str(row.get("whistleban")),
        "trains_day_thru": day_thru,
        "trains_night_thru": night_thru,
        "trains_switching": switching,
        "trains_transit": transit,
        "trains_per_day_total": day_thru + night_thru + switching + transit,
        "passenger_trains_per_day": safe_int(row.get("numberpassengertrainperday")),
        "max_speed_mph": safe_int(row.get("maximumtimetablespeed")),
        "main_tracks": safe_int(row.get("numberofmaintracks")),
        "highway_aadt": safe_int_or_none(row.get("annualaveragedailytrafficcount")),
        "highway_aadt_year": clean_str(row.get("annualaveragedailytrafficyear")),
        "revision_date": clean_str(row.get("revisiondate"))[:10],
        "source_endpoint": SOURCE_PAGE,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        states: List[str] = actor_input.get("states") or []
        railroad_code: str = clean_str(actor_input.get("railroadCode", ""))
        county: str = clean_str(actor_input.get("county", ""))
        crossing_type: str = actor_input.get("crossingType", "all")
        active_only: bool = bool(actor_input.get("activeOnly", True))
        updated_within_days: int = int(actor_input.get("updatedWithinDays", 0))
        min_trains_per_day: int = int(actor_input.get("minTrainsPerDay", 0))
        max_items: int = int(actor_input.get("maxItems", 100))

        cutoff_iso = ""
        if updated_within_days > 0:
            cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=updated_within_days)).strftime("%Y-%m-%d")

        where = build_where(states, railroad_code, county, crossing_type, active_only, cutoff_iso)

        Actor.log.info(
            "Querying FRA Grade Crossing Inventory on data.transportation.gov "
            f"(states={states}, railroad='{railroad_code}', county='{county}', "
            f"type={crossing_type}, activeOnly={active_only}, updatedWithinDays={updated_within_days}, "
            f"minTrainsPerDay={min_trains_per_day})..."
        )

        pushed = 0
        scanned = 0
        offset = 0

        async with httpx.AsyncClient() as client:
            while pushed < max_items and scanned < MAX_ROWS_SCANNED:
                try:
                    rows = await fetch_rows(client, where, offset)
                except Exception as exc:
                    Actor.log.error(f"Failed to fetch crossing rows at offset {offset}: {exc}")
                    break
                if not rows:
                    break
                offset += len(rows)
                scanned += len(rows)

                stop = False
                for row in rows:
                    item = build_item(row)
                    if not item["crossing_id"]:
                        continue
                    if item["trains_per_day_total"] < min_trains_per_day:
                        continue
                    charge_result = await Actor.push_data(item, charged_event_name="crossing-record")
                    pushed += 1
                    if charge_result and getattr(charge_result, "event_charge_limit_reached", False):
                        Actor.log.info("User spending limit reached. Stopping gracefully.")
                        await Actor.exit()
                        return
                    if pushed >= max_items:
                        stop = True
                        break
                if stop:
                    break

        if pushed == 0:
            Actor.log.warning("No matching crossings found for the selected filters.")
        else:
            Actor.log.info(f"Run completed successfully. Total normalized crossings saved: {pushed}")
