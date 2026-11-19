import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from apify import Actor

# City of Toronto DineSafe (Toronto Public Health) — CKAN DataStore API.
# NOTE: this CKAN instance does not expose datastore_search_sql (404), so the
# Actor pages datastore_search sorted by inspectionDate DESC and applies the
# date cutoff client-side (sorted order makes that an early stop).
CKAN_SEARCH_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/datastore_search"
RESOURCE_ID = "75dbb3ff-8281-4f03-9de2-bd1214761302"
SOURCE_PAGE = "https://open.toronto.ca/dataset/dinesafe/"

STATUS_MAP = {"pass": "Pass", "conditional_pass": "Conditional Pass", "closed": "Closed"}
SEVERITY_RANK = {"Minor": 1, "Significant": 2, "Crucial": 3}
MIN_SEVERITY_RANK = {"all": 0, "minor": 1, "significant": 2, "crucial": 3}
POSTAL_RE = re.compile(r"([A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d)\s*$")
PAGE_SIZE = 1000
MAX_ROWS_SCANNED = 200000


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    return " ".join(str(val).split()).strip()


def safe_float_or_none(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def severity_level(raw: Any) -> Tuple[str, int]:
    """'M - Minor' -> ('Minor', 1); 'S - Significant' -> 2; 'C - Crucial' -> 3."""
    text = clean_str(raw).lower()
    for name, rank in SEVERITY_RANK.items():
        if name.lower() in text:
            return name, rank
    return "", 0


def clean_address(address: Any) -> str:
    # The source renders a missing unit/suite as the literal token "None".
    return clean_str(re.sub(r"\s+None\s+", " ", clean_str(address)))


def extract_postal(address: str) -> str:
    match = POSTAL_RE.search(address or "")
    return match.group(1).upper() if match else ""


async def fetch_rows(
    client: httpx.AsyncClient,
    status_value: str,
    offset: int,
) -> List[Dict[str, Any]]:
    import json as _json

    params: Dict[str, Any] = {
        "resource_id": RESOURCE_ID,
        "limit": PAGE_SIZE,
        "offset": offset,
        "sort": "inspectionDate desc, estId asc",
    }
    if status_value:
        params["filters"] = _json.dumps({"inspectionStatus": status_value})
    headers = {
        "User-Agent": "Apify-DineSafeCollector/1.0 (+https://apify.com)",
        "Accept": "application/json",
    }
    response = await client.get(CKAN_SEARCH_URL, params=params, headers=headers, timeout=60.0)
    response.raise_for_status()
    payload = response.json()
    return payload.get("result", {}).get("records", [])


def build_item(rows: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
    """Group of raw rows (one per infraction) -> one normalized inspection item.

    The source dataset's phone column is deliberately never read: this Actor
    does not output phone numbers.
    """
    first = rows[0]
    infractions: List[Dict[str, Any]] = []
    max_rank = 0
    amount_fined: Optional[float] = None
    outcome_date = ""
    outcome_desc = ""

    for row in rows:
        detail = clean_str(row.get("typeDesc"))
        category = clean_str(row.get("deficiencyDesc"))
        if detail or category:
            level, rank = severity_level(row.get("severity"))
            max_rank = max(max_rank, rank)
            infractions.append(
                {
                    "category": category,
                    "detail": detail,
                    "severity": clean_str(row.get("severity")),
                    "severity_level": level,
                }
            )
        od = clean_str(row.get("OutcomeDate"))
        if od and not outcome_date:
            outcome_date = od[:10]
        odesc = clean_str(row.get("OutcomeDesc"))
        if odesc and odesc.lower() != "none" and not outcome_desc:
            outcome_desc = odesc
        fined = safe_float_or_none(row.get("amountFined"))
        if fined is not None:
            amount_fined = fined if amount_fined is None else max(amount_fined, fined)

    address = clean_address(first.get("address"))
    item = {
        "establishment_id": clean_str(first.get("estId")),
        "establishment_name": clean_str(first.get("estName")),
        "address": address,
        "postal_code": extract_postal(address),
        "inspection_date": clean_str(first.get("inspectionDate"))[:10],
        "status": clean_str(first.get("inspectionStatus")),
        "latitude": safe_float_or_none(first.get("latitude")),
        "longitude": safe_float_or_none(first.get("longitude")),
        "infraction_count": len(infractions),
        "infractions": infractions,
        "observation": clean_str(first.get("observation")),
        "outcome_date": outcome_date,
        "outcome_description": outcome_desc,
        "amount_fined": amount_fined,
        "source_endpoint": SOURCE_PAGE,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    return item, max_rank


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        days_back: int = int(actor_input.get("daysBack", 90))
        status_filter: str = actor_input.get("statusFilter", "all")
        keyword: str = clean_str(actor_input.get("keyword", ""))
        min_severity: str = actor_input.get("minSeverity", "all")
        max_items: int = int(actor_input.get("maxItems", 100))

        status_value = STATUS_MAP.get(status_filter, "")
        required_rank = MIN_SEVERITY_RANK.get(min_severity, 0)
        cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

        Actor.log.info(
            f"Querying Toronto DineSafe datastore since {cutoff_iso} "
            f"(status={status_filter}, minSeverity={min_severity}, keyword='{keyword}')..."
        )

        pushed = 0
        scanned = 0
        offset = 0
        current_key: Optional[Tuple[str, str]] = None
        current_rows: List[Dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            while True:
                if pushed >= max_items or scanned >= MAX_ROWS_SCANNED:
                    break
                try:
                    rows = await fetch_rows(client, status_value, offset)
                except Exception as exc:
                    Actor.log.error(f"Failed to fetch DineSafe rows at offset {offset}: {exc}")
                    break
                if not rows:
                    break
                offset += len(rows)
                scanned += len(rows)

                stop = False
                window_end = False
                for row in rows:
                    row_date = clean_str(row.get("inspectionDate"))[:10]
                    if row_date < cutoff_iso:
                        # Sorted newest-first: everything after this is older.
                        window_end = True
                        break
                    if keyword and keyword.lower() not in clean_str(row.get("estName")).lower():
                        continue
                    key = (clean_str(row.get("estId")), row_date)
                    if current_key is not None and key != current_key:
                        item, rank = build_item(current_rows)
                        current_rows = []
                        if rank >= required_rank and item["establishment_id"]:
                            charge_result = await Actor.push_data(item, charged_event_name="inspection-record")
                            pushed += 1
                            if charge_result and getattr(charge_result, "event_charge_limit_reached", False):
                                Actor.log.info("User spending limit reached. Stopping gracefully.")
                                await Actor.exit()
                                return
                            if pushed >= max_items:
                                stop = True
                    current_key = key
                    current_rows.append(row)
                    if stop:
                        break
                if stop:
                    current_rows = []
                if window_end:
                    break

        # Finalize the last inspection group.
        if current_rows and pushed < max_items:
            item, rank = build_item(current_rows)
            if rank >= required_rank and item["establishment_id"]:
                await Actor.push_data(item, charged_event_name="inspection-record")
                pushed += 1

        if pushed == 0:
            Actor.log.warning("No matching inspections found for the selected filters.")
        else:
            Actor.log.info(f"Run completed successfully. Total normalized inspections saved: {pushed}")
