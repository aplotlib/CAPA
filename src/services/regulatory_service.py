from __future__ import annotations
import re
import time
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from src.services.adverse_event_service import AdverseEventService
from src.services.media_service import MediaMonitoringService
from src.services.normalization import NormalizedRecord
from src.services.sanctions_service import SanctionsService
from src.utils import retry_with_backoff

class RegulatoryService:
    """
    Unified Regulatory Intelligence Engine.
    Integrates OpenFDA, global regulators, sanctions lists, and Google crawling.
    Normalizes all ingested content into a unified schema.
    """
    
    # Configuration
    FDA_BASE = "https://api.fda.gov"
    FDA_WARNING_LETTERS = "https://api.fda.gov/other/warningletters.json"
    CPSC_BASE = "https://www.saferproducts.gov/RestWebServices/Recall"
    GOOGLE_URL = "https://customsearch.googleapis.com/customsearch/v1"
    GOOGLE_NEWS_URL = "https://news.google.com/rss/search"

    # RSS/Feed-based endpoints (best-effort; gracefully handled if blocked)
    REGULATORY_FEEDS = [
        {
            "name": "UK MHRA Drug & Device Alerts",
            "jurisdiction": "UK",
            "url": "https://www.gov.uk/drug-device-alerts.atom",
            "product_type": "Drug/Device",
        },
        {
            "name": "EU Field Safety Notices",
            "jurisdiction": "EU",
            "url": "https://ec.europa.eu/tools/eudamed/api/announcements/rss",
            "product_type": "Device",
        },
        {
            "name": "WHO Medical Device/Drug Safety",
            "jurisdiction": "GLOBAL",
            "url": "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml",
            "product_type": "Global Health",
        },
        {
            "name": "PAHO Safety Bulletins",
            "jurisdiction": "LATAM",
            "url": "https://www.paho.org/en/rss-feeds",
            "product_type": "Global Health",
        },
        {
            "name": "ANVISA Alerts",
            "jurisdiction": "BR",
            "url": "https://www.gov.br/anvisa/pt-br/assuntos/alertas?set_language=en&cl=en/@@RSS",
            "product_type": "Drug/Device",
        },
        {
            "name": "INVIMA Alerts",
            "jurisdiction": "CO",
            "url": "https://www.invima.gov.co/en/rss",
            "product_type": "Drug/Device",
        },
        {
            "name": "COFEPRIS Alerts",
            "jurisdiction": "MX",
            "url": "https://www.gob.mx/cofepris/archivo/articulos?format=atom",
            "product_type": "Drug/Device",
        },
    ]

    # Targeted Domains for "Regulatory" Search Category
    REGULATORY_DOMAINS = [
        "gov.uk", "europa.eu", "anvisa.gov.br", "cofepris.gob.mx", 
        "hc-sc.gc.ca", "tga.gov.au", "pmda.go.jp", "swissmedic.ch",
        "invima.gov.co", "argentina.gob.ar/anmat"
    ]

    JURISDICTION_DOMAINS = {
        "EU": ["europa.eu", "ema.europa.eu", "ec.europa.eu"],
        "UK": ["gov.uk", "mhra.gov.uk"],
        "BR": ["anvisa.gov.br"],
        "CO": ["invima.gov.co"],
        "MX": ["cofepris.gob.mx"],
        "GLOBAL": ["who.int", "paho.org"],
    }

    SANCTIONS = SanctionsService()
    MEDIA = MediaMonitoringService()

    @staticmethod
    def search_all_sources(query_term: str, regions: list = None, start_date=None, end_date=None, limit: int = 100, mode: str = "fast", ai_service=None) -> tuple[pd.DataFrame, dict]:
        """
        Main entry point. 
        mode: 'fast' (APIs + Snippets) or 'powerful' (Scrape + AI Verify)
        """
        results = []
        status_log = {}
        
        if regions is None:
            regions = ["US", "EU", "UK", "LATAM", "APAC"]

        # --- 1. OFFICIAL APIs (Fast & Structured) ---
        fda_device_hits = RegulatoryService._fetch_openfda_smart(query_term, "device", limit, start_date, end_date)
        fda_drug_hits = RegulatoryService._fetch_openfda_smart(query_term, "drug", limit, start_date, end_date)
        warning_letters = RegulatoryService._fetch_warning_letters(query_term, limit)
        results.extend(fda_device_hits + fda_drug_hits + warning_letters)
        status_log["FDA Device/Drug"] = len(fda_device_hits) + len(fda_drug_hits)
        status_log["FDA Warning Letters"] = len(warning_letters)

        # MAUDE (Adverse Events)
        maude_service = AdverseEventService()
        maude_hits = maude_service.search_events(query_term, start_date, end_date, limit=20)
        results.extend(maude_hits)
        status_log["FDA MAUDE"] = len(maude_hits)

        # CPSC (Consumer Safety)
        cpsc_hits = RegulatoryService._fetch_cpsc(query_term, start_date, end_date)
        results.extend(cpsc_hits)
        status_log["CPSC"] = len(cpsc_hits)

        # --- 2. INTERNATIONAL REGULATORY FEEDS ---
        feed_hits = []
        for feed in RegulatoryService.REGULATORY_FEEDS:
            feed_hits.extend(RegulatoryService._fetch_rss_feed(feed, query_term))
        results.extend(feed_hits)
        status_log["Regulatory Feeds"] = len(feed_hits)

        # --- 3. GOOGLE PROGRAMMABLE SEARCH (Global Coverage) ---
        reg_query = f'"{query_term}" (recall OR safety OR warning OR alert OR field action)'
        reg_hits = RegulatoryService._google_search(reg_query, category="Regulatory", domains=RegulatoryService.REGULATORY_DOMAINS)
        results.extend(reg_hits)
        status_log["Global Regulators"] = len(reg_hits)

        for region in ["EU", "UK", "BR", "CO", "MX", "GLOBAL"]:
            scoped_hits = RegulatoryService._google_search(
                reg_query,
                category=f"{region} Regulatory",
                domains=RegulatoryService.JURISDICTION_DOMAINS.get(region)
            )
            results.extend(scoped_hits)
            status_log[f"{region} Crawls"] = status_log.get(f"{region} Crawls", 0) + len(scoped_hits)

        # Media/News Search
        media_query = f'"{query_term}" (recall OR death OR lawsuit OR injury OR scandal)'
        media_hits = RegulatoryService._google_search(media_query, category="Media", domains=None) # None = Whole Web
        results.extend(media_hits)
        status_log["Global Media"] = len(media_hits)

        rss_media_hits = []
        for region in regions:
            rss_media_hits.extend(RegulatoryService.MEDIA.search_media(query_term, limit=10, region=region))
        results.extend(rss_media_hits)
        status_log["Regional Media"] = len(rss_media_hits)

        news_hits = RegulatoryService._google_news_rss(query_term, regions or [])
        results.extend(news_hits)
        status_log["Google News RSS"] = len(news_hits)

        # --- 3. POWERFUL MODE: AGENTIC VERIFICATION ---
        if mode == "powerful" and ai_service:
            print(f"🕵️‍♂️ Agent entering Deep Scan mode for {len(results)} records...")
            verified_results = []
            for item in results:
                # Only scrape "Web" sources (Google), usually APIs are structured enough
                if "Google" in item.get("Source", ""):
                    verified_item = RegulatoryService._agent_visit_and_verify(item, query_term, ai_service)
                    if verified_item: # If the agent says it's relevant
                        verified_results.append(verified_item)
                else:
                    verified_results.append(item) # Keep API results as is
            results = verified_results
            status_log["Agent Filtered"] = len(results)

        # --- 4. Final Processing ---
        normalized_records = RegulatoryService._normalize_results(results)
        df = pd.DataFrame(normalized_records)
        if not df.empty:
            df = df.drop_duplicates(subset=['Link'])
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.sort_values(by='Date', ascending=False)
                df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        return df, status_log

    # =========================================================================
    # GOOGLE SEARCH INTEGRATION
    # =========================================================================
    @staticmethod
    def _google_search(query: str, category: str, domains: list = None, num: int = 10) -> list:
        """
        Executes a search using the configured Google Custom Search JSON API.
        """
        api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("google_api_key")
        cx_id = st.secrets.get("GOOGLE_CX_ID") or st.secrets.get("google_cx_id")

        if not api_key or not cx_id:
            print("⚠️ Missing Google API Keys. Skipping Web Search.")
            return []

        # Construct Query
        final_query = query
        if domains:
