from __future__ import annotations

"""Regulatory data aggregation and normalization."""

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.search.cpsc import cpsc_search
from src.search.google_cse import google_search
from src.search.openfda import search_device_enforcement, search_device_recall
from src.services.adverse_event_service import AdverseEventService
from src.services.media_service import MediaMonitoringService


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _safe_list(items: Optional[Iterable[str]]) -> List[str]:
    return [str(x).strip() for x in items or [] if str(x).strip()]


DEFAULT_LOOKBACK_YEARS = 3


class RegulatoryService:
    """
@@ -107,50 +109,53 @@ class RegulatoryService:

        if not vendor_only:
            fda_recalls = cls._fetch_openfda_device_recalls(terms, limit, start_dt, end_dt)
            results.extend(fda_recalls)
            status_log["FDA Device Recalls"] = len(fda_recalls)

            fda_enf = cls._fetch_openfda_enforcement(terms, limit, start_dt, end_dt)
            results.extend(fda_enf)
            status_log["FDA Enforcement"] = len(fda_enf)

            maude_service = AdverseEventService()
            maude_hits = maude_service.search_events(query_term or manufacturer, start_dt, end_dt, limit=30)
            for item in maude_hits:
                item["Matched_Term"] = query_term or manufacturer
            results.extend(maude_hits)
            status_log["FDA MAUDE"] = len(maude_hits)

            cpsc_hits = cls._fetch_cpsc(terms, start_dt, end_dt, limit=limit)
            results.extend(cpsc_hits)
            status_log["CPSC Recalls"] = len(cpsc_hits)

        if include_sanctions and manufacturer:
            sanctions_hits = cls._search_sanctions(manufacturer, limit=limit)
            results.extend(sanctions_hits)
            status_log["Sanctions & Watchlists"] = len(sanctions_hits)
            ofac_hits = cls._search_ofac(manufacturer, limit=limit)
            results.extend(ofac_hits)
            status_log["OFAC Sanctions"] = len(ofac_hits)

        if is_powerful:
            web_hits = cls._search_regulatory_web(terms, regions, limit=limit)
            results.extend(web_hits)
            status_log["Regulatory Web"] = len(web_hits)

            media_hits = cls._search_media(query_term or manufacturer, regions)
            results.extend(media_hits)
            status_log["Media Signals"] = len(media_hits)

        df = pd.DataFrame(results)
        if df.empty:
            return df, status_log

        df = cls._dedupe(df)
        df = cls._normalize_columns(df)
        df.sort_values(by="Date", ascending=False, inplace=True, ignore_index=True)
        return df, status_log

    @classmethod
    def prepare_terms(cls, query_term: str, manufacturer: str, max_terms: int = 8) -> List[str]:
        base_terms = []
        if query_term:
            base_terms.append(query_term)
        if manufacturer:
@@ -312,50 +317,135 @@ class RegulatoryService:
        return results

    @classmethod
    def _search_regulatory_web(
        cls,
        terms: Sequence[str],
        regions: Sequence[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        per_term_limit = max(5, min(limit, 10))
        for region in regions:
            domains = cls.REGIONAL_DOMAINS.get(region, [])
            for term in _safe_list(terms):
                query = f'"{term}" (recall OR warning OR safety alert OR enforcement)'
                hits = google_search(query, num=per_term_limit, pages=2, domains=domains)
                results.extend(cls._google_hits_to_records(hits, f"Regulatory Web ({region})", term))
        return results

    @classmethod
    def _search_sanctions(cls, manufacturer: str, limit: int) -> List[Dict[str, Any]]:
        query = f'"{manufacturer}" (sanction OR enforcement OR penalty OR debarment OR warning)'
        hits = google_search(query, num=min(limit, 10), pages=2, domains=cls.SANCTIONS_DOMAINS)
        return cls._google_hits_to_records(hits, "Sanctions & Watchlists", manufacturer)

    @classmethod
    def _search_ofac(cls, manufacturer: str, limit: int) -> List[Dict[str, Any]]:
        if not manufacturer:
            return []

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "CAPA-Regulatory-Agent/1.0 (+https://sanctionssearch.ofac.treas.gov/)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        base_url = "https://sanctionssearch.ofac.treas.gov"
        token = None
        try:
            landing = session.get(base_url, timeout=15)
            if landing.ok:
                soup = BeautifulSoup(landing.text, "lxml")
                token_input = soup.find("input", {"name": "__RequestVerificationToken"})
                if token_input and token_input.get("value"):
                    token = token_input["value"]
        except requests.RequestException:
            return []

        payload = {
            "searchValue": manufacturer,
            "searchType": "Name",
            "searchCriteria": "0",
            "searchTypeId": "0",
            "name": manufacturer,
        }
        if token:
            payload["__RequestVerificationToken"] = token

        endpoints = ["/Home/Search", "/Home/Search/"]
        html = None
        for endpoint in endpoints:
            try:
                response = session.post(f"{base_url}{endpoint}", data=payload, timeout=20)
                if response.ok and response.text:
                    html = response.text
                    break
            except requests.RequestException:
                continue

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")
        if not table:
            return []

        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        records: List[Dict[str, Any]] = []
        for row in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
            if not cells:
                continue
            row_data = dict(zip(headers, cells)) if headers else {}
            name = row_data.get("Name") or cells[0]
            programs = row_data.get("Program") or row_data.get("Programs") or ""
            sanctions_type = row_data.get("Type") or ""
            reason = " | ".join([x for x in [programs, sanctions_type] if x])
            link = base_url
            records.append(
                {
                    "Source": "OFAC Sanctions Search",
                    "Date": "",
                    "Product": name,
                    "Description": name,
                    "Reason": reason or "OFAC sanctions list match",
                    "Firm": name,
                    "Model Info": "",
                    "ID": f"OFAC:{name}",
                    "Link": link,
                    "Status": "Listed",
                    "Risk_Level": "High",
                    "Matched_Term": manufacturer,
                }
            )
            if len(records) >= limit:
                break
        return records

    @classmethod
    def _search_media(cls, query_term: str, regions: Sequence[str]) -> List[Dict[str, Any]]:
        if not query_term:
            return []
        media_svc = MediaMonitoringService()
        results: List[Dict[str, Any]] = []
        for region in regions:
            results.extend(media_svc.search_media(query_term, limit=10, region=region))
        return results

    @staticmethod
    def _google_search(query: str, category: str = "Web Search", num: int = 10) -> List[Dict[str, Any]]:
        hits = google_search(query, num=min(max(num, 1), 10), pages=2)
        return RegulatoryService._google_hits_to_records(hits, category, query)

    @staticmethod
    def _google_hits_to_records(
        hits: Sequence[Dict[str, Any]],
        source_label: str,
        matched_term: str,
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for item in hits:
            link = item.get("link", "")
            snippet = item.get("snippet") or ""
