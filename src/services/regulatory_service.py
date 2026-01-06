import os
import re
from datetime import datetime, date
from typing import List, Optional

import pandas as pd
import requests
import streamlit as st

from src.search.google_cse import google_search
from src.services.adverse_event_service import AdverseEventService

# Try to import BeautifulSoup for scraping, fallback to regex if missing
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

class RegulatoryService:
    """
    Unified Regulatory Intelligence Engine.
    Integrates OpenFDA, CPSC, and Google Custom Search (Global Web/Regulators).
    Includes Agentic capabilities to visit and verify links.
    """
    
    # Configuration
    FDA_BASE = "https://api.fda.gov"
    CPSC_BASE = "https://www.saferproducts.gov/RestWebServices/Recall"
    GOOGLE_URL = "https://customsearch.googleapis.com/customsearch/v1"

    # Targeted Domains for "Regulatory" Search Category by Region
    REGIONAL_DOMAINS = {
        "US": [
            "fda.gov",
            "openfda.gov",
            "saferproducts.gov",
            "cpsc.gov",
            "cdc.gov",
        ],
        "UK": [
            "gov.uk",
            "mhra.gov.uk",
            "nhs.uk",
        ],
        "EU": [
            "europa.eu",
            "ema.europa.eu",
            "ec.europa.eu",
            "echa.europa.eu",
        ],
        "LATAM": [
            "anvisa.gov.br",
            "cofepris.gob.mx",
            "invima.gov.co",
            "anmat.gob.ar",
            "minsalud.gov.co",
        ],
        "APAC": [
            "tga.gov.au",
            "pmda.go.jp",
            "hsa.gov.sg",
        ],
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
        "defibrillator": ["aed", "automated external defibrillator", "icd", "implantable cardioverter defibrillator"],
        "infusion pump": ["iv pump", "syringe pump", "intravenous pump"],
        "insulin pump": ["diabetes pump", "csii pump"],
        "ventilator": ["respirator", "mechanical ventilator"],
    }

    @staticmethod
    def search_all_sources(
        query_term: str,
        regions: list = None,
        start_date=None,
        end_date=None,
        limit: int = 100,
        mode: str = "fast",
        ai_service=None,
        manufacturer: Optional[str] = None,
        vendor_only: bool = False,
        include_sanctions: bool = True,
    ) -> tuple[pd.DataFrame, dict]:
        """
        Main entry point.
        mode: 'fast' (APIs + Snippets) or 'powerful' (Scrape + AI Verify)
        """
        results = []
        status_log = {}

        # Legacy positional safeguard (some callers passed dates as 2nd/3rd args)
        if regions is not None and not isinstance(regions, list) and isinstance(regions, (date, datetime)):
            if isinstance(start_date, (date, datetime)):
                end_date = start_date
            start_date = regions
            regions = None

        if regions is None:
            regions = ["US", "EU", "UK", "LATAM", "APAC"]

        manufacturer = (manufacturer or "").strip()
        query_term = (query_term or "").strip()
        if not query_term and not manufacturer:
            return pd.DataFrame(), {"Error": 0}

        expanded_terms = RegulatoryService._expand_terms(query_term)
        if not expanded_terms and manufacturer:
            expanded_terms = [manufacturer]

        # --- 1. OFFICIAL APIs (Fast & Structured) ---
        if not vendor_only:
            fda_enf = RegulatoryService._fetch_openfda_enforcement(expanded_terms, limit, start_date, end_date, manufacturer)
            results.extend(fda_enf)
            status_log["FDA Enforcement"] = len(fda_enf)

            fda_recalls = RegulatoryService._fetch_openfda_device_recalls(expanded_terms, limit, start_date, end_date, manufacturer)
            results.extend(fda_recalls)
            status_log["FDA Recalls"] = len(fda_recalls)

            maude_service = AdverseEventService()
            maude_hits = maude_service.search_events(query_term, start_date, end_date, limit=20)
            results.extend(maude_hits)
            status_log["FDA MAUDE"] = len(maude_hits)

            cpsc_hits = RegulatoryService._fetch_cpsc(query_term, start_date, end_date)
            results.extend(cpsc_hits)
            status_log["CPSC"] = len(cpsc_hits)

        # --- 2. GOOGLE PROGRAMMABLE SEARCH (Global Coverage) ---
        if not vendor_only:
            reg_hits = RegulatoryService._search_regional_web(expanded_terms, regions, manufacturer)
            results.extend(reg_hits)
            status_log["Global Regulators"] = len(reg_hits)

            media_subject = query_term or manufacturer or "medical device"
            media_hits = RegulatoryService._google_search(
                query=f'"{media_subject}" (recall OR death OR lawsuit OR injury OR scandal OR safety alert)',
                category="Media",
                domains=None,
                pages=3,
                manufacturer=manufacturer,
            )
            results.extend(media_hits)
            status_log["Global Media"] = len(media_hits)

        # --- 3. Manufacturer / Enforcement / Sanctions ---
        if manufacturer:
            vendor_hits = RegulatoryService._search_manufacturer(manufacturer, regions, include_sanctions)
            results.extend(vendor_hits)
            status_log["Manufacturer Actions"] = len(vendor_hits)

        # --- 4. POWERFUL MODE: AGENTIC VERIFICATION ---
        if mode == "powerful" and ai_service:
            print(f"🕵️‍♂️ Agent entering Deep Scan mode for {len(results)} records...")
            verified_results = []
            for item in results:
                if "Google" in item.get("Source", ""):
                    verified_item = RegulatoryService._agent_visit_and_verify(item, query_term or manufacturer, ai_service)
                    if verified_item:
                        verified_results.append(verified_item)
                else:
                    verified_results.append(item)
            results = verified_results
            status_log["Agent Filtered"] = len(results)

        # --- 5. Final Processing ---
        df = pd.DataFrame(results)
        if not df.empty:
            df = df.drop_duplicates(subset=["Link", "ID"], keep="first")
            for col in ["Product", "Firm", "Reason", "Source", "Link", "Risk_Level", "Date"]:
                if col not in df.columns:
                    df[col] = "N/A"

            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.sort_values(by="Date", ascending=False)
                df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

        return df, status_log

    # =========================================================================
    # HELPER UTILITIES
    # =========================================================================
    @staticmethod
    def _expand_terms(term: str) -> List[str]:
        if not term:
            return []
        terms = {term}
        lower = term.lower()
        for key, synonyms in RegulatoryService.SYNONYM_MAP.items():
            if key in lower or lower in synonyms:
                terms.update(synonyms)
                terms.add(key)
        return list(terms)

    @staticmethod
    def _risk_from_text(text: str) -> str:
        lowered = (text or "").lower()
        if any(k in lowered for k in ["class i", "death", "serious injury", "urgent", "ban", "sanction"]):
            return "High"
        if any(k in lowered for k in ["class ii", "warning", "enforcement", "investigation"]):
            return "Medium"
        return "Low"

    @staticmethod
    def _search_regional_web(terms: List[str], regions: List[str], manufacturer: str) -> list:
        out = []
        for t in terms:
            base_query = f'"{t}" (recall OR safety alert OR enforcement OR warning OR field safety notice OR FSN)'
            if manufacturer:
                base_query += f' "{manufacturer}"'
            for region in regions:
                domains = RegulatoryService.REGIONAL_DOMAINS.get(region, [])
                if not domains:
                    continue
                out.extend(
                    RegulatoryService._google_search(
                        query=base_query,
                        category=f"{region} Regulators",
                        domains=domains,
                        pages=3,
                        manufacturer=manufacturer,
                    )
                )
        return out

    @staticmethod
    def _search_manufacturer(manufacturer: str, regions: List[str], include_sanctions: bool) -> list:
        out = []
        if not manufacturer:
            return out

        enforcement_query = f'"{manufacturer}" (enforcement OR warning letter OR recall OR inspection OR import alert OR consent decree)'
        sanction_query = f'"{manufacturer}" (sanction OR denied OR restricted OR prohibited OR debarment)'

        for region in regions:
            domains = RegulatoryService.REGIONAL_DOMAINS.get(region, [])
            out.extend(
                RegulatoryService._google_search(
                    query=enforcement_query,
                    category=f"{region} Manufacturer",
                    domains=domains,
                    pages=2,
                    manufacturer=manufacturer,
                )
            )

        if include_sanctions:
            out.extend(
                RegulatoryService._google_search(
                    query=sanction_query,
                    category="Sanctions / Watchlists",
                    domains=RegulatoryService.SANCTIONS_DOMAINS,
                    pages=2,
                    manufacturer=manufacturer,
                )
            )
        return out

    # =========================================================================
    # GOOGLE SEARCH INTEGRATION
    # =========================================================================
    @staticmethod
    def _google_search(query: str, category: str, domains: list = None, num: int = 10, pages: int = 2, manufacturer: str = "") -> list:
        """
        Executes a search using the configured Google Custom Search JSON API.
        """
        api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("google_api_key") or os.getenv("GOOGLE_API_KEY")
        cx_id = st.secrets.get("GOOGLE_CX_ID") or st.secrets.get("google_cx_id") or os.getenv("GOOGLE_CX_ID")

        if not api_key or not cx_id:
            print("⚠️ Missing Google API Keys. Skipping Web Search.")
            return []

        items = google_search(query, num=num, pages=pages, domains=domains, api_key=api_key, cx_id=cx_id)

        out = []
        for item in items:
            snippet = item.get('snippet', '')
            title = item.get('title', '')
            link = item.get('link')
            risk_level = RegulatoryService._risk_from_text(f"{title} {snippet}")
            product_term = query.split('"')[1] if '"' in query else query
            firm = item.get('displayLink', 'Web Source')
            if manufacturer and manufacturer.lower() in snippet.lower():
                firm = manufacturer

            out.append({
                "Source": f"{category} (Google)",
                "Date": item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time", "Recent"),
                "Product": product_term,
                "Description": title,
                "Reason": snippet,
                "Firm": firm,
                "ID": link,
                "Link": link,
                "Status": "Public Web",
                "Risk_Level": risk_level
            })
        return out

    # =========================================================================
    # AGENTIC CAPABILITIES (Scraping & Verification)
    # =========================================================================
    @staticmethod
    def _agent_visit_and_verify(item: dict, query_term: str, ai_service) -> dict:
        """
        Visits the URL, scrapes content, and asks AI if it's relevant.
        Returns the updated item (with AI summary) or None if irrelevant.
        """
        url = item.get('Link')
        if not url: return item

        # 1. Scrape Content
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            resp = requests.get(url, headers=headers, timeout=5)
            
            if resp.status_code != 200:
                return item # Keep original if we can't scrape

            text_content = ""
            if BeautifulSoup:
                soup = BeautifulSoup(resp.content, 'html.parser')
                # Remove scripts and styles
                for script in soup(["script", "style", "nav", "footer"]):
                    script.extract()
                text_content = soup.get_text(separator=' ')
            else:
                # Fallback Regex Stripper
                text_content = re.sub('<[^<]+?>', ' ', resp.text)
            
            # Truncate for Token Limits (approx 1500 words)
            text_content = " ".join(text_content.split())[:8000]

        except Exception:
            return item # Return original on scrape error

        # 2. AI Verification
        # We define a prompt to check if this page is actually about the product and a risk
        try:
            prompt = f"""
            I am researching: "{query_term}"
            I found this webpage content:
            "{text_content}..."
            
            Task:
            1. Is this page discussing a recall, safety alert, lawsuit, or negative quality event related to "{query_term}"?
            2. If YES, summarize the specific issue in 1 sentence.
            3. If NO (it's an ad, unrelated product, or generic home page), return "IRRELEVANT".
            
            Return JSON: {{ "is_relevant": true/false, "summary": "..." }}
            """
            
            # Using the fast model for speed
            analysis = ai_service._generate_json(prompt, system_instruction="You are a Regulatory filter.")
            
            if analysis.get("is_relevant") is True:
                item["Reason"] = f"✅ VERIFIED: {analysis.get('summary')}"
                item["AI_Verified"] = True
                return item
            else:
                return None # Filter out
                
        except Exception:
            return item # Keep if AI fails to decide

    # =========================================================================
    # STRUCTURED API HELPERS
    # =========================================================================
    @staticmethod
    def _build_openfda_query(term: str, manufacturer: str) -> str:
        clean_term = "+".join(term.strip().replace('"', '').split())
        query_parts = [
            f'(product_description:"{clean_term}" OR reason_for_recall:"{clean_term}" OR recalling_firm:"{clean_term}")'
        ]
        if manufacturer:
            query_parts.append(f'(recalling_firm:"{"+".join(manufacturer.split())}")')
        return " AND ".join(query_parts)

    @staticmethod
    def _wrap_openfda_result(item: dict, source: str) -> dict:
        cls = item.get("classification", "")
        risk = "High" if "Class I" in cls or "Class 1" in cls else "Medium" if "Class II" in cls else "Low"
        link = item.get("url") or f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={item.get('event_id', '')}"
        if not link:
            link = f"https://open.fda.gov/apis/device/enforcement/#{item.get('recall_number', '')}"
        return {
            "Source": source,
            "Date": item.get("recall_initiation_date") or item.get("report_date"),
            "Product": item.get("product_description"),
            "Description": item.get("product_description"),
            "Reason": item.get("reason_for_recall"),
            "Firm": item.get("recalling_firm"),
            "ID": item.get("recall_number") or item.get("event_id"),
            "Link": link,
            "Status": item.get("status"),
            "Risk_Level": risk,
            "Recall_Class": cls or "Unknown",
        }

    @staticmethod
    def _fetch_openfda_enforcement(terms: List[str], limit: int, start=None, end=None, manufacturer: str = "") -> list:
        out = []
        url = f"{RegulatoryService.FDA_BASE}/device/enforcement.json"
        for term in terms:
            date_q = ""
            if start and end:
                s_str = start.strftime("%Y-%m-%d") if hasattr(start, 'strftime') else str(start)
                e_str = end.strftime("%Y-%m-%d") if hasattr(end, 'strftime') else str(end)
                date_q = f' AND recall_initiation_date:[{s_str} TO {e_str}]'

            params = {
                "search": RegulatoryService._build_openfda_query(term, manufacturer) + date_q,
                "limit": max(1, min(limit, 100)),
                "sort": "recall_initiation_date:desc",
            }
            try:
                res = requests.get(url, params=params, timeout=10)
                data = res.json()
                if "results" in data:
                    for item in data["results"]:
                        out.append(RegulatoryService._wrap_openfda_result(item, "FDA Device Enforcement"))
            except Exception as e:
                print(f"OpenFDA Enforcement error for term '{term}': {e}")
        return out

    @staticmethod
    def _fetch_openfda_device_recalls(terms: List[str], limit: int, start=None, end=None, manufacturer: str = "") -> list:
        out = []
        url = f"{RegulatoryService.FDA_BASE}/device/recall.json"
        for term in terms:
            date_q = ""
            if start and end:
                s_str = start.strftime("%Y-%m-%d") if hasattr(start, 'strftime') else str(start)
                e_str = end.strftime("%Y-%m-%d") if hasattr(end, 'strftime') else str(end)
                date_q = f' AND report_date:[{s_str} TO {e_str}]'

            params = {
                "search": RegulatoryService._build_openfda_query(term, manufacturer) + date_q,
                "limit": max(1, min(limit, 100)),
                "sort": "report_date:desc",
            }
            try:
                res = requests.get(url, params=params, timeout=10)
                data = res.json()
                if "results" in data:
                    for item in data["results"]:
                        out.append(RegulatoryService._wrap_openfda_result(item, "FDA Device Recall"))
            except Exception as e:
                print(f"OpenFDA Device Recall error for term '{term}': {e}")
        return out

    @staticmethod
    def _fetch_cpsc(term: str, start=None, end=None) -> list:
        params = {'format': 'json', 'RecallTitle': term}
        if start and end:
            params['RecallDateStart'] = start.strftime("%Y-%m-%d") if hasattr(start, 'strftime') else str(start)
            params['RecallDateEnd'] = end.strftime("%Y-%m-%d") if hasattr(end, 'strftime') else str(end)

        out = []
        try:
            res = requests.get(RegulatoryService.CPSC_BASE, params=params, timeout=8)
            if res.status_code == 200:
                items = res.json()
                if isinstance(items, list):
                    for item in items:
                        reason = item.get("Description", "See Link")
                        risk = RegulatoryService._risk_from_text(reason)
                        out.append({
                            "Source": "CPSC",
                            "Date": item.get("RecallDate"),
                            "Product": item.get("Title"),
                            "Description": item.get("Title"),
                            "Reason": reason,
                            "Firm": item.get("Products", [{}])[0].get("Name", "See Details") if isinstance(item.get("Products"), list) else "See Details",
                            "ID": str(item.get("RecallID")),
                            "Link": item.get("URL"),
                            "Status": "Public",
                            "Risk_Level": risk
                        })
        except Exception as e:
            print(f"CPSC search error: {e}")
        return out
