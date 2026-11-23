import csv
import io
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import httpx
from apify import Actor

# Bureau of Safety and Environmental Enforcement (BSEE) Data Center — API
# List, the federal register of offshore wells in U.S. federal waters. The
# complete well list is published by BSEE as a single ZIP file (no
# registration or API key), refreshed daily. The data is a work of the U.S.
# federal government: public domain under 17 U.S.C. § 105. The BSEE
# Disclaimer (https://www.bsee.gov/node/14532) states: "Information
# presented on this website is considered public information and may be
# distributed or copied." No noncommercial-only, no-modification, or
# indemnity condition applies.
#
# Personal-data design: the source files carry operator (company) names
# only — offshore operators are corporations (e.g. Shell Offshore Inc.).
# No column in either source file names a private individual or carries
# personal contact details, so no column needs exclusion; the COLUMNS
# lists below are still the ONLY columns this Actor reads.
#
# Download quirk (verified 2026-11-23): the BSEE/BOEM hosts serve the ZIP
# only to requests without a narrow Accept header — see _fetch below. The
# same file is mirrored byte-identically on data.boem.gov, and a US
# residential proxy retry is kept as a final fallback.
SOURCE_URL = "https://www.data.bsee.gov/Well/Files/APIRawData.zip"
# The same file is mirrored on the sister bureau's domain (BOEM and BSEE
# share the Data Center; the API List Online Query itself lives on
# data.boem.gov). The mirror ZIP is byte-identical (member CRCs verified
# 2026-11-23). data.bsee.gov sometimes answers datacenter clients with an
# HTML page instead of the ZIP, so the Actor tries each official URL in
# order and uses the first response that is actually a ZIP file.
SOURCE_URLS = [
    SOURCE_URL,
    "https://www.data.boem.gov/Well/Files/APIRawData.zip",
    "https://data.bsee.gov/Well/Files/APIRawData.zip",
    "https://data.boem.gov/Well/Files/APIRawData.zip",
]
SOURCE_PAGE = "https://www.data.bsee.gov/Well/API/Default.aspx"

WELL_FILE_SUFFIX = "mv_api_list_all.txt"
COMPLETION_FILE_SUFFIX = "mv_api_wellcomps_all.txt"

# BSEE OCS region codes as published in the source file, with region names.
REGIONS: Dict[str, str] = {
    "G": "Gulf of Mexico",
    "P": "Pacific",
    "Y": "Alaska",
    "A": "Atlantic",
}

# The ONLY well-header columns this Actor reads.
WELL_COLUMNS = [
    "API_WELL_NUMBER",
    "WELL_TYPE_CODE",
    "WELL_NAME",
    "WELL_NAME_SUFFIX",
    "COMPANY_NAME",
    "BOREHOLE_STAT_DT",
    "BOREHOLE_STAT_CD",
    "BOTM_FLD_NAME_CD",
    "SURF_AREA_CODE",
    "SURF_BLOCK_NUMBER",
    "SURF_LEASE_NUMBER",
    "BOTM_AREA_CODE",
    "BOTM_BLOCK_NUMBER",
    "BOTM_LEASE_NUMBER",
    "WELL_SPUD_DATE",
    "TOTAL_DEPTH_DATE",
    "BH_TOTAL_MD",
    "REGION_CODE",
]

# The ONLY completion-record columns this Actor reads.
COMPLETION_COLUMNS = [
    "API_WELL_NUMBER",
    "COMPLETION_DATE",
    "PROD_INTERVAL_CD",
    "COMP_STATUS_CD",
]


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    return " ".join(str(val).split()).strip()


