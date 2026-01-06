import requests
import pandas as pd
import re
import time
import streamlit as st
from datetime import datetime
from urllib.parse import quote
from src.services.adverse_event_service import AdverseEventService
from src.utils import retry_with_backoff

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

        # --- 2. GOOGLE PROGRAMMABLE SEARCH (Global Coverage) ---
        # We perform two types of Google Searches:
        # A. Official Regulatory Bodies (Site-restricted) - High Trust
        # B. Global News/Media (General Web) - High Speed

        # A. Regulatory Site Search
        reg_query = f'"{query_term}" (recall OR safety OR warning OR alert OR field action)'
        reg_hits = RegulatoryService._google_search(reg_query, category="Regulatory", domains=RegulatoryService.REGULATORY_DOMAINS)
        results.extend(reg_hits)
        status_log["Global Regulators"] = len(reg_hits)

        # B. Media/News Search
        media_query = f'"{query_term}" (recall OR death OR lawsuit OR injury OR scandal)'
        media_hits = RegulatoryService._google_search(media_query, category="Media", domains=None) # None = Whole Web
        results.extend(media_hits)
        status_log["Global Media"] = len(media_hits)

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
        df = pd.DataFrame(results)
        if not df.empty:
            # Deduplicate by Link or ID
            df = df.drop_duplicates(subset=['Link'])
            # Normalize Columns
            for col in ['Product', 'Firm', 'Reason', 'Source', 'Link', 'Risk_Level', 'Date']:
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
            print("⚠️ Missing Google API Keys. Skipping Web Search.")
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
                        "Source": f"{category} (Google)",
                        "Date": "Recent", # Google snippet dates are messy, we treat as recent/unknown
                        "Product": query.split('"')[1] if '"' in query else query, # Extract term
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
