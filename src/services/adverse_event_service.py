import requests
import pandas as pd
from datetime import datetime

class AdverseEventService:
    """
    Service to fetch Adverse Event reports (MAUDE) from openFDA.
    Identifies safety signals like injuries or malfunctions.
    """
    
    BASE_URL = "https://api.fda.gov/device/event.json"

    def search_events(self, query_term: str, start_date=None, end_date=None, limit: int = 50) -> list:
        if not query_term:
            return []

        # Construct date filter
        date_query = ""
        if start_date and end_date:
            s_str = start_date.strftime("%Y-%m-%d") if hasattr(start_date, 'strftime') else str(start_date)
            e_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, 'strftime') else str(end_date)
            date_query = f'+AND+date_received:[{s_str}+TO+{e_str}]'

        # Query syntax: Search for device name and ensure we capture relevant events
        sanitized_term = query_term.strip().replace(" ", "+")
        search_query = f'device.generic_name:"{sanitized_term}"{date_query}'
        
        params = {
            'search': search_query,
            'limit': limit,
            'sort': 'date_received:desc'
        }

        out = []
        try:
            res = requests.get(self.BASE_URL, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "results" in data:
                    for item in data["results"]:
                        # Extract key fields
                        mdr_text = "See details."
                        if "mdr_text" in item and item["mdr_text"]:
                            mdr_text = item["mdr_text"][0].get("text", "No description.")
                        
                        # Determine event type
                        event_type = item.get("event_type", "Unknown")
                        outcome = "Malfunction"
                        if "remedial_action" in item:
                            outcome = str(item["remedial_action"])
                        
                        out.append({
                            "Source": "FDA MAUDE (Adverse Event)",
                            "Date": item.get("date_received"),
                            "Product": item.get("device", [{}])[0].get("generic_name", query_term),
                            "Description": mdr_text[:200] + "...",
                            "Reason": f"Event Type: {event_type} | Outcome: {outcome}",
                            "Firm": item.get("manufacturer_name", "Unknown"),
                            "Model Info": item.get("device", [{}])[0].get("model_number", "N/A"),
                            "ID": item.get("report_number", "N/A"),
                            "Link": f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/detail.cfm?mdrfoi__id={item.get('report_number')}",
                            "Status": event_type
                        })
        except Exception as e:
            print(f"MAUDE Search Error: {e}")
            
        return out
