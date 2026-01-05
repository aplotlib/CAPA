import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime

class MediaMonitoringService:
    """
    Service to monitor negative media coverage and safety bulletins via News RSS.
    """
    
    RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    def search_media(self, query_term: str, limit: int = 20) -> list:
        if not query_term:
            return []

        # Refine query to target safety/quality issues
        # We look for the product name AND keywords like 'recall', 'safety', 'danger', 'lawsuit', 'warning'
        refined_query = f'{query_term} AND (safety OR recall OR danger OR lawsuit OR warning OR FDA OR death)'
        encoded_query = quote(refined_query)
        
        target_url = self.RSS_URL.format(query=encoded_query)
        
        out = []
        try:
            res = requests.get(target_url, timeout=10)
            if res.status_code == 200:
                # Parse XML
                root = ET.fromstring(res.content)
                
                count = 0
                for item in root.findall('.//item'):
                    if count >= limit: break
                    
                    title = item.find('title').text if item.find('title') is not None else "No Title"
                    link = item.find('link').text if item.find('link') is not None else "N/A"
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "N/A"
                    
                    # Convert date to YYYY-MM-DD if possible
                    fmt_date = pub_date
                    try:
                        dt_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                        fmt_date = dt_obj.strftime("%Y-%m-%d")
                    except:
                        pass

                    out.append({
                        "Source": "Media Monitor",
                        "Date": fmt_date,
                        "Product": query_term, # News doesn't inherently have a "product" field
                        "Description": title,
                        "Reason": "Negative Media / Safety Bulletin",
                        "Firm": "Media Source",
                        "Model Info": "N/A",
                        "ID": link[-10:], # Pseudo-ID
                        "Link": link,
                        "Status": "Public Report"
                    })
                    count += 1
        except Exception as e:
            print(f"Media Search Error: {e}")
            
        return out
