# src/search/google_cse.py
from __future__ import annotations
import os
import requests
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

GOOGLE_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"
ENV_GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ENV_GOOGLE_CX_ID = os.getenv("GOOGLE_CX_ID")


def google_search(
    query: str,
    days: Optional[int] = None,
    num: int = 10,
    pages: int = 1,
    domains: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    cx_id: Optional[str] = None,
    dedupe: bool = True,
) -> List[Dict[str, Any]]:
    """
    Google Programmable Search with pagination and optional domain scoping.
    - num: number of results per page (max 10 by API)
    - pages: number of pages to fetch (start param increments by 10)
    - domains: list of domains to include via site: filters
    """
    key = api_key or ENV_GOOGLE_API_KEY
    cx = cx_id or ENV_GOOGLE_CX_ID

    if not key or not cx:
        return []

    scope_query = query
    if domains:
        site_group = " OR ".join([f"site:{d}" for d in domains])
        scope_query = f"({site_group}) {query}"

    all_items: List[Dict[str, Any]] = []
    seen_links: set[str] = set()
    seen_titles: set[str] = set()
    for page in range(max(pages, 1)):
        start = page * min(max(num, 1), 10) + 1
        params = {
            "key": key,
            "cx": cx,
            "q": scope_query,
            "num": min(max(num, 1), 10),
            "start": start,
        }
        if days is not None:
            params["dateRestrict"] = f"d{int(days)}"

        r = requests.get(GOOGLE_ENDPOINT, params=params, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        items = data.get("items", []) or []
        for item in items:
            if not dedupe:
                all_items.append(item)
                continue
            link = _normalize_link(item.get("link", ""))
            title = (item.get("title") or "").strip().lower()
            if link and link in seen_links:
                continue
            if title and title in seen_titles:
                continue
            if link:
                seen_links.add(link)
            if title:
                seen_titles.add(title)
            all_items.append(item)
        if not items or len(items) < params["num"]:
            break

    return all_items


def _normalize_link(link: str) -> str:
    if not link:
        return ""
    parsed = urlparse(link)
    clean = parsed._replace(query="", fragment="")
    return urlunparse(clean).rstrip("/")
