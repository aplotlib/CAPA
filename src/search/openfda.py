# src/search/openfda.py
from __future__ import annotations
import requests
from datetime import date
from typing import Any, Dict, List

DEVICE_RECALL_ENDPOINT = "https://api.fda.gov/device/recall.json"
DEVICE_ENF_ENDPOINT    = "https://api.fda.gov/device/enforcement.json"

def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")

def _openfda(endpoint: str, search: str, limit: int = 100) -> List[Dict[str, Any]]:
    params = {"search": search, "limit": min(max(limit, 1), 1000)}
    r = requests.get(endpoint, params=params, timeout=30)
    # openFDA returns 404 when no results; treat as empty.
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json().get("results", []) or []

def search_device_recall(product_name: str, start: date, end: date, limit: int = 100):
    # Match product text + date window (report_date is a common choice; fallback to recall_initiation_date if needed)
    s = (
        f'(product_description:"{product_name}" OR reason_for_recall:"{product_name}" OR recalling_firm:"{product_name}")'
        f" AND report_date:[{_yyyymmdd(start)} TO {_yyyymmdd(end)}]"
    )
    return _openfda(DEVICE_RECALL_ENDPOINT, s, limit)

def search_device_enforcement(product_name: str, start: date, end: date, limit: int = 100):
    s = (
        f'(product_description:"{product_name}" OR reason_for_recall:"{product_name}" OR recalling_firm:"{product_name}")'
        f" AND report_date:[{_yyyymmdd(start)} TO {_yyyymmdd(end)}]"
    )
    return _openfda(DEVICE_ENF_ENDPOINT, s, limit)
