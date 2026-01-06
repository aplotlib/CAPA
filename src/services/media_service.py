import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime

class MediaMonitoringService:
    """
    Service to monitor negative media coverage and safety bulletins via News RSS.
    Enhanced with Regional Targeting (EU, LATAM, APAC) and Robust Headers.
    """
    
    # Google News RSS URL template
    # gl = Country (Geo Location), hl = Host Language, ceid = Country:Language
    RSS_URL = "https://news.google.com/rss/search?q={query}&hl={lang}&gl={geo}&ceid={geo}:{lang}"

    def search_media(self, query_term: str, limit: int = 20, region: str = "US") -> list:
        """
        Searches media with region-specific targeting.
        """
        if not query_term:
            return []

        # Region Configuration
        config = {
            "US": {"geo": "US", "lang": "en-US"},
            "EU": {"geo": "IE", "lang": "en-IE"}, # Ireland as proxy for English EU news
            "UK": {"geo": "GB", "lang": "en-GB"},
            "LATAM": {"geo": "MX", "lang": "es-419"}, # Mexico/Spanish as proxy for LATAM
            "APAC": {"geo": "SG", "lang": "en-SG"}, # Singapore as proxy for English APAC
            "GLOBAL": {"geo": "US", "lang": "en-US"}
        }
        
        settings = config.get(region, config["US"])
        
        # Build Query
        encoded_query = quote(query_term)
        target_url = self.RSS_URL.format(
            query=encoded_query, 
            lang=settings["lang"], 
            geo=settings["geo"]
        )
        
        # Robust Headers to look like a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://news.google.com/'
        }
        
        out = []
        try:
            res = requests.get(target_url, headers=headers, timeout=8)
            if res.status_code == 200:
                # Check if content is actually XML
                if not res.content.strip().startswith(b'<'):
                    return []

                root = ET.fromstring(res.content)
                
                count = 0
                for item in root.findall('.//item'):
                    if count >= limit: break
                    
                    title = item.find('title').text if item.find('title') is not None else "No Title"
                    link = item.find('link').text if item.find('link') is not None else "N/A"
                    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "N/A"
                    source_elem = item.find('source')
                    source_name = source_elem.text if source_elem is not None else "News"
                    
                    # Risk Assessment (Client-Side)
                    full_text = title.lower()
                    risk_keywords = [
                        'recall', 'death', 'injury', 'lawsuit', 'warning', 'fda', 'danger', 
                        'safety', 'fail', 'defect', 'ban', 'seize', 'alert', 'adverse',
                        'muerte', 'fallo', 'retiro', 'investigation', 'class i', 'urgent'
                    ]
                    
                    is_risk = any(k in full_text for k in risk_keywords)
                    
                    # Date Formatting
                    fmt_date = pub_date
                    try:
                        # Common RSS date format: "Mon, 06 Jan 2025 14:30:00 GMT"
                        dt_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                        fmt_date = dt_obj.strftime("%Y-%m-%d")
                    except:
                        pass

                    out.append({
                        "Source": f"Media ({region})",
                        "Date": fmt_date,
                        "Product": query_term,
                        "Description": title,
                        "Reason": "Media Report" if not is_risk else f"Safety Keywords Found: {', '.join([k for k in risk_keywords if k in full_text])}",
                        "Firm": source_name,
                        "Model Info": "N/A",
                        "ID": f"NEWS-{hash(link)}",
                        "Link": link,
                        "Status": "Public Report",
                        "Risk_Level": "High" if is_risk else "Low"
                    })
                    count += 1
        except Exception as e:
            print(f"Media Search Error ({region}): {e}")
            
        return out
