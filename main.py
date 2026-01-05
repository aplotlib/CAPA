import streamlit as st
import requests
import json
from openai import OpenAI

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
st.set_page_config(page_title="CAPA Regulatory AI", layout="wide")

# Retrieve keys from Streamlit Secrets
try:
    # Use the existing OpenAI key you already had in secrets
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    
    # Use the new Google keys we just added
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX_ID = st.secrets["GOOGLE_CX_ID"]
except KeyError as e:
    st.error(f"Missing API Key in secrets: {e}. Please check your secrets.toml file.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# 2. SEARCH TOOLS
# ==========================================

def search_openfda(device_name, manufacturer=None):
    """Queries the official US FDA database for enforcement reports."""
    base_url = "https://api.fda.gov/device/enforcement.json"
    
    # Construct query
    query_parts = [f'product_description:"{device_name}"']
    if manufacturer:
        query_parts.append(f'recalling_firm:"{manufacturer}"')
    
    search_query = " AND ".join(query_parts)
    params = {'search': search_query, 'limit': 5}
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if "error" in data:
            return [] # Return empty list if no hits
            
        results = []
        for item in data.get('results', []):
            results.append({
                "source": "US FDA (Structured)",
                "recall_number": item.get('recall_number'),
                "reason": item.get('reason_for_recall'),
                "status": item.get('status'),
                "date": item.get('report_date')
            })
        return results
    except Exception as e:
        return [f"Error querying OpenFDA: {str(e)}"]

def search_google(query, category="general"):
    """Uses Google Programmable Search to find Global Regs & Media."""
    url = "https://www.googleapis.com/customsearch/v1"
    
    # Define site filters for regulatory bodies
    regulatory_sites = [
        "site:gov.uk",           # UK MHRA
        "site:europa.eu",        # EU EMA/EUDAMED
        "site:anvisa.gov.br",    # Brazil ANVISA
        "site:cofepris.gob.mx",  # Mexico
        "site:fda.gov",          # US FDA (Web)
        "site:tga.gov.au",       # Australia TGA
        "site:hc-sc.gc.ca"       # Health Canada
    ]
    
    final_query = query
    
    if category == "regulatory":
        # Force Google to look at specific government domains
        site_string = " OR ".join(regulatory_sites)
        final_query = f"({site_string}) {query} recall OR alert OR safety"
    elif category == "media":
        # Look for news
        final_query = f"{query} medical device recall news problem lawsuit"

    params = {
        'key': GOOGLE_API_KEY,
        'cx': GOOGLE_CX_ID,
        'q': final_query,
        'num': 5
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        results = []
        if 'items' in data:
            for item in data['items']:
                results.append({
                    "source": "Web/Media",
                    "title": item.get('title'),
                    "link": item.get('link'),
                    "snippet": item.get('snippet')
                })
        return results
    except Exception as e:
        return [f"Error querying Google: {str(e)}"]

# ==========================================
# 3. UI & APP LOGIC
# ==========================================

st.title("🏥 CAPA AI: Regulatory Intelligence Tool")
st.markdown("Search US, EU, UK, and LATAM databases + Global Media for device safety issues.")

with st.form("search_form"):
    col1, col2 = st.columns(2)
    with col1:
        device_name = st.text_input("Device Name", placeholder="e.g. Infusion Pump")
        model_num = st.text_input("Model Number (Optional)", placeholder="e.g. Alaris 8015")
    with col2:
        manufacturer = st.text_input("Manufacturer/Vendor", placeholder="e.g. Becton Dickinson")
        category = st.selectbox("Device Category", ["General", "Cardiovascular", "Orthopedic", "Radiology", "Dental"])
    
    submitted = st.form_submit_button("Run Safety Scan")

if submitted and device_name:
    st.divider()
    
    with st.status("Running Global Safety Scan...", expanded=True) as status:
        
        # 1. US FDA
        st.write("🇺🇸 Querying US FDA Enforcement Database...")
        fda_hits = search_openfda(device_name, manufacturer)
        
        # 2. Global Regulatory
        st.write("🌍 Querying Global Agencies (EU, UK, LATAM, APAC)...")
        reg_query = f"{device_name} {manufacturer if manufacturer else ''} {model_num if model_num else ''}"
        global_hits = search_google(reg_query, category="regulatory")
        
        # 3. Media
        st.write("📰 Querying Global Media & News...")
        media_hits = search_google(reg_query, category="media")
        
        status.update(label="Data collection complete!", state="complete", expanded=False)

    # Display Raw Data in Tabs
    tab1, tab2, tab3 = st.tabs(["AI Analysis", "Raw Database Hits", "Web Search Results"])
    
    with tab1:
        st.subheader("🤖 AI Risk Assessment")
        
        prompt = f"""
        You are a Quality Assurance Regulatory Expert. Review the collected data for:
        Device: {device_name}
        Manufacturer: {manufacturer}
        
        DATA:
        1. US FDA Database: {json.dumps(fda_hits)}
        2. Global Regulatory Web Hits: {json.dumps(global_hits)}
        3. Media News Hits: {json.dumps(media_hits)}
        
        OUTPUT:
        Provide a professional CAPA Risk Assessment Summary using Markdown.
        1. **Executive Summary**: Is there an active crisis?
        2. **Global Recall Status**: Break down by region (US vs EU vs others).
        3. **Key Warning Signals**: Summarize specific technical failures mentioned (e.g., software bug, battery failure).
        4. **Risk Level**: (Low/Medium/High) with justification.
        5. **Recommended Actions**: 3 bullet points for the quality engineering team.
        """
        
        if not OPENAI_API_KEY:
             st.error("No OpenAI Key found.")
        else:
            with st.spinner("AI is analyzing regulatory texts..."):
                try:
                    completion = client.chat.completions.create(
                        model="gpt-4o", 
                        messages=[
                            {"role": "system", "content": "You are a precise and helpful regulatory consultant."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    st.markdown(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI Error: {e}")

    with tab2:
        st.subheader("US FDA Structured Data")
        if fda_hits:
            st.json(fda_hits)
        else:
            st.info("No structured FDA enforcement reports found for this specific query.")

    with tab3:
        st.subheader("Global Web & Regulatory Hits")
        if global_hits or media_hits:
            for hit in global_hits + media_hits:
                st.markdown(f"**[{hit['title']}]({hit['link']})**")
                st.caption(f"{hit['source']} | {hit['snippet']}")
                st.divider()
        else:
            st.info("No web results found.")

elif submitted:
    st.warning("Please enter at least a Device Name to start.")
