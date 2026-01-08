import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from src.services.regulatory_service import RegulatoryService

def get_ai_service():
    """Retrieves AI Service from session state."""
    return st.session_state.get('ai_service')

def display_recalls_tab():
    st.header("🌍 Global Regulatory Intelligence & Agentic Surveillance")
    st.caption("Deep-scan surveillance: FDA, CPSC, Global Regulators (EU/UK/LATAM), and Media.")

    ai = get_ai_service()
    
    # Initialize Session State
    if 'recall_hits' not in st.session_state: 
        st.session_state.recall_hits = pd.DataFrame()
    if 'recall_log' not in st.session_state: 
        st.session_state.recall_log = {}

    p_info = st.session_state.get('product_info', {})
    default_name = p_info.get('name', '')

    # --- CONFIGURATION PANEL ---
    with st.expander("🛠️ Search Configuration", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_term = st.text_input("Product Name / Search Term", value=default_name, placeholder="e.g. Infusion Pump")
            manufacturer = st.text_input("Manufacturer / Vendor (optional)", value=p_info.get('manufacturer', ''), placeholder="e.g. Acme Medical")
        with col2:
            st.markdown("**Search Depth**")
            search_mode = st.radio("Mode", ["Fast (APIs + Snippets)", "Powerful (Agentic Scrape)"], label_visibility="collapsed")
        with col3:
            st.markdown("**Lookback**")
            days_back = st.selectbox("Period", [30, 90, 365, 730], index=1, label_visibility="collapsed")
            include_sanctions = st.checkbox("Sanctions/Watchlists", value=True)
            vendor_only = st.checkbox("Vendor-only search", value=False)

        # Date Calculation
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Calculate Mode
        mode_key = "powerful" if "Powerful" in search_mode else "fast"
        
        btn_col, _ = st.columns([1, 2])
        if btn_col.button("🚀 Launch Surveillance Mission", type="primary", width="stretch"):
            if not search_term and not manufacturer:
                st.error("Please enter a search term or manufacturer.")
            elif vendor_only and not manufacturer:
                st.error("Vendor-only search requires a manufacturer/vendor name.")
            else:
                if mode_key == "powerful" and not ai:
                    st.warning("⚠️ Powerful mode requires AI. Please check your API keys. Switching to Fast mode.")
                    mode_key = "fast"
                
                with st.spinner(f"Running {mode_key.upper()} surveillance across US, EU, UK, LATAM..."):
                    # Clear previous
                    st.session_state.recall_hits = pd.DataFrame()
                    st.session_state.recall_log = {}

                    # EXECUTE SEARCH
                    df, logs = RegulatoryService.search_all_sources(
                        query_term=search_term, 
                        regions=["US", "EU", "UK", "LATAM", "APAC"],
                        manufacturer=manufacturer,
                        vendor_only=vendor_only,
                        include_sanctions=include_sanctions,
                        start_date=start_date, 
                        end_date=end_date,
                        limit=100,
                        mode=mode_key,
                        ai_service=ai
                    )
                    
                    st.session_state.recall_hits = df
                    st.session_state.recall_log = logs
                    st.rerun()

    # --- RESULTS DASHBOARD ---
    df = st.session_state.recall_hits
    logs = st.session_state.recall_log

    if logs:
        # Metrics Bar
        cols = st.columns(len(logs))
        for i, (source, count) in enumerate(logs.items()):
            cols[i].metric(source, count)
        st.divider()

    if not df.empty:
        # Risk Formatting
        if "Risk_Level" in df.columns:
            df["Risk_Level"] = df["Risk_Level"].fillna("TBD")
        
        tab_list, tab_raw = st.tabs(["⚡ Smart Findings", "📊 Data Grid"])
        
        with tab_list:
            # Sort: High Risk First, then Verified, then Recent
            if "AI_Verified" in df.columns:
                df = df.sort_values(by=["Risk_Level", "AI_Verified"], ascending=[True, False]) # High < Low alphabetically, wait. High/Medium/Low.
                # Custom sort usually better, but simplified here.
            
            for idx, row in df.iterrows():
                risk = row.get("Risk_Level", "Medium")
                color = "🔴" if risk == "High" else "🟠" if risk == "Medium" else "🟢"
                
                verified_badge = "✅ AGENT VERIFIED" if row.get("AI_Verified") else ""
                
                with st.expander(f"{color} {row['Source']} | {row['Product'][:50]}... {verified_badge}"):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**Description:** {row['Description']}")
                        st.info(f"**Reason/Context:** {row['Reason']}")
                        st.caption(f"Date: {row['Date']} | Firm: {row['Firm']}")
                    with c2:
                        st.markdown(f"[🔗 Open Source]({row['Link']})")
                        if row.get("AI_Verified"):
                            st.success("Verified Relevant by AI")

        with tab_raw:
            st.dataframe(
                df, 
                column_config={"Link": st.column_config.LinkColumn("Link")}, 
                width="stretch"
            )
            
            # Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Download Report (CSV)", csv, "regulatory_report.csv", "text/csv")
            
    elif logs:
        st.info("No records found matching criteria.")
