import requests
import pandas as pd
import re
import time
import streamlit as st
from datetime import datetime
from urllib.parse import quote
from src.services.adverse_event_service import AdverseEventService
from src.services.media_service import MediaMonitoringService
from src.utils import retry_with_backoff

# Try to import BeautifulSoup for scraping, fallback to regex if missing
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

class RegulatoryService:
    """
    Unified Regulatory Intelligence Engine.
    Integrates OpenFDA, CPSC, Google Custom Search, and RSS Media Monitoring.
    Includes Agentic capabilities to visit and verify links.
    """
    
    # Configuration
    FDA_BASE = "https://api.fda.gov"
    CPSC_BASE = "https://www.saferproducts.gov/RestWebServices/Recall"
    GOOGLE_URL = "https://customsearch.googleapis.com/customsearch/v1"

    # Targeted Domains for "Regulatory" Search Category
    REGULATORY_DOMAINS = [
        "gov.uk", "europa.eu", "anvisa.gov.br", "cofepris.gob.mx", 
        "hc-sc.gc.ca", "tga.gov.au", "pmda.go.jp", "swissmedic.ch",
        "invima.gov.co", "argentina.gob.ar/anmat"
    ]

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
        # FDA Recalls
        fda_hits = RegulatoryService._fetch_openfda_smart(query_term, "device", limit, start_date, end_date)
        results.extend(fda_hits)
        status_log["FDA Device"] = len(fda_hits)

        # MAUDE (Adverse Events)
        maude_service = AdverseEventService()
        maude_hits = maude_service.search_events(query_term, start_date, end_date, limit=20)
        results.extend(maude_hits)
        status_log["FDA MAUDE"] = len(maude_hits)

        # CPSC (Consumer Safety)
        cpsc_hits = RegulatoryService._fetch_cpsc(query_term, start_date, end_date)
        results.extend(cpsc_hits)
        status_log["CPSC"] = len(cpsc_hits)

        # --- 2. GLOBAL WEB & MEDIA (Multi-Source) ---
        # We perform two types of searches:
        # A. Google Custom Search API (Best for specific Regulatory Bodies)
        # B. RSS Media Monitoring (Best for News/PR, works without API keys)

        # A. Google Custom Search (Requires Keys)
        reg_query = f'"{query_term}" (recall OR safety OR warning OR alert OR field action)'
        reg_hits = RegulatoryService._google_search(reg_query, category="Regulatory", domains=RegulatoryService.REGULATORY_DOMAINS)
        results.extend(reg_hits)
        status_log["Global Regulators (API)"] = len(reg_hits)

        # B. RSS Media Search (Fallback & Enhancement)
        # This ensures we get news even if Google API keys are missing/exhausted
        media_service = MediaMonitoringService()
        rss_hits = []
        
        # Scan primary regions using RSS
        target_regions = [r for r in regions if r in ["US", "EU", "UK", "LATAM", "APAC"]]
        if not target_regions: target_regions = ["US"]
        
        for reg in target_regions:
            hits = media_service.search_media(query_term, limit=10, region=reg)
            rss_hits.extend(hits)
            
        results.extend(rss_hits)
        status_log["Global Media (RSS)"] = len(rss_hits)

        # C. Google Media Search (API - complementary to RSS)
        if mode == "powerful": # Only burn API credits for media in powerful mode
            media_query = f'"{query_term}" (recall OR death OR lawsuit OR injury OR scandal)'
            api_media_hits = RegulatoryService._google_search(media_query, category="Media (API)", domains=None)
            results.extend(api_media_hits)
            status_log["Global Media (API)"] = len(api_media_hits)

        # --- 3. POWERFUL MODE: AGENTIC VERIFICATION ---
        if mode == "powerful" and ai_service:
            print(f"🕵️‍♂️ Agent entering Deep Scan mode for {len(results)} records...")
            verified_results = []
            
            # Prioritize items that are likely web/unstructured for verification
            for item in results:
                # API results are usually trusted. We verify Web/Media hits.
                if any(x in item.get("Source", "") for x in ["Google", "Media", "Web"]):
                    verified_item = RegulatoryService._agent_visit_and_verify(item, query_term, ai_service)
                    if verified_item: 
                        verified_results.append(verified_item)
                else:
                    verified_results.append(item) 
            
            results = verified_results
            status_log["Agent Filtered"] = len(results)

        # --- 4. Final Processing ---
        df = pd.DataFrame(results)
        if not df.empty:
            # Deduplicate by Link (primary) or ID
            df = df.drop_duplicates(subset=['Link'])
            
            # Normalize Columns
            for col in ['Product', 'Firm', 'Reason', 'Source', 'Link', 'Risk_Level', 'Date', 'Description']:
                if col not in df.columns:
                    df[col] = "N/A"
            
            # Sort by Date
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
            # Silent fail is okay here because we have RSS fallback in search_all_sources
            return []

        # Construct Query
        final_query = query
        if domains:
            # Create a site: filter (site:a.com OR site:b.com)
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

                    out.append({
                        "Source": f"{category}",
                        "Date": "Recent", 
                        "Product": query.split('"')[1] if '"' in query else query,
                        "Description": title,
                        "Reason": snippet,
                        "Firm": item.get('displayLink', 'Web Source'),
                        "ID": "WEB-HIT",
                        "Link": item.get('link'),
                        "Status": "Public Web",
                        "Risk_Level": risk_level
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
        Uses robust headers to simulate a real browser.
        """
        url = item.get('Link')
        if not url: return item

        # 1. Scrape Content with Browser Mimicry
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/'
            }
            
            resp = requests.get(url, headers=headers, timeout=8)
            
            if resp.status_code != 200:
                # If we can't scrape, we return the item but mark it as "Unverified"
                # We do NOT discard it, as the snippet might still be useful.
                item["AI_Analysis"] = "Could not scrape content to verify (Access Denied)."
                return item 

            text_content = ""
            if BeautifulSoup:
                soup = BeautifulSoup(resp.content, 'html.parser')
                # Remove scripts and styles
                for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    script.extract()
                text_content = soup.get_text(separator=' ')
            else:
                # Fallback Regex Stripper
                text_content = re.sub('<[^<]+?>', ' ', resp.text)
            
            # Truncate for Token Limits (approx 1500 words)
            text_content = " ".join(text_content.split())[:6000]

        except Exception as e:
            item["AI_Analysis"] = f"Scraping Error: {str(e)}"
            return item

        # 2. AI Verification
        try:
            # More robust prompt that handles loose keyword matches
            prompt = f"""
            I am researching: "{query_term}"
            I found this webpage content:
            "{text_content}..."
            
            Task:
            1. Is this page discussing a recall, safety alert, lawsuit, or quality issue related to "{query_term}" (or a very similar device)?
            2. If YES, summarize the specific issue in 1 sentence.
            3. If NO (it's an ad, unrelated product, generic home page, or paywall), return "IRRELEVANT".
            
            Return JSON: {{ "is_relevant": true/false, "summary": "..." }}
            """
            
            analysis = ai_service._generate_json(prompt, system_instruction="You are a Regulatory filter.")
            
            if analysis.get("is_relevant") is True:
                item["Reason"] = f"✅ VERIFIED: {analysis.get('summary')}"
                item["AI_Verified"] = True
                return item
            else:
                # If AI says irrelevant, we DROP this item entirely to clean up results
                return None 
                
        except Exception:
            return item # Keep if AI fails to decide

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
        
        # IMPROVED QUERY SYNTAX:
        # 1. Exact phrase match (High precision)
        # 2. OR Keyword match (High recall)
        # This fixes "Zero results" when the user types "Infusion Pump" but record is "Pump, Infusion"
        
        # We construct a query that looks for the phrase OR the words
        base_query = f'(product_description:"{clean_term}"+OR+reason_for_recall:"{clean_term}"+OR+recalling_firm:"{clean_term}"+OR+product_description:{clean_term})'
        
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
                        "Source": f"FDA {category.capitalize()}",
                        "Date": item.get("recall_initiation_date"),
                        "Product": item.get("product_description"),
                        "Description": item.get("product_description"),
                        "Reason": item.get("reason_for_recall"),
                        "Firm": item.get("recalling_firm"),
                        "ID": item.get("recall_number"),
                        "Link": f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={item.get('event_id', '')}",
                        "Status": item.get("status"),
                        "Risk_Level": risk
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
                            "Date": item.get("RecallDate"),
                            "Product": item.get("Title"),
                            "Description": item.get("Title"),
                            "Reason": item.get("Description", "See Link"), 
                            "Firm": "See Details", 
                            "ID": str(item.get("RecallID")),
                            "Link": item.get("URL"),
                            "Status": "Public",
                            "Risk_Level": "Medium"
                        })
        except Exception: pass
        return out
