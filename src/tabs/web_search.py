import streamlit as st
import pandas as pd
from src.services.regulatory_service import RegulatoryService

def display_web_search():
    st.header("🌐 Global Web & Media Search")
    st.caption("Search for news, press releases, and safety notices outside of strict regulatory databases.")

    with st.container(border=True):
        with st.form("web_search_form"):
            col1, col2, col3 = st.columns([2.2, 1, 1])
            with col1:
                query = st.text_input(
                    "Search Query",
                    placeholder="e.g. Medtronic recall news, Philips ventilator lawsuit",
                )
            with col2:
                region = st.selectbox("Region", ["US", "EU", "UK", "LATAM", "APAC", "GLOBAL"])
                max_results = st.select_slider("Max results", options=[10, 15, 20, 30], value=15)
            with col3:
                st.markdown("##### Focus")
                include_media = st.checkbox("Media RSS", value=True)
                include_google = st.checkbox("Google CSE", value=True)
            submit = st.form_submit_button("🔎 Search Web", type="primary", use_container_width=True)

    if submit:
        if not query:
            st.error("Please enter a query.")
        else:
            with st.spinner(f"Searching global sources in {region}..."):
                results = []

                from src.services.media_service import MediaMonitoringService

                media_svc = MediaMonitoringService()
                if include_media:
                    rss_hits = media_svc.search_media(query, limit=max_results, region=region)
                    results.extend(rss_hits)

                if include_google:
                    api_hits = RegulatoryService._google_search(
                        query,
                        category="Web Search",
                        num=min(10, max_results),
                    )
                    results.extend(api_hits)

                if results:
                    df = pd.DataFrame(results)
                    df = df.drop_duplicates(subset=["Link"])

                    st.subheader(f"Found {len(df)} Results")
                    left, right = st.columns([2, 1])
                    with left:
                        for _, row in df.iterrows():
                            with st.expander(f"📰 {row['Description']}"):
                                st.write(f"**Source:** {row['Source']}")
                                st.write(f"**Date:** {row['Date']}")
                                st.info(row.get("Reason", "No snippet"))
                                st.markdown(f"[Read Full Article]({row['Link']})")
                    with right:
                        st.markdown("#### Filters & Tips")
                        st.caption("Refine your query with product families, model numbers, or recall terms.")
                        st.markdown(
                            "- Add region-specific terms (MHRA, EMA, ANVISA)\n"
                            "- Include incident keywords (injury, field safety, warning)"
                        )
                        st.markdown("#### Quick Queries")
                        st.code(
                            "“{query}” safety alert\n"
                            f"site:gov {query}\n"
                            f"{query} field safety notice",
                            language="text",
                        )
                else:
                    st.warning("No results found. Try broadening your search terms.")
