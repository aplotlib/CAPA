import requests
import pandas as pd
import streamlit as st

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
    def search_all_sources(query_term: str, limit: int = 15) -> tuple[pd.DataFrame, dict]:
        """
        Searches all sources and returns:
        1. DataFrame of combined results.
        2. Dictionary of counts per source (e.g., {'FDA Device': 5, 'CPSC': 0}).
        """
        results = []
        status_log = {}

        # --- 1. FDA Sources ---
        # We search Devices, Drugs, and Food
        fda_categories = [
            ("FDA Device", "device"),
            ("FDA Drug", "drug"),
            ("FDA Food", "food")
        ]

        for label, category in fda_categories:
            hits = RegulatoryService._fetch_openfda(query_term, category, limit)
            status_log[label] = len(hits)
            results.extend(hits)

        # --- 2. CPSC Source ---
        cpsc_hits = RegulatoryService._fetch_cpsc(query_term)
        status_log["CPSC"] = len(cpsc_hits)
        results.extend(cpsc_hits)

        # --- 3. Aggregate & Sort ---
        df = pd.DataFrame(results)
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='Date', ascending=False)
            
        return df, status_log

    @staticmethod
    def _fetch_openfda(term: str, category: str, limit: int) -> list:
        """
        Generic handler for FDA APIs.
        FIX: Uses spaces for Boolean logic; lets `requests` handle URL encoding.
        """
        if not term.strip():
            return []

        url = f"{RegulatoryService.FDA_BASE}/{category}/enforcement.json"
        
        # FIX: Do NOT use '+'. Use spaces. 'requests' will encode spaces to '+' automatically.
        # We construct a Lucene query: (field:(term AND term) OR field:(term AND term))
        words = term.strip().split()
        if not words: 
            return []
            
        # Join with " AND " to ensure all words must be present
        joined_term = " AND ".join(words)
        
        # Search in Product Description OR Reason for Recall
        search_query = f'(product_description:({joined_term}) OR reason_for_recall:({joined_term}))'
        
        params = {
            'search': search_query,
            'limit': limit,
            'sort': 'recall_initiation_date:desc'
        }
        
        out = []
        try:
            res = requests.get(url, params=params, timeout=5)
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
        except Exception as e:
            # print(f"Debug: FDA {category} error: {e}")
            pass
        return out

    @staticmethod
    def _fetch_cpsc(term: str) -> list:
        """Handler for CPSC SaferProducts API."""
        if not term.strip():
            return []
            
        # CPSC Simple Search
        params = {'format': 'json', 'RecallTitle': term}
        out = []
        try:
            res = requests.get(RegulatoryService.CPSC_BASE, params=params, timeout=5)
            if res.status_code == 200:
                items = res.json()
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
