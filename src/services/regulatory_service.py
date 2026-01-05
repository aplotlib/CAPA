import requests
import pandas as pd
import re
from datetime import datetime

class RegulatoryService:
    """
    Unified service to search US regulatory databases:
    1. FDA Device Enforcement
    2. FDA Drug Enforcement
    3. FDA Food Enforcement
    4. CPSC (Consumer Product Safety Commission)
    """
    
    FDA_BASE = "https://api.fda.gov"
    CPSC_BASE = "https://www.saferproducts.gov/RestWebServices/Recall"

    @staticmethod
    def search_all_sources(query_term: str, start_date=None, end_date=None, limit: int = 50) -> tuple[pd.DataFrame, dict]:
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

        # --- 1. FDA Sources ---
        fda_categories = [
            ("FDA Device", "device"),
            ("FDA Drug", "drug"),
            ("FDA Food", "food")
        ]

        for label, category in fda_categories:
            # Increased limit to ensure we catch relevant hits
            hits = RegulatoryService._fetch_openfda(query_term, category, limit=limit, date_filter=date_query_fda)
            status_log[label] = len(hits)
            results.extend(hits)

        # --- 2. CPSC Source ---
        cpsc_hits = RegulatoryService._fetch_cpsc(query_term, date_params_cpsc)
        status_log["CPSC"] = len(cpsc_hits)
        results.extend(cpsc_hits)

        # --- 3. Aggregate & Sort ---
        df = pd.DataFrame(results)
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='Date', ascending=False)
            # Standardize date display
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            
        return df, status_log

    @staticmethod
    def _fetch_openfda(term: str, category: str, limit: int, date_filter: str) -> list:
        """
        Advanced handler for FDA APIs using Cross-Field Logic.
        Fixes False Negatives by allowing terms to be distributed across fields.
        """
        if not term.strip():
            return []

        url = f"{RegulatoryService.FDA_BASE}/{category}/enforcement.json"
        
        # CLEANUP: Replace non-alphanumeric chars with spaces
        clean_term = re.sub(r'[^\w\s]', ' ', term.strip())
        words = clean_term.split()
        
        if not words: 
            return []
            
        # CROSS-FIELD AND LOGIC:
        # Instead of searching "Medtronic Pump" in one field, we ensure "Medtronic"
        # is in (Desc OR Reason OR Firm) AND "Pump" is in (Desc OR Reason OR Firm).
        # This catches cases where Firm="Medtronic" and Desc="Infusion Pump".
        
        and_clauses = []
        for word in words:
            # For each word in the user's query, it must appear in at least one of these fields
            or_clause = (
                f'(product_description:{word} '
                f'OR reason_for_recall:{word} '
                f'OR recalling_firm:{word})'
            )
            and_clauses.append(or_clause)
            
        # Join the groups with AND
        main_query = " AND ".join(and_clauses)
        
        # Append date filter
        search_query = f'({main_query}){date_filter}'
        
        params = {
            'search': search_query,
            'limit': limit,
            'sort': 'recall_initiation_date:desc'
        }
        
        out = []
        try:
            res = requests.get(url, params=params, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if "results" in data:
                    for item in data["results"]:
                        out.append({
                            "Source": f"FDA {category.capitalize()}",
                            "Date": item.get("recall_initiation_date"),
                            "Product": item.get("product_description"),
                            "Reason": item.get("reason_for_recall"),
                            "Firm": item.get("recalling_firm"),
                            "ID": item.get("recall_number"),
                            "Status": item.get("status")
                        })
            else:
                # print(f"FDA Error {res.status_code}: {res.text}")
                pass
        except Exception:
            pass
            
        return out

    @staticmethod
    def _fetch_cpsc(term: str, date_params: dict) -> list:
        """Handler for CPSC SaferProducts API."""
        if not term.strip():
            return []
            
        # CPSC Search Params
        params = {'format': 'json', 'RecallTitle': term}
        if date_params:
            params.update(date_params)
            
        out = []
        try:
            res = requests.get(RegulatoryService.CPSC_BASE, params=params, timeout=15)
            if res.status_code == 200:
                items = res.json()
                if isinstance(items, list):
                    for item in items:
                        out.append({
                            "Source": "CPSC (Consumer)",
                            "Date": item.get("RecallDate"),
                            "Product": item.get("Title"),
                            "Reason": item.get("Description"), 
                            "Firm": "See Details", 
                            "ID": str(item.get("RecallID")),
                            "Status": "Public Recall"
                        })
        except Exception:
            pass
            
        return out
