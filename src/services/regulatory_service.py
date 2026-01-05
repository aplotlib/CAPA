import requests
import pandas as pd
import re
from datetime import datetime
from urllib.parse import quote
from src.services.adverse_event_service import AdverseEventService
from src.services.media_service import MediaMonitoringService

class RegulatoryService:
    """
    Unified service to search global regulatory databases with enhanced
    fallback logic and robust error handling.
    """
    
    FDA_BASE = "https://api.fda.gov"
    CPSC_BASE = "https://www.saferproducts.gov/RestWebServices/Recall"
    GOV_UK_BASE = "https://www.gov.uk/api/search.json"
    CANADA_BASE = "https://healthycanadians.gc.ca/recall-alert-rappel-avis/api/recent/en"

    @staticmethod
    def search_all_sources(query_term: str, start_date=None, end_date=None, limit: int = 150) -> tuple[pd.DataFrame, dict]:
        results = []
        status_log = {}

        # Initialize Sub-Services
        maude_service = AdverseEventService()
        media_service = MediaMonitoringService()

        # Date Filtering Setup
        date_query_fda = ""
        date_params_cpsc = {}

        if start_date and end_date:
            s_str = start_date.strftime("%Y-%m-%d") if hasattr(start_date, 'strftime') else str(start_date)
            e_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, 'strftime') else str(end_date)
            date_query_fda = f' AND recall_initiation_date:[{s_str} TO {e_str}]'
            date_params_cpsc = {'RecallDateStart': s_str, 'RecallDateEnd': e_str}

        # --- 1. FDA Recalls (Device, Drug, Food) ---
        # We try a specific search first, then a broad one if needed
        fda_categories = [("FDA Device", "device"), ("FDA Drug", "drug")]
        for label, category in fda_categories:
            hits = RegulatoryService._fetch_openfda_smart(query_term, category, limit, date_query_fda)
            status_log[label] = len(hits)
            results.extend(hits)

        # --- 2. FDA MAUDE (Adverse Events) ---
        maude_hits = maude_service.search_events(query_term, start_date, end_date, limit=50)
        status_log["FDA MAUDE"] = len(maude_hits)
        results.extend(maude_hits)

        # --- 3. News Media (Enhanced) ---
        media_hits = media_service.search_media(query_term, limit=20)
        status_log["Media"] = len(media_hits)
        results.extend(media_hits)

        # --- 4. CPSC (Consumer Products) ---
        cpsc_hits = RegulatoryService._fetch_cpsc(query_term, date_params_cpsc)
        status_log["CPSC"] = len(cpsc_hits)
        results.extend(cpsc_hits)

        # --- 5. UK MHRA ---
        uk_hits = RegulatoryService._fetch_uk_mhra(query_term, limit)
        status_log["UK MHRA"] = len(uk_hits)
        results.extend(uk_hits)

        # --- 6. Health Canada ---
        ca_hits = RegulatoryService._fetch_canada(query_term)
        status_log["Health Canada"] = len(ca_hits)
        results.extend(ca_hits)

        # --- Aggregate ---
        df = pd.DataFrame(results)
        if not df.empty:
            # Normalize Date
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.sort_values(by='Date', ascending=False)
                df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            
            # Ensure critical columns exist
            for col in ['Product', 'Firm', 'Reason', 'Source', 'Link']:
                if col not in df.columns:
                    df[col] = "N/A"
            
        return df, status_log

    @staticmethod
    def _fetch_openfda_smart(term: str, category: str, limit: int, date_filter: str) -> list:
        """
        Smart search that attempts exact matching first, then falls back to broad matching.
        """
        if not term.strip(): return []
        url = f"{RegulatoryService.FDA_BASE}/{category}/enforcement.json"
        
        # Strategy A: Broad Description Search
        # Searches product_description OR reason_for_recall
        clean_term = term.strip().replace('"', '')
        search_query = f'(product_description:"{clean_term}"+OR+reason_for_recall:"{clean_term}"+OR+recalling_firm:"{clean_term}"){date_filter}'
        
        params = {'search': search_query, 'limit': limit, 'sort': 'recall_initiation_date:desc'}
        
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            
            # Fallback Strategy B: If no results, try splitting words (Fuzzy-ish)
            if "error" in data or not data.get("results"):
                words = clean_term.split()
                if len(words) > 1:
                    # Construct AND query for words: (product_description:word1+AND+product_description:word2)
                    # Note: We apply wildcards to be more effective
                    desc_parts = [f'product_description:{w}*' for w in words]
                    combined_desc = "+AND+".join(desc_parts)
                    search_query = f'({combined_desc}){date_filter}'
                    params['search'] = search_query
                    res = requests.get(url, params=params, timeout=10)
                    data = res.json()

            if "results" in data:
                out = []
                for item in data["results"]:
                    rid = item.get("recall_number", "N/A")
                    out.append({
                        "Source": f"FDA {category.capitalize()}",
                        "Date": item.get("recall_initiation_date"),
                        "Product": item.get("product_description"),
                        "Description": item.get("product_description"),
                        "Reason": item.get("reason_for_recall"),
                        "Firm": item.get("recalling_firm"),
                        "Model Info": item.get("code_info", "N/A"),
                        "ID": rid,
                        "Link": f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={item.get('event_id', '')}",
                        "Status": item.get("status")
                    })
                return out
                
        except Exception as e:
            print(f"FDA Search Error ({category}): {e}")
            
        return []

    @staticmethod
    def _fetch_cpsc(term: str, date_params: dict) -> list:
        # CPSC API is simple but effective
        if not term.strip(): return []
        params = {'format': 'json', 'RecallTitle': term}
        if date_params: params.update(date_params)
        out = []
        try:
            res = requests.get(RegulatoryService.CPSC_BASE, params=params, timeout=5)
            if res.status_code == 200:
                items = res.json()
                if isinstance(items, list):
                    for item in items:
                        out.append({
                            "Source": "CPSC (USA)",
                            "Date": item.get("RecallDate"),
                            "Product": item.get("Title"),
                            "Description": item.get("Title"),
                            "Reason": item.get("Description", "See Link"), 
                            "Firm": "See Details", 
                            "Model Info": "N/A",
                            "ID": str(item.get("RecallID")),
                            "Link": item.get("URL", "https://www.cpsc.gov/Recalls"),
                            "Status": "Public"
                        })
        except Exception: pass
        return out

    @staticmethod
    def _fetch_uk_mhra(term: str, limit: int) -> list:
        if not term.strip(): return []
        params = {'q': term, 'filter_organisations': 'medicines-and-healthcare-products-regulatory-agency', 'count': limit, 'order': '-public_timestamp'}
        out = []
        try:
            res = requests.get(RegulatoryService.GOV_UK_BASE, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if 'results' in data:
                    for item in data['results']:
                        raw_date = item.get("public_timestamp", "")
                        fmt_date = raw_date.split("T")[0] if "T" in raw_date else raw_date
                        out.append({
                            "Source": "UK MHRA",
                            "Date": fmt_date,
                            "Product": item.get("title"),
                            "Description": item.get("description"),
                            "Reason": item.get("description"), 
                            "Firm": "MHRA",
                            "Model Info": "N/A",
                            "ID": "MHRA-Alert",
                            "Link": f"https://www.gov.uk{item.get('link')}",
                            "Status": "Active"
                        })
        except Exception: pass
        return out

    @staticmethod
    def _fetch_canada(term: str) -> list:
        # Improved filtering for Canada
        out = []
        try:
            res = requests.get(RegulatoryService.CANADA_BASE, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('results', []) if isinstance(data, dict) else data
                
                term_parts = term.lower().split()
                
                for item in items:
                    title = item.get('title', '').lower()
                    cat = item.get('category', '').lower()
                    
                    # Fuzzy match: If ANY major word from search term is in title
                    if any(t in title for t in term_parts) and any(x in cat for x in ['health', 'medical', 'device']):
                        
                        date_val = item.get('date_published', '')
                        if str(date_val).isdigit(): 
                            date_val = datetime.fromtimestamp(int(date_val)).strftime('%Y-%m-%d')
                            
                        link = item.get('url', 'https://recalls-rappels.canada.ca/en')
                        if link.startswith('/'): link = f"https://recalls-rappels.canada.ca{link}"
                        
                        out.append({
                            "Source": "Health Canada",
                            "Date": date_val,
                            "Product": item.get('title'),
                            "Description": item.get('title'),
                            "Reason": "See Link",
                            "Firm": "Health Canada",
                            "Model Info": "N/A",
                            "ID": item.get('recall_id', 'N/A'),
                            "Link": link,
                            "Status": "Public"
                        })
        except Exception: pass
        return out
