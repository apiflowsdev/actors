import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import httpx
from apify import Actor

# 稼働検証済み：Austin 市公式 Socrata SODA API エンドポイント定義
CITY_CONFIGS: Dict[str, Dict[str, Any]] = {
    "austin": {
        "city_name": "Austin",
        "state": "TX",
        "endpoint": "https://data.austintexas.gov/resource/3syk-w9eu.json",
        "date_field": "issue_date",
        "order_field": "issue_date DESC",
    },
}

TRADE_KEYWORDS: Dict[str, List[str]] = {
    "solar": ["solar", "photovoltaic", "pv system", "battery storage", "powerwall"],
    "roofing": ["roof", "reroof", "re-roof", "shingle", "roofing"],
    "pool": ["pool", "swimming pool", "spa", "jacuzzi"],
    "adu": ["adu", "accessory dwelling", "garage conversion", "guest house"],
    "hvac": ["hvac", "heat pump", "air conditioning", "furnace", "mechanical"],
    "electrical": ["electrical", "panel upgrade", "ev charger", "200 amp", "subpanel"],
    "new_construction": ["new construction", "new building", "new single family", "erect"],
}


def safe_float(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    try:
        cleaned = str(val).replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    return " ".join(str(val).split()).strip()


def detect_trade(description: str, permit_type: str) -> str:
    combined = f"{description} {permit_type}".lower()
    for trade, keywords in TRADE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return trade
    return "general"


def normalize_record(city_key: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """各都市ごとに異なるSocrataのJSONフィールドを単一のクリーンなスキーマへ統一"""
    cfg = CITY_CONFIGS[city_key]
    permit_id = ""
    issued_date = ""
    permit_type = ""
    status = ""
    description = ""
    valuation = 0.0
    address = ""
    zip_code = ""
    contractor = ""

    if city_key == "austin":
        permit_id = clean_str(raw.get("permit_number"))
        issued_date = clean_str(raw.get("issue_date"))[:10]
        permit_type = clean_str(raw.get("permit_type_desc") or raw.get("permit_type"))
        status = clean_str(raw.get("status_current"))
        description = clean_str(raw.get("description"))
        valuation = safe_float(raw.get("total_job_valuation"))
        address = clean_str(raw.get("original_address1"))
        zip_code = clean_str(raw.get("original_zip"))
        contractor = clean_str(raw.get("contractor_company_name"))

    trade_category = detect_trade(description, permit_type)

    return {
        "city": cfg["city_name"],
        "state": cfg["state"],
        "permit_id": permit_id,
        "issued_date": issued_date,
        "permit_type": permit_type,
        "trade_category": trade_category,
        "status": status,
        "estimated_value_usd": valuation,
        "address": address,
        "zip_code": zip_code,
        "contractor_name": contractor,
        "work_description": description,
        "source_endpoint": cfg["endpoint"],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def matches_filters(
    item: Dict[str, Any],
    trade_filter: str,
    custom_keyword: str,
    min_valuation: float,
) -> bool:
    if min_valuation > 0 and item["estimated_value_usd"] < min_valuation:
        return False

    searchable = f"{item['work_description']} {item['permit_type']}".lower()

    if trade_filter != "all":
        keywords = TRADE_KEYWORDS.get(trade_filter, [])
        if not any(kw in searchable for kw in keywords):
            return False

    if custom_keyword:
        if custom_keyword.lower() not in searchable:
            return False

    return True


async def fetch_city_permits(
    client: httpx.AsyncClient,
    city_key: str,
    cutoff_iso: str,
    fetch_limit: int,
) -> List[Dict[str, Any]]:
    cfg = CITY_CONFIGS[city_key]
    params = {
        "$where": f"{cfg['date_field']} >= '{cutoff_iso}'",
        "$order": cfg["order_field"],
        "$limit": str(fetch_limit),
    }
    headers = {
        "User-Agent": "Apify-MunicipalPermitsCollector/1.0 (+https://apify.com)",
        "Accept": "application/json",
    }
    response = await client.get(cfg["endpoint"], params=params, headers=headers, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        return []
    return data


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        cities: List[str] = actor_input.get("cities") or ["austin"]
        trade_filter: str = actor_input.get("tradeFilter", "all")
        custom_keyword: str = clean_str(actor_input.get("customKeyword", ""))
        days_back: int = int(actor_input.get("daysBack", 30))
        min_valuation: float = float(actor_input.get("minValuationUsd", 0))
        max_items_per_city: int = int(actor_input.get("maxItemsPerCity", 100))

        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
        cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT00:00:00")

        total_pushed = 0
        seen_keys = set()

        # フィルタリングで除外される分を見越して多めにフェッチ（最大5000件）
        raw_fetch_limit = min(max(max_items_per_city * 5, 500), 5000)

        async with httpx.AsyncClient() as client:
            for city_key in cities:
                if city_key not in CITY_CONFIGS:
                    Actor.log.warning(f"Unsupported city skipped: {city_key}")
                    continue

                Actor.log.info(f"Querying official Socrata API for {city_key} since {cutoff_iso}...")
                try:
                    raw_rows = await fetch_city_permits(client, city_key, cutoff_iso, raw_fetch_limit)
                except Exception as exc:
                    Actor.log.error(f"Failed to fetch data for {city_key}: {exc}")
                    continue

                city_count = 0
                for raw_row in raw_rows:
                    if city_count >= max_items_per_city:
                        break

                    normalized = normalize_record(city_key, raw_row)
                    if not normalized["permit_id"]:
                        continue

                    dedupe_key = f"{city_key}:{normalized['permit_id']}"
                    if dedupe_key in seen_keys:
                        continue

                    if not matches_filters(normalized, trade_filter, custom_keyword, min_valuation):
                        continue

                    seen_keys.add(dedupe_key)

                    # Pay-Per-Event (PPE) 課金付きでデータセットへ保存
                    charge_result = await Actor.push_data(
                        normalized,
                        charged_event_name="permit-record",
                    )
                    city_count += 1
                    total_pushed += 1

                    # ユーザーの最大予算上限（Max Total Charge）に到達したら安全停止
                    if charge_result and getattr(charge_result, "event_charge_limit_reached", False):
                        Actor.log.info("User spending limit reached. Stopping gracefully.")
                        await Actor.exit()
                        return

                Actor.log.info(f"Extracted {city_count} matching permits for {city_key}.")

        if total_pushed == 0:
            Actor.log.warning("No matching permits found for the selected filters.")
        else:
            Actor.log.info(f"Run completed successfully. Total normalized permits saved: {total_pushed}")