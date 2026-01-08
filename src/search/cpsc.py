# src/search/cpsc.py
from __future__ import annotations
import requests
from datetime import date
from typing import Any, Dict, List

CPSC_ENDPOINT = "https://www.saferproducts.gov/RestWebServices/Recall"

def cpsc_search(product_name: str, start: date, end: date, limit: int = 200) -> List[Dict[str, Any]]:
    params = {
        "format": "json",
        "ProductName": product_name,
        "RecallDateStart": start.isoformat(),  # YYYY-MM-DD
        "RecallDateEnd": end.isoformat(),
    }
    try:
        r = requests.get(CPSC_ENDPOINT, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException:
        return []
    # API returns a list of recalls
    if isinstance(data, list):
        return data[:limit]
    return []
