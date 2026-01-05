import requests
import pandas as pd
import re
from datetime import datetime
from urllib.parse import quote

class RegulatoryService:
    """
    Unified service to search global regulatory databases with robust link generation.
    """
    
    FDA_BASE = "https://api.fda.gov"
    CPSC_BASE = "https://www.saferproducts.gov/RestWebServices/Recall"
    GOV_UK_BASE = "https://www.gov.uk/api/search.json"
    CANADA_BASE = "https://healthycanadians.gc.ca/recall-alert-rappel-avis/api/recent/en"

    @staticmethod
    def search_all_sources(query_term: str, start_date=None, end_date=None, limit: int = 150) -> tuple[pd.DataFrame, dict]:
        results = []
        status_log = {}

        # Date Filtering Setup
        date_query_fda = ""
        date_params_cpsc = {}

        if start_date and end_date:
            s_str = start_date.strftime("%Y-%m-%d") if hasattr(start_date, 'strftime') else str(start_date)
            e_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, 'strftime') else str(end_date)
            date_query_fda = f' AND recall_initiation_date:[{s_str} TO {e_str}]'
            date_params_cpsc = {'RecallDateStart': s_str, 'RecallDateEnd': e_str}

        # --- 1. FDA Sources ---
        fda_categories = [("FDA Device", "device"), ("FDA Drug", "drug"), ("FDA Food", "food")]
        for label, category in fda_categories:
            hits = RegulatoryService._fetch_openfda_deep(query_term, category, limit, date_query_fda)
            status_log[label] = len(hits)
            results.extend(hits)

        # --- 2. CPSC ---
        cpsc_hits = RegulatoryService._fetch_cpsc(query_term, date_params_cpsc)
        status_log["CPSC"] = len(cpsc_hits)
        results.extend(cpsc_hits)

        # --- 3. UK MHRA ---
        uk_hits = RegulatoryService._fetch_uk_mhra(query_term, limit)
        status_log["UK MHRA"] = len(uk_hits)
        results.extend(uk_hits)

        # --- 4. Health Canada ---
        ca_hits = RegulatoryService._fetch_canada(query_term)
        status_log["Health Canada"] = len(ca_hits)
        results.extend(ca_hits)

        # --- Aggregate ---
        df = pd.DataFrame(results)
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='Date', ascending=False)
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            
        return df, status_log

    @staticmethod
    def _fetch_openfda_deep(term: str, category: str, limit: int, date_filter: str) -> list:
        if not term.strip(): return []

        url = f"{RegulatoryService.FDA_BASE}/{category}/enforcement.json"
        
        # Deep Scan Logic
        clean_term = re.sub(r'[^\w\s]', ' ', term.strip())
        words = clean_term.split()
        if not words: return []
        
        and_clauses = []
        for word in words:
            w_wild = f"{word}*"
            fields = ["product_description", "reason_for_recall", "recalling_firm", "code_info"]
            or_parts = [f'{field}:{w_wild}' for field in fields]
            and_clauses.append(f"({' OR '.join(or_parts)})")
            
        main_query = " AND ".join(and_clauses)
        search_query = f'({main_query}){date_filter}'
        
        params = {'search': search_query, 'limit': limit, 'sort': 'recall_initiation_date:desc'}
        
        out = []
        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "results" in data:
                    for item in data["results"]:
                        # ROBUST LINK GENERATION
                        rid = item.get("recall_number", "N/A")
                        event_id = item.get("event_id")
                        
                        if category == 'device' and event_id:
                            link = f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={event_id}"
                        elif category == 'drug' and rid != "N/A":
                             link = f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=BasicSearch.process"
                        else:
                            q_safe = quote(item.get("product_description", "")[:50])
                            link = f"https://www.google.com/search?q=FDA+Recall+{rid}+{q_safe}"

                        out.append({
                            "Source": f"FDA {category.capitalize()}",
                            "Date": item.get("recall_initiation_date"),
                            "Product": item.get("product_description"),
                            "Description": item.get("product_description"),
                            "Reason": item.get("reason_for_recall"),
                            "Firm": item.get("recalling_firm"),
                            "Model Info": item.get("code_info", "N/A"),
                            "ID": rid,
                            "Link": link,
                            "Status": item.get("status")
                        })
        except Exception: pass
        return out

    @staticmethod
    def _fetch_cpsc(term: str, date_params: dict) -> list:
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
                            "Description": item.get("Title"),
                            "Reason": item.get("Description"), 
                            "Firm": "See Details", 
                            "Model Info": "See Link",
                            "ID": str(item.get("RecallID")),
                            "Link": item.get("URL", "https://www.cpsc.gov/Recalls"),
                            "Status": "Public"
                        })
        except Exception: pass
        return out

    @staticmethod
    def _fetch_uk_mhra(term: str, limit: int) -> list:
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
                            "Description": item.get("description"),
                            "Reason": item.get("description"), 
                            "Firm": "MHRA Alert",
                            "Model Info": "N/A",
                            "ID": "MHRA-Link",
                            "Link": link,
                            "Status": "Active"
                        })
        except Exception: pass
        return out

    @staticmethod
    def _fetch_canada(term: str) -> list:
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
                        link = item.get('url', 'https://recalls-rappels.canada.ca/en')
                        if link.startswith('/'): link = f"https://recalls-rappels.canada.ca{link}"
                        out.append({
                            "Source": "Health Canada",
                            "Date": date_val,
                            "Product": item.get('title'),
                            "Description": item.get('title'),
                            "Reason": "See Link for Full Text",
                            "Firm": "Health Canada",
                            "Model Info": "N/A",
                            "ID": item.get('recall_id', 'N/A'),
                            "Link": link,
                            "Status": "Public"
                        })
        except Exception: pass
        return out
