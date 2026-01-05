import requests
import pandas as pd
import streamlit as st
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
    def search_all_sources(query_term: str, limit: int = 15) -> pd.DataFrame:
        """Aggregates recalls from all available regulatory sources."""
        results = []
        
        # 1. FDA Devices
        results.extend(RegulatoryService._fetch_openfda(query_term, "device", limit))
        
        # 2. FDA Drugs
        results.extend(RegulatoryService._fetch_openfda(query_term, "drug", limit))
        
        # 3. FDA Food
        results.extend(RegulatoryService._fetch_openfda(query_term, "food", limit))
        
        # 4. CPSC (Consumer Products)
        results.extend(RegulatoryService._fetch_cpsc(query_term))
        
        df = pd.DataFrame(results)
        if not df.empty:
            # Sort by date descending
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.sort_values(by='Date', ascending=False)
        return df

    @staticmethod
    def _fetch_openfda(term: str, category: str, limit: int) -> list:
        """
        Generic handler for FDA Device/Drug/Food APIs.
        USES SMART KEYWORD SEARCH (AND Logic) instead of PHRASE SEARCH.
        """
        if not term.strip():
            return []

        url = f"{RegulatoryService.FDA_BASE}/{category}/enforcement.json"
        
        # FIX: Split query into words to allow "AND" logic
        # e.g., "Heart Valve" becomes (product_description:(Heart+AND+Valve) ...)
        # This finds "Valve, Heart" AND "Heart Valve"
        words = term.strip().split()
        joined_term = "+AND+".join(words)
        
        # Construct flexible query: (Product matches A+B OR Reason matches A+B)
        search_query = f'(product_description:({joined_term})+OR+reason_for_recall:({joined_term}))'
        
        params = {
            'search': search_query,
            'limit': limit,
            'sort': 'recall_initiation_date:desc'
        }
        
        out = []
        try:
            # We must pass the search query carefully. Requests usually encodes spaces, 
            # but we already constructed the syntax with '+'.
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
            # Fail silently to keep the app running if one API is down
            print(f"Error fetching FDA {category}: {e}")
        return out

    @staticmethod
    def _fetch_cpsc(term: str) -> list:
        """Handler for CPSC SaferProducts API."""
        # CPSC uses 'RecallTitle' or 'Description' for filtering
        # Note: CPSC API is simpler and does not support complex boolean operators easily in one param.
        # We search RecallTitle first.
        
        if not term.strip():
            return []
            
        params = {'format': 'json', 'RecallTitle': term}
        out = []
        try:
            res = requests.get(RegulatoryService.CPSC_BASE, params=params, timeout=5)
            if res.status_code == 200:
                items = res.json()
                # CPSC returns a list directly
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
        except Exception as e:
            print(f"Error fetching CPSC: {e}")
        return out
