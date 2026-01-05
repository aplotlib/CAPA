import requests
import pandas as pd
import streamlit as st
import re

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
            # Ensure dates are datetime objects for sorting
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='Date', ascending=False)
            # Convert back to string for display if needed, or keep as datetime
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            
        return df, status_log

    @staticmethod
    def _fetch_openfda(term: str, category: str, limit: int) -> list:
        """
        Generic handler for FDA APIs using robust Lucene query construction.
        """
        if not term or not term.strip():
            return []

        url = f"{RegulatoryService.FDA_BASE}/{category}/enforcement.json"
        
        # FIX: Clean the term to remove punctuation and extra spaces
        # "Infusion, Pump" -> ["Infusion", "Pump"]
        words = re.findall(r'\w+', term.strip())
        
        if not words: 
            return []
            
        # Join with " AND " to ensure all words must be present in the result
        joined_term = " AND ".join(words)
        
        # Search in Product Description OR Reason for Recall
        # We rely on requests to handle the URL encoding of the space/characters
        search_query = f'(product_description:({joined_term}) OR reason_for_recall:({joined_term}))'
        
        params = {
            'search': search_query,
            'limit': limit,
            'sort': 'recall_initiation_date:desc'
        }
        
        out = []
        try:
            # Added explicit timeout
            res = requests.get(url, params=params, timeout=10)
            
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
            elif res.status_code == 400:
                # 400 often means "No matches found" in OpenFDA
                pass
            else:
                print(f"FDA API Error ({category}): {res.status_code}")
                
        except Exception as e:
            print(f"FDA Connection Error: {e}")
            # Optionally log to streamlit if needed, but print is safer for services
            pass
            
        return out

    @staticmethod
    def _fetch_cpsc(term: str) -> list:
        """Handler for CPSC SaferProducts API."""
        if not term or not term.strip():
            return []
            
        # CPSC Simple Search
        # Note: RecallTitle performs a keyword search on the title
        params = {'format': 'json', 'RecallTitle': term}
        out = []
        try:
            res = requests.get(RegulatoryService.CPSC_BASE, params=params, timeout=10)
            if res.status_code == 200:
                items = res.json()
                # CPSC returns a list directly
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
        except Exception as e:
            print(f"CPSC Connection Error: {e}")
            pass
            
        return out
