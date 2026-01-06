import streamlit as st
import pandas as pd
from src.services.regulatory_service import RegulatoryService

def display_web_search():
    st.header("🌐 Global Web & Media Search")
    st.caption("Search for news, press releases, and safety notices outside of strict regulatory databases.")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Search Query", placeholder="e.g. Medtronic recall news, Philips ventilator lawsuit")
    with col2:
        region = st.selectbox("Region", ["US", "EU", "UK", "LATAM", "APAC", "GLOBAL"])

    if st.button("🔎 Search Web", type="primary"):
        if not query:
            st.error("Please enter a query.")
        else:
            with st.spinner(f"Searching global sources in {region}..."):
                # Use the robust search from RegulatoryService
                # We force 'powerful' mode logic but focused on Media/Web
                
                results = []
                
                # 1. RSS Media Search (No Keys needed)
                from src.services.media_service import MediaMonitoringService
                media_svc = MediaMonitoringService()
                rss_hits = media_svc.search_media(query, limit=15, region=region)
                results.extend(rss_hits)
                
                # 2. Google Custom Search (If keys exist)
                api_hits = RegulatoryService._google_search(
                    query, 
                    category="Web Search", 
                    num=10
                )
                results.extend(api_hits)
                
                if results:
                    df = pd.DataFrame(results)
                    # Deduplicate
                    df = df.drop_duplicates(subset=['Link'])
                    
                    st.subheader(f"Found {len(df)} Results")
                    
                    for idx, row in df.iterrows():
                        with st.expander(f"📰 {row['Description']}"):
                            st.write(f"**Source:** {row['Source']}")
                            st.write(f"**Date:** {row['Date']}")
                            st.info(row.get('Reason', 'No snippet'))
                            st.markdown(f"[Read Full Article]({row['Link']})")
                else:
                    st.warning("No results found. Try broadening your search terms.")
