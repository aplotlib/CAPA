# src/search/google_cse.py
from __future__ import annotations
import requests
from typing import Any, Dict, List, Optional
from ..config import GOOGLE_API_KEY, GOOGLE_CX_ID

GOOGLE_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"

def google_search(query: str, days: Optional[int] = None, num: int = 10) -> List[Dict[str, Any]]:
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX_ID,
        "q": query,
        "num": min(max(num, 1), 10),
    }
    if days is not None:
        params["dateRestrict"] = f"d{int(days)}"

    r = requests.get(GOOGLE_ENDPOINT, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("items", []) or []
