import requests
import pandas as pd
import streamlit as st

class OpenFDAService:
    """
    Service to interact with the openFDA API for real-time regulatory data.
    Documentation: https://open.fda.gov/apis/device/enforcement/
    """
    
    BASE_URL = "https://api.fda.gov/device/enforcement.json"

    @staticmethod
    def search_recalls(query_term: str, limit: int = 10) -> pd.DataFrame:
        """
        Searches the FDA Device Enforcement endpoint for real recalls.
        """
        if not query_term:
            return pd.DataFrame()

        # Construct query: Search description, product code, or reason
        # We replace spaces with '+' for the API syntax
        sanitized_term = query_term.strip().replace(" ", "+")
        
        # Search syntax: (product_description:"term"+OR+reason_for_recall:"term")
        search_query = f'(product_description:"{sanitized_term}"+OR+reason_for_recall:"{sanitized_term}")'
        
        params = {
            'search': search_query,
            'limit': limit,
            'sort': 'recall_initiation_date:desc' # Get newest first
        }

        try:
            response = requests.get(OpenFDAService.BASE_URL, params=params)
            data = response.json()

            if "error" in data:
                # Handle "No matches found" gracefully
                return pd.DataFrame()

            if "results" in data:
                results = data["results"]
                
                # Extract relevant fields for the UI
                processed_data = []
                for item in results:
                    processed_data.append({
                        "Date": item.get("recall_initiation_date"),
                        "Class": item.get("classification"),
                        "Product": item.get("product_description"),
                        "Reason": item.get("reason_for_recall"),
                        "Firm": item.get("recalling_firm"),
                        "Status": item.get("status"),
                        "Recall #": item.get("recall_number")
                    })
                
                return pd.DataFrame(processed_data)
            
            return pd.DataFrame()

        except Exception as e:
            st.error(f"Failed to connect to FDA API: {e}")
            return pd.DataFrame()
