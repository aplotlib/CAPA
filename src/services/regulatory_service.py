# src/services/regulatory_service.py

import requests
import pandas as pd
import re
from datetime import datetime
from urllib.parse import quote

class RegulatoryService:
    """
    Unified service to search global regulatory databases with enhanced 'Deep Scan' logic.
    Sources:
    1. FDA (Device, Drug, Food) - USA
    2. CPSC (Consumer) - USA
    3. MHRA - UK (via GOV.UK API)
    4. Health Canada - Canada
    """
    
    FDA_BASE = "https://api.fda.gov"
    CPSC_BASE = "https://www.saferproducts.gov/RestWebServices/Recall"
    GOV_UK_BASE = "https://www.gov.uk/api/search.json"
    CANADA_BASE = "https://healthycanadians.gc.ca/recall-alert-rappel-avis/api/recent/en"

    @staticmethod
    def search_all_sources(query_term: str, start_date=None, end_date=None, limit: int = 150) -> tuple[pd.DataFrame, dict]:
        """
        Searches all sources and returns:
        1. DataFrame of combined results.
        2. Dictionary of counts per source.
        """
        results = []
        status_log = {}

        # Format dates for APIs if provided
        date_query_fda = ""
        date_params_cpsc = {}

        if start_date and end_date:
            s_str = start_date.strftime("%Y-%m-%d") if hasattr(start_date, 'strftime') else str(start_date)
            e_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, 'strftime') else str(end_date)
            
            # OpenFDA Date Range Syntax: [YYYY-MM-DD TO YYYY-MM-DD]
            date_query_fda = f' AND recall_initiation_date:[{s_str} TO {e_str}]'
            
            # CPSC Date Params
            date_params_cpsc = {
                'RecallDateStart': s_str,
                'RecallDateEnd': e_str
            }

        # --- 1. FDA Sources (USA) ---
        # We now query with "Deep Scan" logic (Wildcards + Cross-field)
        fda_categories = [
            ("FDA Device", "device"),
            ("FDA Drug", "drug"),
            ("FDA Food", "food")
        ]

        for label, category in fda_categories:
            hits = RegulatoryService._fetch_openfda_deep(query_term, category, limit=limit, date_filter=date_query_fda)
            status_log[label] = len(hits)
            results.extend(hits)

        # --- 2. CPSC Source (USA) ---
        cpsc_hits = RegulatoryService._fetch_cpsc(query_term, date_params_cpsc)
        status_log["CPSC"] = len(cpsc_hits)
        results.extend(cpsc_hits)

        # --- 3. MHRA (UK) ---
        uk_hits = RegulatoryService._fetch_uk_mhra(query_term, limit)
        status_log["UK MHRA"] = len(uk_hits)
        results.extend(uk_hits)

        # --- 4. Health Canada (International/Americas) ---
        ca_hits = RegulatoryService._fetch_canada(query_term)
        status_log["Health Canada"] = len(ca_hits)
        results.extend(ca_hits)

        # --- 5. Aggregate & Sort ---
        df = pd.DataFrame(results)
        if not df.empty and 'Date' in df.columns:
            # Normalize dates
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='Date', ascending=False)
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            
        return df, status_log

    @staticmethod
    def _fetch_openfda_deep(term: str, category: str, limit: int, date_filter: str) -> list:
        """
        Advanced handler for FDA APIs using Wildcards (*) and Cross-Field Logic.
        Matches if words appear in Description OR Reason OR Firm OR Code Info.
        """
        if not term.strip(): return []

        url = f"{RegulatoryService.FDA_BASE}/{category}/enforcement.json"
        
        # CLEANUP: Replace non-alphanumeric chars with spaces
        clean_term = re.sub(r'[^\w\s]', ' ', term.strip())
        words = clean_term.split()
        if not words: return []
        
        # DEEP SCAN QUERY CONSTRUCTION
        # Strategy: For each word, look for "word*" in key fields.
        and_clauses = []
        for word in words:
            # Append wildcard to catch plurals/variations (e.g. "pump" -> "pumps")
            w_wild = f"{word}*"
            
            # Fields to check
            fields = ["product_description", "reason_for_recall", "recalling_firm", "code_info"]
            
            or_parts = [f'{field}:{w_wild}' for field in fields]
            or_clause = f"({' OR '.join(or_parts)})"
            and_clauses.append(or_clause)
            
        main_query = " AND ".join(and_clauses)
        search_query = f'({main_query}){date_filter}'
        
        params = {
            'search': search_query,
            'limit': limit,
            'sort': 'recall_initiation_date:desc'
        }
        
        out = []
        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "results" in data:
                    for item in data["results"]:
                        # Construct a direct link if possible (OpenFDA doesn't always give one, so we default to search)
                        rid = item.get("recall_number", "N/A")
                        link = f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={item.get('event_id', '')}"
                        if category != 'device':
                             link = f"https://open.fda.gov/apis/drug/enforcement/" # Generic fallback for non-devices

                        out.append({
                            "Source": f"FDA {category.capitalize()}",
                            "Date": item.get("recall_initiation_date"),
                            "Product": item.get("product_description"),
                            "Reason": item.get("reason_for_recall"),
                            "Firm": item.get("recalling_firm"),
                            "ID": rid,
                            "Link": link,
                            "Status": item.get("status")
                        })
        except Exception:
            pass # Fail silently to keep other sources running
            
        return out

    @staticmethod
    def _fetch_cpsc(term: str, date_params: dict) -> list:
        """Handler for CPSC SaferProducts API."""
        if not term.strip(): return []
            
        params = {'format': 'json', 'RecallTitle': term}
        if date_params: params.update(date_params)
            
        out = []
        try:
            res = requests.get(RegulatoryService.CPSC_BASE, params=params, timeout=10)
            if res.status_code == 200:
                items = res.json()
                if isinstance(items, list):
                    for item in items:
                        out.append({
                            "Source": "CPSC (USA)",
                            "Date": item.get("RecallDate"),
                            "Product": item.get("Title"),
                            "Reason": item.get("Description"), 
                            "Firm": "See Details", 
                            "ID": str(item.get("RecallID")),
                            "Link": item.get("URL", "https://www.cpsc.gov/Recalls"),
                            "Status": "Public Recall"
                        })
        except Exception: pass
        return out

    @staticmethod
    def _fetch_uk_mhra(term: str, limit: int) -> list:
        """Fetches alerts from the UK GOV.UK Search API."""
        if not term.strip(): return []
        params = {
            'q': term,
            'filter_organisations': 'medicines-and-healthcare-products-regulatory-agency',
            'filter_format': 'medical_safety_alert',
            'count': limit,
            'order': '-public_timestamp'
        }
        out = []
        try:
            res = requests.get(RegulatoryService.GOV_UK_BASE, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if 'results' in data:
                    for item in data['results']:
                        raw_date = item.get("public_timestamp", "")
                        fmt_date = raw_date.split("T")[0] if "T" in raw_date else raw_date
                        link = f"https://www.gov.uk{item.get('link')}"
                        out.append({
                            "Source": "UK MHRA",
                            "Date": fmt_date,
                            "Product": item.get("title"),
                            "Reason": item.get("description"), 
                            "Firm": "MHRA Alert",
                            "ID": "MHRA-Link",
                            "Link": link,
                            "Status": "Active"
                        })
        except Exception: pass
        return out

    @staticmethod
    def _fetch_canada(term: str) -> list:
        """Fetches recent recalls from Health Canada."""
        out = []
        try:
            res = requests.get(RegulatoryService.CANADA_BASE, timeout=10)
            if res.status_code == 200:
                data = res.json()
                items = data.get('results', []) if isinstance(data, dict) else data
                term_lower = term.lower()
                for item in items:
                    title = item.get('title', '').lower()
                    category = item.get('category', '').lower()
                    if term_lower in title and any(x in category for x in ['health', 'medical', 'device', 'drug']):
                        date_val = item.get('date_published', '')
                        if str(date_val).isdigit():
                             date_val = datetime.fromtimestamp(int(date_val)).strftime('%Y-%m-%d')
                        out.append({
                            "Source": "Health Canada",
                            "Date": date_val,
                            "Product": item.get('title'),
                            "Reason": "See Health Canada Link",
                            "Firm": "Health Canada",
                            "ID": item.get('recall_id', 'N/A'),
                            "Link": item.get('url'),
                            "Status": "Public"
                        })
        except Exception: pass
        return out
