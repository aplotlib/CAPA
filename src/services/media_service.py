import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime

class MediaMonitoringService:
    """
    Service to monitor negative media coverage and safety bulletins via News RSS.
    Enhanced with proper headers and broader search logic.
    """
    
    # We use Google News RSS as it's the most reliable free source
    RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    def search_media(self, query_term: str, limit: int = 20) -> list:
        if not query_term:
            return []

        # Strategy: Search broadly for the term, then filter for risk keywords in Python.
        # This prevents the RSS feed from returning 0 results due to strict AND logic.
        encoded_query = quote(query_term)
        target_url = self.RSS_URL.format(query=encoded_query)
        
        # Headers are critical for Google News to accept the request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        out = []
        try:
            res = requests.get(target_url, headers=headers, timeout=8)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                
                count = 0
                for item in root.findall('.//item'):
                    if count >= limit: break
                    
                    title = item.find('title').text if item.find('title') is not None else "No Title"
                    link = item.find('link').text if item.find('link') is not None else "N/A"
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "N/A"
                    
                    # Risk Assessment (Client-Side)
                    # We check if the news item is actually "negative" or relevant to safety
                    full_text = title.lower()
                    risk_keywords = ['recall', 'death', 'injury', 'lawsuit', 'warning', 'fda', 'danger', 'safety', 'fail', 'defect']
                    
                    # If it contains a risk keyword, we flag it. 
                    # If not, we still include it but it might be "Low Risk" in the UI.
                    is_risk = any(k in full_text for k in risk_keywords)
                    
                    # Convert date
                    fmt_date = pub_date
                    try:
                        dt_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                        fmt_date = dt_obj.strftime("%Y-%m-%d")
                    except:
                        pass

                    out.append({
                        "Source": "Media",
                        "Date": fmt_date,
                        "Product": query_term,
                        "Description": title,
                        "Reason": "Media Report" if not is_risk else f"Potential Safety Issue ({', '.join([k for k in risk_keywords if k in full_text])})",
                        "Firm": "News Source",
                        "Model Info": "N/A",
                        "ID": "News-Link",
                        "Link": link,
                        "Status": "Public Report",
                        "Risk_Level": "Medium" if is_risk else "Low"
                    })
                    count += 1
        except Exception as e:
            print(f"Media Search Error: {e}")
            
        return out