def safe_int_or_none(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    text = str(val).strip()
    if not text or set(text) == {"*"}:
        # The source masks some measured depths as "*****".
        return None
    try:
        return int(float(text.replace(",", "")))
    except (ValueError, TypeError):
        return None


def iso_date(val: Any) -> str:
    """Source dates are M/D/YYYY; normalize to YYYY-MM-DD. Unparseable or
    empty values become an empty string."""
    text = clean_str(val)
    if not text:
        return ""
    try:
        return datetime.strptime(text, "%m/%d/%Y").date().isoformat()
    except ValueError:
        return text


def build_completion_index(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Fold the completion records into one summary per well: count, the
    latest completion (by completion date) and its status code, and the
    set of production interval codes seen."""
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        api_number = clean_str(row.get("API_WELL_NUMBER"))
        if not api_number:
            continue
        entry = index.get(api_number)
        if entry is None:
            entry = {
                "count": 0,
                "latest_date": "",
                "latest_status": "",
                "intervals": set(),
            }
            index[api_number] = entry
        entry["count"] += 1
        comp_date = iso_date(row.get("COMPLETION_DATE"))
        if comp_date and comp_date >= entry["latest_date"]:
            entry["latest_date"] = comp_date
            entry["latest_status"] = clean_str(row.get("COMP_STATUS_CD"))
        interval = clean_str(row.get("PROD_INTERVAL_CD"))
        if interval:
            entry["intervals"].add(interval)
    return index


def build_item(
    row: Dict[str, Any],
    completion: Optional[Dict[str, Any]],
    source_url: str = SOURCE_URL,
) -> Dict[str, Any]:
    """One raw BSEE well-header record (+ its folded completion summary)
    -> one normalized well item. Only the columns in WELL_COLUMNS /
    COMPLETION_COLUMNS are read; nothing else in the record is output."""
    region_code = clean_str(row["REGION_CODE"])
    return {
        "api_well_number": clean_str(row["API_WELL_NUMBER"]),
        "well_name": clean_str(row["WELL_NAME"]),
        "well_name_suffix": clean_str(row["WELL_NAME_SUFFIX"]),
        "well_type_code": clean_str(row["WELL_TYPE_CODE"]),
        "operator_name": clean_str(row["COMPANY_NAME"]),
        "borehole_status_code": clean_str(row["BOREHOLE_STAT_CD"]),
        "borehole_status_date": iso_date(row["BOREHOLE_STAT_DT"]),
        "field_name_code": clean_str(row["BOTM_FLD_NAME_CD"]),
        "surface_area_code": clean_str(row["SURF_AREA_CODE"]),
        "surface_block_number": clean_str(row["SURF_BLOCK_NUMBER"]),
        "surface_lease_number": clean_str(row["SURF_LEASE_NUMBER"]),
        "bottom_area_code": clean_str(row["BOTM_AREA_CODE"]),
        "bottom_block_number": clean_str(row["BOTM_BLOCK_NUMBER"]),
        "bottom_lease_number": clean_str(row["BOTM_LEASE_NUMBER"]),
        "well_spud_date": iso_date(row["WELL_SPUD_DATE"]),
        "total_depth_date": iso_date(row["TOTAL_DEPTH_DATE"]),
        "bottom_hole_total_md_ft": safe_int_or_none(row["BH_TOTAL_MD"]),
        "region_code": region_code,
        "region_name": REGIONS.get(region_code, ""),
        "completions_count": completion["count"] if completion else 0,
        "latest_completion_date": completion["latest_date"] if completion else "",
        "latest_completion_status_code": (
            completion["latest_status"] if completion else ""
        ),
        "production_intervals": (
            "; ".join(sorted(completion["intervals"])) if completion else ""
        ),
        "source_endpoint": source_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def _fetch(client: httpx.AsyncClient, url: str, dest_path: str) -> bool:
    """Stream one URL to dest_path; True when it is actually a ZIP file."""
    # NOTE: do NOT send a narrow Accept header. The BSEE/BOEM server
    # answers requests with e.g. "Accept: application/zip" with its HTML
    # site shell instead of the file (verified 2026-11-23: identical
    # 27,647-byte HTML response); the default Accept (*/*) gets the ZIP.
    headers = {
        "User-Agent": "Apify-OffshoreWellCollector/1.0 (+https://apify.com)",
    }
    async with client.stream(
        "GET", url, headers=headers, timeout=600.0
    ) as response:
        response.raise_for_status()
        with open(dest_path, "wb") as fh:
            async for chunk in response.aiter_bytes(chunk_size=1 << 20):
                fh.write(chunk)
        content_type = response.headers.get("content-type")
    if zipfile.is_zipfile(dest_path):
        return True
    Actor.log.warning(
        f"{url} did not serve a ZIP file ({os.path.getsize(dest_path)} bytes, "
        f"content-type={content_type}); trying the next source."
    )
    return False


async def download_zip(dest_path: str) -> str:
    """Download the source ZIP from the first official URL that actually
    serves a ZIP file; returns the URL used. When every direct URL fails
    the Actor retries once through the Apify Proxy (US residential) as a
    final fallback — the file is ~2.6 MB, so the proxy cost of a run is
    a few cents at most."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for url in SOURCE_URLS:
            if await _fetch(client, url, dest_path):
                return url
    Actor.log.info(
        "Direct download served no ZIP; retrying through Apify Proxy "
        "(US residential)."
    )
    proxy_configuration = await Actor.create_proxy_configuration(
        groups=["RESIDENTIAL"], country_code="US"
    )
    if proxy_configuration is None:
        raise RuntimeError("Could not create an Apify Proxy configuration.")
    proxy_url = proxy_configuration.new_url()
    if hasattr(proxy_url, "__await__"):
        proxy_url = await proxy_url
    async with httpx.AsyncClient(follow_redirects=True, proxy=proxy_url) as client:
        for url in SOURCE_URLS:
            if await _fetch(client, url, dest_path):
                return url
    raise RuntimeError("No official source URL served the APIRawData.zip file.")


def read_member(zf: zipfile.ZipFile, suffix: str) -> List[Dict[str, Any]]:
    names = [n for n in zf.namelist() if n.endswith(suffix)]
    if not names:
        raise RuntimeError(f"Source ZIP does not contain a file ending {suffix}")
    raw = zf.read(names[0])
    text = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8-sig", newline="")
    return list(csv.DictReader(text))


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        raw_regions: List[str] = actor_input.get("regions") or []
        area_code: str = clean_str(actor_input.get("areaCode", "")).upper()
        operator_contains: str = clean_str(
            actor_input.get("operatorContains", "")
        ).lower()
        raw_statuses: List[str] = actor_input.get("statusCodes") or []
        max_items: int = int(actor_input.get("maxItems", 100))

        requested_regions: List[str] = []
        for entry in raw_regions:
            code = clean_str(entry).upper()
            if code in REGIONS:
                if code not in requested_regions:
                    requested_regions.append(code)
            elif code:
                Actor.log.warning(f"Ignoring unknown region code: {entry!r}")
        region_codes = requested_regions if requested_regions else list(REGIONS.keys())

        status_filter: Set[str] = set()
        for entry in raw_statuses:
            code = clean_str(entry).upper()
            if code:
                status_filter.add(code)

        Actor.log.info(
            "Querying BSEE API List (offshore well inventory) "
            f"(regions={region_codes}, areaCode={area_code or 'any'}, "
            f"operatorContains={operator_contains or 'any'}, "
            f"statusCodes={sorted(status_filter) or 'all'}, maxItems={max_items})..."
        )

        pushed = 0
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            source_url = await download_zip(tmp_path)
            Actor.log.info(
                f"Downloaded BSEE raw data file ({os.path.getsize(tmp_path)} bytes) "
                f"from {source_url}."
            )
            with zipfile.ZipFile(tmp_path) as zf:
                well_rows = read_member(zf, WELL_FILE_SUFFIX)
                completion_rows = read_member(zf, COMPLETION_FILE_SUFFIX)
            Actor.log.info(
                f"Source file: {len(well_rows)} well records, "
                f"{len(completion_rows)} completion records."
            )
            completion_index = build_completion_index(completion_rows)

            scanned = 0
            for row in well_rows:
                if pushed >= max_items:
                    break
                item = build_item(
                    row,
                    completion_index.get(clean_str(row["API_WELL_NUMBER"])),
                    source_url,
                )
                if not item["api_well_number"]:
                    continue
                scanned += 1
                if item["region_code"] not in region_codes:
                    continue
                if area_code and item["surface_area_code"] != area_code:
                    continue
                if operator_contains and operator_contains not in item["operator_name"].lower():
                    continue
                if status_filter and item["borehole_status_code"] not in status_filter:
                    continue
                charge_result = await Actor.push_data(
                    item, charged_event_name="well-record"
                )
                pushed += 1
                if charge_result and getattr(
                    charge_result, "event_charge_limit_reached", False
                ):
                    Actor.log.info("User spending limit reached. Stopping gracefully.")
                    await Actor.exit()
                    return
            Actor.log.info(f"Scanned {scanned} well records.")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if pushed == 0:
            Actor.log.warning("No matching wells found for the selected filters.")
        else:
            Actor.log.info(
                f"Run completed successfully. Total normalized wells saved: {pushed}"
            )