@@ -134,61 +211,77 @@ class RegulatoryService:
            site_group = " OR ".join([f"site:{d}" for d in domains])
            final_query = f"{query} ({site_group})"

        params = {
            'key': api_key,
            'cx': cx_id,
            'q': final_query,
            'num': num
        }
        
        out = []
        try:
            res = requests.get(RegulatoryService.GOOGLE_URL, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                items = data.get('items', [])
                for item in items:
                    snippet = item.get('snippet', '')
                    title = item.get('title', '')
                    
                    # Basic Relevance Pre-filter
                    risk_level = "Medium"
                    if any(x in (title + snippet).lower() for x in ['death', 'injury', 'urgent', 'class i']):
                        risk_level = "High"

                    jurisdiction = "Global"
                    if category and " " in category:
                        jurisdiction = category.split(" ", 1)[0]
                    elif category in ["EU", "UK", "BR", "CO", "MX"]:
                        jurisdiction = category

                    category_type = "media" if "Media" in category else "regulatory_action"

                    out.append({
                        "Source": f"{category} (Google)",
                        "Jurisdiction": jurisdiction,
                        "Category": category_type,
                        "Product_Type": "Unknown",
                        "Date": "Recent", # Google snippet dates are messy, we treat as recent/unknown
                        "Product": query.split('"')[1] if '"' in query else query, # Extract term
                        "Description": title,
                        "Reason": snippet,
                        "Firm": item.get('displayLink', 'Web Source'),
                        "ID": "WEB-HIT",
                        "Link": item.get('link'),
                        "Status": "Public Web",
                        "Risk_Level": risk_level,
                        "Provenance": {
                            "query": query,
                            "domains": domains,
                            "engine": "Google CSE"
                        }
                    })
        except Exception as e:
            print(f"Google Search Error: {e}")
            
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
@@ -217,97 +310,256 @@ class RegulatoryService:
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
    # FDA / Enforcement helpers
    # =========================================================================
    @staticmethod
    def _fetch_warning_letters(term: str, limit: int = 50) -> list:
        params = {
            "search": f'(subject:\"{term}\" OR issuing_office:\"{term}\" OR document_number:\"{term}\")',
            "limit": limit,
            "sort": "date_issued:desc"
        }
        out = []
        try:
            res = requests.get(RegulatoryService.FDA_WARNING_LETTERS, params=params, timeout=10)
            if res.status_code == 404:
                return []
            res.raise_for_status()
            data = res.json()
            for item in data.get("results", []):
                out.append({
                    "Source": "FDA Warning Letters",
                    "Jurisdiction": "US",
                    "Category": "warning_letter",
                    "Product_Type": item.get("product_type", "Unknown"),
                    "Product": item.get("product_type", term),
                    "Description": item.get("subject"),
                    "Reason": item.get("issuance_reason", item.get("subject", "")),
                    "Firm": item.get("recipient_name"),
                    "Date": item.get("date_issued"),
                    "Link": item.get("url", ""),
                    "Document_URL": item.get("url", ""),
                    "Risk_Level": "High" if "warning" in str(item.get("subject", "")).lower() else "Medium",
                    "Provenance": {"endpoint": RegulatoryService.FDA_WARNING_LETTERS}
                })
        except Exception:
            return []
        return out

    # =========================================================================
    # NORMALIZATION & SANCTIONS
    # =========================================================================
    @staticmethod
    def _normalize_results(raw_results: list[dict]) -> list[dict]:
        normalized = []
        for raw in raw_results:
            record = NormalizedRecord.from_raw(raw).to_dict()
            matches = RegulatoryService.SANCTIONS.check_manufacturer(record.get("Manufacturer"))
            record["Sanctions_Flag"] = bool(matches)
            record["Sanctions_Source"] = ", ".join(matches)
            normalized.append(record)
        return normalized

    # =========================================================================
    # FEEDS & NEWS
    # =========================================================================
    @staticmethod
    def _fetch_rss_feed(feed_meta: dict, query_term: str) -> list:
        url = feed_meta.get("url")
        if not url:
            return []
        headers = {
            'User-Agent': 'Mozilla/5.0 (RegulatoryAgent)',
            'Accept': 'application/xml, text/xml;q=0.9, */*;q=0.8'
        }
        out = []
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return []
            content = resp.content
            # Lightweight XML parsing
            from xml.etree import ElementTree as ET
            root = ET.fromstring(content)
            for item in root.findall('.//item'):
                title = item.findtext('title', default="")
                link = item.findtext('link', default="")
                pub_date = item.findtext('pubDate', default="")
                description = item.findtext('description', default=title)
                if query_term.lower() not in (title + description).lower():
                    continue
                out.append({
                    "Source": feed_meta.get("name"),
                    "Jurisdiction": feed_meta.get("jurisdiction", "GLOBAL"),
                    "Category": "regulatory_action",
                    "Product_Type": feed_meta.get("product_type", "Unknown"),
                    "Product": title,
                    "Description": description,
                    "Reason": description,
                    "Firm": feed_meta.get("name"),
                    "Date": pub_date,
                    "Link": link,
                    "Document_URL": link,
                    "Risk_Level": "Medium",
                    "Provenance": {"feed": url}
                })
        except Exception:
            return []
        return out

    @staticmethod
    def _google_news_rss(query_term: str, regions: list[str]) -> list[dict]:
        hits = []
        region_targets = regions or ["US"]
        region_map = {
            "US": ("US", "en-US"),
            "EU": ("IE", "en-IE"),
            "UK": ("GB", "en-GB"),
            "LATAM": ("MX", "es-419"),
            "APAC": ("SG", "en-SG"),
            "GLOBAL": ("US", "en-US"),
            "BR": ("BR", "pt-BR"),
            "CO": ("CO", "es-CO"),
            "MX": ("MX", "es-MX"),
        }
        for region in region_targets:
            try:
                geo, lang = region_map.get(region, ("US", "en-US"))
                params = {
                    "q": quote(query_term),
                    "hl": lang,
                    "gl": geo,
                    "ceid": f"{geo}:{lang}",
                }
                resp = requests.get(RegulatoryService.GOOGLE_NEWS_URL, params=params, timeout=8)
                if resp.status_code != 200 or not resp.content.startswith(b'<'):
                    continue
                from xml.etree import ElementTree as ET
                root = ET.fromstring(resp.content)
                for item in root.findall('.//item'):
                    title = item.findtext('title', default="")
                    link = item.findtext('link', default="")
                    pub_date = item.findtext('pubDate', default="")
                    hits.append({
                        "Source": "Google News",
                        "Jurisdiction": region,
                        "Category": "media",
                        "Product": query_term,
                        "Description": title,
                        "Reason": item.findtext('description', default=""),
                        "Firm": item.findtext('source', default="News"),
                        "Date": pub_date,
                        "Link": link,
                        "Document_URL": link,
                        "Risk_Level": "Medium",
                        "Provenance": {"feed": "Google News RSS", "region": region}
                    })
            except Exception:
                continue
        return hits

    # =========================================================================
    # LEGACY / API HELPERS (Preserved)
    # =========================================================================
    @staticmethod
    def _fetch_openfda_smart(term: str, category: str, limit: int, start=None, end=None) -> list:
        # Date filtering logic
        date_q = ""
        if start and end:
            s_str = start.strftime("%Y-%m-%d") if hasattr(start, 'strftime') else str(start)
            e_str = end.strftime("%Y-%m-%d") if hasattr(end, 'strftime') else str(end)
            date_q = f' AND recall_initiation_date:[{s_str} TO {e_str}]'

        clean_term = term.strip().replace('"', '')
        base_query = f'(product_description:"{clean_term}"+OR+reason_for_recall:"{clean_term}"+OR+recalling_firm:"{clean_term}")'
        
        # OpenFDA URL construction
        url = f"{RegulatoryService.FDA_BASE}/{category}/enforcement.json"
        params = {'search': base_query + date_q, 'limit': limit, 'sort': 'recall_initiation_date:desc'}
        
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            if "results" in data:
                out = []
                for item in data["results"]:
                    cls = item.get("classification", "")
                    risk = "High" if "Class I" in cls or "Class 1" in cls else "Medium"
                    out.append({
                        "Source": f"FDA {category.capitalize()} Enforcement",
                        "Jurisdiction": "US",
                        "Category": "recall",
                        "Recall_Class": cls,
                        "Product_Type": category.capitalize(),
                        "Date": item.get("recall_initiation_date"),
                        "Product": item.get("product_description"),
                        "Description": item.get("product_description"),
                        "Reason": item.get("reason_for_recall"),
                        "Firm": item.get("recalling_firm"),
                        "Model_Numbers": item.get("product_code"),
                        "ID": item.get("recall_number"),
                        "Link": f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={item.get('event_id', '')}",
                        "Status": item.get("status"),
                        "Risk_Level": risk,
                        "Provenance": {"endpoint": url}
                    })
                return out
        except Exception:
            pass
        return []

    @staticmethod
    def _fetch_cpsc(term: str, start=None, end=None) -> list:
        params = {'format': 'json', 'RecallTitle': term}
        if start and end:
            params['RecallDateStart'] = start.strftime("%Y-%m-%d") if hasattr(start, 'strftime') else str(start)
            params['RecallDateEnd'] = end.strftime("%Y-%m-%d") if hasattr(end, 'strftime') else str(end)
            
        out = []
        try:
            res = requests.get(RegulatoryService.CPSC_BASE, params=params, timeout=5)
            if res.status_code == 200:
                items = res.json()
                if isinstance(items, list):
                    for item in items:
                        out.append({
                            "Source": "CPSC",
                            "Jurisdiction": "US",
                            "Category": "recall",
                            "Product_Type": "Consumer Product",
                            "Date": item.get("RecallDate"),
                            "Product": item.get("Title"),
                            "Description": item.get("Title"),
                            "Reason": item.get("Description", "See Link"), 
                            "Firm": "See Details", 
                            "ID": str(item.get("RecallID")),
                            "Link": item.get("URL"),
                            "Status": "Public",
                            "Risk_Level": "Medium",
                            "Provenance": {"endpoint": RegulatoryService.CPSC_BASE}
                        })
        except Exception: pass
        return out
