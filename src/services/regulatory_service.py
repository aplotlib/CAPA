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
    Unified Regulatory Intelligence Engine.
    Integrates OpenFDA, CPSC, Google Custom Search (regulators), and Media.
    """

    REGIONAL_DOMAINS = {
        "US": ["fda.gov", "openfda.gov", "saferproducts.gov", "cpsc.gov", "cdc.gov"],
        "UK": ["gov.uk", "mhra.gov.uk", "nhs.uk"],
        "CA": ["canada.ca", "recalls-rappels.gc.ca", "healthcanada.gc.ca"],
        "EU": ["europa.eu", "ema.europa.eu", "ec.europa.eu", "echa.europa.eu"],
        "LATAM": ["anvisa.gov.br", "cofepris.gob.mx", "invima.gov.co", "minsalud.gov.co"],
        "APAC": ["tga.gov.au", "pmda.go.jp", "hsa.gov.sg"],
    }

    SANCTIONS_DOMAINS = [
        "treasury.gov",
        "hmt-sanctions.s3.eu-west-2.amazonaws.com",
        "ec.europa.eu",
        "un.org/securitycouncil",
    ]

    SYNONYM_MAP = {
        "bpm": ["blood pressure monitor", "bp monitor", "sphygmomanometer"],
        "blood pressure monitor": ["bpm", "bp monitor", "blood pressure machine"],
        "scooter": ["mobility scooter", "powered scooter", "electric scooter"],
        "pacemaker": ["cardiac pacemaker", "implantable pacemaker"],
        "defibrillator": [
            "aed",
            "automated external defibrillator",
            "icd",
            "implantable cardioverter defibrillator",
        ],
        "infusion pump": ["iv pump", "syringe pump", "intravenous pump"],
        "insulin pump": ["diabetes pump", "csii pump"],
        "ventilator": ["respirator", "mechanical ventilator"],
        "catheter": ["urinary catheter", "central line", "iv catheter"],
        "syringe": ["syringe", "pre-filled syringe", "prefilled syringe"],
        "glucometer": ["glucose meter", "blood glucose monitor"],
        "sterilizer": ["autoclave", "steam sterilizer"],
    }

    @classmethod
    def search_all_sources(
        cls,
        query_term: str,
        regions: Optional[List[str]] = None,
        start_date: Any = None,
        end_date: Any = None,
        limit: int = 100,
        mode: str = "fast",
        ai_service: Any = None,
        manufacturer: Optional[str] = None,
        vendor_only: bool = False,
        include_sanctions: bool = True,
        extra_terms: Optional[Sequence[str]] = None,
    ) -> tuple[pd.DataFrame, dict]:
        """
        Main entry point.
        mode: 'fast' (APIs + Structured) or 'powerful' (adds web/media coverage)
        """
        results: List[Dict[str, Any]] = []
        status_log: Dict[str, int] = {}

        regions = regions or ["US", "EU", "UK", "CA", "LATAM", "APAC"]
        query_term = (query_term or "").strip()
        manufacturer = (manufacturer or "").strip()
        if not query_term and not manufacturer:
            return pd.DataFrame(), {"Error": 0}

        start_dt = _as_date(start_date) or date.today().replace(year=date.today().year - DEFAULT_LOOKBACK_YEARS)
        end_dt = _as_date(end_date) or date.today()
        if start_dt > end_dt:
            start_dt, end_dt = end_dt, start_dt
        is_powerful = mode == "powerful"
        max_terms = 12 if is_powerful else 10

        terms = cls.prepare_terms(query_term, manufacturer, max_terms=max_terms, extra_terms=extra_terms)

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
    def search_all_sources_safe(cls, **kwargs: Any) -> tuple[pd.DataFrame, dict]:
        try:
            return cls.search_all_sources(**kwargs)
        except TypeError as exc:
            if "extra_terms" in str(exc):
                kwargs.pop("extra_terms", None)
                return cls.search_all_sources(**kwargs)
            raise

    @classmethod
    def prepare_terms(
        cls,
        query_term: str,
        manufacturer: str,
        max_terms: int = 8,
        extra_terms: Optional[Sequence[str]] = None,
    ) -> List[str]:
        base_terms = []
        if query_term:
            base_terms.append(query_term)
        if manufacturer:
            base_terms.append(manufacturer)
        if query_term and manufacturer:
            base_terms.append(f"{manufacturer} {query_term}")
            base_terms.append(f"{manufacturer} {query_term} recall")
        if query_term and extra_terms:
            for keyword in _safe_list(extra_terms):
                base_terms.append(f"{query_term} {keyword}")

        expanded: List[str] = []
        for term in base_terms:
            expanded.extend(cls._expand_terms(term))

        deduped = cls._dedupe_terms(expanded)
        return deduped[:max_terms]

    @classmethod
    def _expand_terms(cls, term: str) -> List[str]:
        if not term:
            return []
        normalized = term.strip()
        lower_term = normalized.lower()
        expanded = {normalized}

        if lower_term in cls.SYNONYM_MAP:
            expanded.update(cls.SYNONYM_MAP[lower_term])

        for key, synonyms in cls.SYNONYM_MAP.items():
            if key in lower_term:
                expanded.update(synonyms)

        if "-" in normalized:
            expanded.add(normalized.replace("-", " "))
        if " " in normalized:
            expanded.add(normalized.replace(" ", "-"))

        return [t for t in expanded if t]

    @staticmethod
    def _dedupe_terms(terms: Sequence[str]) -> List[str]:
        seen = set()
        out = []
        for term in terms:
            key = term.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(term.strip())
        return out

    @classmethod
    def _fetch_openfda_device_recalls(cls, terms: Sequence[str], limit: int, start: date, end: date) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for term in terms:
            hits = search_device_recall(term, start, end, limit=limit)
            for hit in hits:
                recall_number = hit.get("recall_number", "")
                reason = hit.get("reason_for_recall", "")
                classification = hit.get("classification", "")
                record = {
                    "Source": "FDA Device Recall",
                    "Date": hit.get("report_date", ""),
                    "Product": hit.get("product_description", ""),
                    "Description": hit.get("product_description", ""),
                    "Reason": reason,
                    "Firm": hit.get("recalling_firm", ""),
                    "Model Info": hit.get("model_number", "") or hit.get("code_info", ""),
                    "ID": recall_number,
                    "Link": cls._openfda_link("recall", recall_number),
                    "Status": hit.get("status", ""),
                    "Risk_Level": cls._risk_from_classification(classification),
                    "Matched_Term": term,
                }
                results.append(record)
            if len(results) >= limit:
                break
        return results

    @classmethod
    def _fetch_openfda_enforcement(cls, terms: Sequence[str], limit: int, start: date, end: date) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for term in terms:
            hits = search_device_enforcement(term, start, end, limit=limit)
            for hit in hits:
                recall_number = hit.get("recall_number", "")
                reason = hit.get("reason_for_recall", "")
                classification = hit.get("classification", "")
                record = {
                    "Source": "FDA Enforcement",
                    "Date": hit.get("report_date", ""),
                    "Product": hit.get("product_description", ""),
                    "Description": hit.get("product_description", ""),
                    "Reason": reason,
                    "Firm": hit.get("recalling_firm", ""),
                    "Model Info": hit.get("model_number", "") or hit.get("code_info", ""),
                    "ID": recall_number,
                    "Link": cls._openfda_link("enforcement", recall_number),
                    "Status": hit.get("status", ""),
                    "Risk_Level": cls._risk_from_classification(classification),
                    "Matched_Term": term,
                }
                results.append(record)
            if len(results) >= limit:
                break
        return results

    @classmethod
    def _fetch_cpsc(cls, terms: Sequence[str], start: date, end: date, limit: int = 100) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for term in terms:
            hits = cpsc_search(term, start, end, limit=limit)
            for hit in hits:
                record = {
                    "Source": "CPSC Recall",
                    "Date": hit.get("RecallDate", ""),
                    "Product": hit.get("Title", ""),
                    "Description": hit.get("Title", ""),
                    "Reason": hit.get("Description", ""),
                    "Firm": hit.get("Manufacturer", ""),
                    "Model Info": hit.get("ProductID", ""),
                    "ID": hit.get("RecallID", ""),
                    "Link": hit.get("URL", ""),
                    "Status": hit.get("Status", ""),
                    "Risk_Level": "Medium",
                    "Matched_Term": term,
                }
                results.append(record)
            if len(results) >= limit:
                break
        return results

    @classmethod
    def _search_sanctions(cls, manufacturer: str, limit: int = 50) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for domain in cls.SANCTIONS_DOMAINS:
            results.extend(cls._google_search(f'"{manufacturer}" site:{domain}', category="Sanctions", num=limit))
        return results[:limit]

    @classmethod
    def _search_ofac(cls, manufacturer: str, limit: int = 50) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        url = "https://www.treasury.gov/ofac/downloads/sdn.csv"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            lines = response.text.splitlines()
        except Exception:
            return results

        for line in lines[1:]:
            fields = line.split(",")
            name = fields[1] if len(fields) > 1 else ""
            if manufacturer.lower() in name.lower():
                link = "https://www.treasury.gov/ofac/downloads/sdn.csv"
                results.append(
                    {
                        "Source": "OFAC Sanctions",
                        "Date": "",
                        "Product": name,
                        "Description": name,
                        "Reason": "OFAC sanctions list match",
                        "Firm": name,
                        "Model Info": "",
                        "ID": f"OFAC:{name}",
                        "Link": link,
                        "Status": "Listed",
                        "Risk_Level": "High",
                        "Matched_Term": manufacturer,
                    }
                )
            if len(results) >= limit:
                break
        return results

    @classmethod
    def _search_media(cls, query_term: str, regions: Sequence[str]) -> List[Dict[str, Any]]:
        if not query_term:
            return []
        media_svc = MediaMonitoringService()
        results: List[Dict[str, Any]] = []
        for region in regions:
            results.extend(media_svc.search_media(query_term, limit=10, region=region))
        return results

    @classmethod
    def _search_regulatory_web(
        cls,
        terms: Sequence[str],
        regions: Sequence[str],
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        if not terms:
            return []
        results: List[Dict[str, Any]] = []
        per_query_limit = max(1, min(10, limit // max(1, len(terms))))
        for term in terms:
            for region in regions:
                domains = cls.REGIONAL_DOMAINS.get(region, [])
                for domain in domains:
                    query = f"\"{term}\" site:{domain}"
                    results.extend(
                        cls._google_search(
                            query,
                            category=f"Regulatory Web ({region})",
                            num=per_query_limit,
                        )
                    )
                    if len(results) >= limit:
                        return results[:limit]
        return results[:limit]

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
            title = item.get("title") or snippet
            risk_level = RegulatoryService._risk_from_keywords(f"{title} {snippet}")
            records.append(
                {
                    "Source": source_label,
                    "Date": "",
                    "Product": title,
                    "Description": title,
                    "Reason": snippet,
                    "Firm": item.get("displayLink") or "",
                    "Model Info": "",
                    "ID": link,
                    "Link": link,
                    "Status": "Published",
                    "Risk_Level": risk_level,
                    "Matched_Term": matched_term,
                }
            )
        return records

    @staticmethod
    def _risk_from_keywords(text: str) -> str:
        if not text:
            return "Medium"
        normalized = text.lower()
        high_risk_terms = [
            "class i",
            "class ii",
            "class iii",
            "recall",
            "safety alert",
            "field safety",
            "warning",
            "urgent",
        ]
        if any(term in normalized for term in high_risk_terms):
            return "High"
        return "Medium"

    @staticmethod
    def _risk_from_classification(classification: str) -> str:
        normalized = classification.strip().upper().replace("CLASS ", "")
        if normalized == "I":
            return "High"
        if normalized == "II":
            return "Medium"
        if normalized == "III":
            return "Low"
        return "Medium"

    @staticmethod
    def _openfda_link(category: str, recall_number: str) -> str:
        if not recall_number:
            return ""
        endpoint = "device/recall" if category == "recall" else "device/enforcement"
        return f"https://api.fda.gov/{endpoint}.json?search=recall_number:{recall_number}"

    @staticmethod
    def _dedupe(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        id_series = df["ID"].fillna("").astype(str) if "ID" in df.columns else pd.Series("", index=df.index)
        link_series = df["Link"].fillna("").astype(str) if "Link" in df.columns else pd.Series("", index=df.index)
        product_series = df["Product"].fillna("").astype(str) if "Product" in df.columns else pd.Series("", index=df.index)

        dedupe_key = id_series.where(id_series != "", link_series.where(link_series != "", product_series))
        df["__dedupe_key"] = dedupe_key
        df = df.drop_duplicates(subset=["Source", "__dedupe_key"])
        df.drop(columns="__dedupe_key", inplace=True)
        return df

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "Manufacturer" not in df.columns and "Firm" in df.columns:
            df["Manufacturer"] = df["Firm"]
        if "Model Info" not in df.columns and "Model_Numbers" in df.columns:
            df["Model Info"] = df["Model_Numbers"]
        for col in ["Date", "Product", "Reason", "Firm", "Link"]:
            if col not in df.columns:
                df[col] = ""
        return df
