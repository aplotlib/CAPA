from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable, List, Optional
from urllib.parse import urlparse, urlunparse
import xml.etree.ElementTree as ET

import requests


@dataclass(frozen=True)
class AgencyFeed:
    name: str
    region: str
    url: str


FEEDS: List[AgencyFeed] = [
    AgencyFeed("UK MHRA Alerts", "UK", "https://www.gov.uk/drug-device-alerts.atom"),
    AgencyFeed("EU EMA News", "EU", "https://www.ema.europa.eu/en/rss.xml"),
    AgencyFeed("Canada Health Recalls", "CA", "https://recalls-rappels.canada.ca/en/rss.xml"),
    AgencyFeed(
        "Brazil ANVISA Alerts",
        "LATAM",
        "https://www.gov.br/anvisa/pt-br/assuntos/fiscalizacao-e-monitoramento/monitoramento/alertas/alertas-de-seguranca/rss",
    ),
]


def fetch_agency_alerts(terms: Iterable[str], regions: Iterable[str], limit: int = 50) -> List[dict]:
    selected_regions = {r.upper() for r in regions}
    normalized_terms = _normalize_terms(terms)
    if not normalized_terms:
        return []

    results: List[dict] = []
    seen_links: set[str] = set()
    for feed in FEEDS:
        if feed.region.upper() not in selected_regions:
            continue
        remaining = limit - len(results)
        if remaining <= 0:
            break
        items = _fetch_feed(feed)
        for item in items:
            if len(results) >= limit:
                break
            if not _matches_terms(item, normalized_terms):
                continue
            link = item.link or ""
            normalized_link = _normalize_link(link)
            if normalized_link in seen_links:
                continue
            seen_links.add(normalized_link)
            results.append(
                {
                    "Source": feed.name,
                    "Date": item.date_str,
                    "Product": item.title or "",
                    "Description": item.title or "",
                    "Reason": item.summary or "",
                    "Firm": feed.name,
                    "Model Info": "",
                    "ID": normalized_link or item.title or item.summary or "",
                    "Link": link,
                    "Status": "Published",
                    "Risk_Level": "High" if _looks_high_risk(item.title, item.summary) else "Medium",
                    "Matched_Term": item.matched_term,
                }
            )
    return results


def _normalize_terms(terms: Iterable[str]) -> List[str]:
    normalized = []
    for term in terms:
        cleaned = (term or "").strip().lower()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _matches_terms(item: "FeedItem", terms: List[str]) -> bool:
    haystack = f"{item.title} {item.summary}".lower()
    for term in terms:
        if term in haystack:
            item.matched_term = term
            return True
    return False


def _looks_high_risk(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    keywords = ["recall", "safety", "alert", "warning", "field safety", "withdrawal", "urgent", "class i"]
    return any(keyword in text for keyword in keywords)


def _fetch_feed(feed: AgencyFeed) -> List["FeedItem"]:
    try:
        response = requests.get(feed.url, timeout=12)
        response.raise_for_status()
    except requests.RequestException:
        return []

    content = response.content.strip()
    if not content.startswith(b"<"):
        return []

    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []

    items: List[FeedItem] = []
    if root.tag.endswith("feed"):
        items.extend(_parse_atom_feed(root))
    else:
        items.extend(_parse_rss_feed(root))
    return items


class FeedItem:
    def __init__(self, title: str, link: str, summary: str, date_str: str):
        self.title = title
        self.link = link
        self.summary = summary
        self.date_str = date_str
        self.matched_term = ""


def _parse_atom_feed(root: ET.Element) -> List[FeedItem]:
    items: List[FeedItem] = []
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = _text(entry.find("{http://www.w3.org/2005/Atom}title"))
        link = _atom_link(entry)
        summary = _text(entry.find("{http://www.w3.org/2005/Atom}summary")) or _text(
            entry.find("{http://www.w3.org/2005/Atom}content")
        )
        date_str = _format_date(_text(entry.find("{http://www.w3.org/2005/Atom}updated")))
        items.append(FeedItem(title, link, summary, date_str))
    return items


def _parse_rss_feed(root: ET.Element) -> List[FeedItem]:
    items: List[FeedItem] = []
    for item in root.findall(".//item"):
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        summary = _text(item.find("description"))
        date_str = _format_date(_text(item.find("pubDate")))
        items.append(FeedItem(title, link, summary, date_str))
    return items


def _atom_link(entry: ET.Element) -> str:
    link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
    if link_elem is None:
        return ""
    return link_elem.attrib.get("href", "")


def _text(element: Optional[ET.Element]) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _format_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return value


def _normalize_link(link: str) -> str:
    if not link:
        return ""
    parsed = urlparse(link)
    clean = parsed._replace(fragment="", query="")
    return urlunparse(clean).rstrip("/")
