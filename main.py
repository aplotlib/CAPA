# main.py
from __future__ import annotations

import os
import time
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

# Import the Unified Service and AI Factory
from src.services.regulatory_service import RegulatoryService
from src.ai_services import get_ai_service

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="CAPA Regulatory Agent", 
    layout="wide", 
    page_icon="🛡️"
)

# ============================================================
# SESSION & API SETUP
# ============================================================
def init_session():
    # Ensure API keys are accessible to the Service
    # We check secrets first, then env vars
    if "GOOGLE_API_KEY" not in st.secrets and "GOOGLE_API_KEY" in os.environ:
        # Streamlit secrets are immutable, so we rely on the Service checking os.environ as fallback
        pass 

    # Initialize AI Service
    if 'ai_service' not in st.session_state:
        # Attempt to grab key from secrets
        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            st.session_state.api_key = api_key
            get_ai_service() # Triggers init inside ai_services.py

init_session()
ai = get_ai_service()

# ============================================================
# SIDEBAR CONFIGURATION
# ============================================================
st.sidebar.title("🛡️ Mission Control")

st.sidebar.header("1. Search Scope")
# Date Selection
date_mode = st.sidebar.selectbox(
    "Time Window",
    ["Last 30 days", "Last 90 days", "Last 1 Year", "Last 2 Years", "Custom"],
    index=2
)

if date_mode == "Custom":
    start_date = st.sidebar.date_input("Start", value=date.today() - timedelta(days=365))
    end_date = st.sidebar.date_input("End", value=date.today())
else:
    days_map = {"Last 30 days": 30, "Last 90 days": 90, "Last 1 Year": 365, "Last 2 Years": 730}
    days = days_map.get(date_mode, 365)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

st.sidebar.caption(f"📅 Range: {start_date} → {end_date}")

# Region Selection
st.sidebar.header("2. Target Regions")
regions = []
c1, c2 = st.sidebar.columns(2)
with c1:
    if st.checkbox("🇺🇸 US (FDA/CPSC)", value=True): regions.append("US")
    if st.checkbox("🇪🇺 EU (EMA/MDR)", value=True): regions.append("EU")
with c2:
    if st.checkbox("🇬🇧 UK (MHRA)", value=True): regions.append("UK")
    if st.checkbox("🌎 LATAM (Anvisa)", value=True): regions.append("LATAM")

if st.sidebar.checkbox("🌏 APAC (TGA/PMDA)", value=False): regions.append("APAC")

# Mode Selection
st.sidebar.header("3. Intelligence Level")
mode_select = st.sidebar.radio(
    "Agent Mode",
    ["⚡ Fast (APIs + Snippets)", "🧠 Powerful (Agentic Verify)"],
    help="Fast: Quick scan of headlines. Powerful: AI visits links, reads content, and verifies relevance (Slower)."
)
search_mode = "powerful" if "Powerful" in mode_select else "fast"

# ============================================================
# MAIN TABS
# ============================================================
st.title("🛡️ Global Regulatory Intelligence Agent")
st.markdown(f"**Active Scope:** {', '.join(regions)} | **Mode:** {search_mode.upper()}")

tab1, tab2 = st.tabs(["🔎 Single Target Search", "📂 Batch Fleet Scan"])

# ------------------------------------------------------------
# TAB 1: SINGLE SEARCH
# ------------------------------------------------------------
with tab1:
    col_search, col_act = st.columns([3, 1])
    with col_search:
        query = st.text_input("Enter Product Name / Keyword", placeholder="e.g. Infusion Pump, Pacemaker Lead...")
    with col_act:
        st.write("")
        st.write("")
        run_btn = st.button("🚀 Run Surveillance", type="primary", use_container_width=True)

    if run_btn and query:
        if search_mode == "powerful" and not ai:
            st.error("⚠️ Powerful mode requires OpenAI API Key. Please check secrets.")
        else:
            with st.status(f"Agent running {search_mode} surveillance...", expanded=True) as status:
                st.write("📡 Connecting to Global Regulatory Databases...")
                
                # CALL THE UNIFIED SERVICE
                df, logs = RegulatoryService.search_all_sources(
                    query_term=query,
                    regions=regions,
                    start_date=start_date,
                    end_date=end_date,
                    limit=100,
                    mode=search_mode,
                    ai_service=ai
                )
                
                status.write(f"✅ Search Complete. Found {len(df)} records.")
                status.update(label="Mission Complete", state="complete", expanded=False)

            # METRICS
            if logs:
                m_cols = st.columns(len(logs))
                for i, (k, v) in enumerate(logs.items()):
                    m_cols[i].metric(k, v)
            
            st.divider()

            # RESULTS
            if not df.empty:
                # 1. Smart View (Expander)
                st.subheader("📝 Key Findings")
                
                # Sort: Verified -> High Risk -> Date
                if "AI_Verified" in df.columns:
                    df["_sort"] = df["AI_Verified"].apply(lambda x: 1 if x else 0)
                    df = df.sort_values(by=["_sort", "Risk_Level", "Date"], ascending=[False, True, False])

                for _, row in df.iterrows():
                    risk = row.get("Risk_Level", "Medium")
                    icon = "🔴" if risk == "High" else "🟠" if risk == "Medium" else "🟢"
                    verified = "✅ VERIFIED" if row.get("AI_Verified") else ""
                    
                    title = f"{icon} {row['Source']} | {row['Date']} | {row['Product'][:60]}... {verified}"
                    
                    with st.expander(title):
                        cA, cB = st.columns([3, 1])
                        with cA:
                            st.markdown(f"**Issue:** {row['Reason']}")
                            st.markdown(f"**Description:** {row['Description']}")
                            st.caption(f"Manufacturer: {row['Firm']}")
                        with cB:
                            st.link_button("🔗 Open Source", row['Link'])
                            if row.get("AI_Verified"):
                                st.success("Confirmed relevant by Agent")

                # 2. Data Table
                st.subheader("📊 Full Dataset")
                st.dataframe(
                    df, 
                    use_container_width=True,
                    column_config={"Link": st.column_config.LinkColumn("URL")}
                )

                # Export
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("💾 Download Report (CSV)", csv, f"Report_{query}_{date.today()}.csv", "text/csv")
            else:
                st.warning("No records found matching your criteria.")

# ------------------------------------------------------------
# TAB 2: BATCH SCAN
# ------------------------------------------------------------
with tab2:
    st.info("Upload a CSV/Excel with columns: **SKU**, **Product Name**")
    uploaded_file = st.file_uploader("Upload Fleet File", type=["csv", "xlsx"])
    
    if uploaded_file and st.button("🚀 Scan Entire Fleet"):
        # Load File
        try:
            if uploaded_file.name.endswith('.csv'): 
                input_df = pd.read_csv(uploaded_file)
            else: 
                input_df = pd.read_excel(uploaded_file)
            
            # Normalize Headers
            input_df.columns = [c.strip() for c in input_df.columns]
            if "Product Name" not in input_df.columns:
                st.error("File must have a 'Product Name' column.")
                st.stop()
                
            products = input_df["Product Name"].unique()
            
            all_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, prod in enumerate(products):
                status_text.text(f"Scanning: {prod} ({i+1}/{len(products)})...")
                progress_bar.progress((i+1)/len(products))
                
                # Execute Search
                hits, _ = RegulatoryService.search_all_sources(
                    str(prod), regions, start_date, end_date, limit=20, mode=search_mode, ai_service=ai
                )
                
                if not hits.empty:
                    hits["Queried_Product"] = prod
                    all_results.append(hits)
            
            progress_bar.empty()
            status_text.success("Fleet Scan Complete!")
            
            if all_results:
                final_df = pd.concat(all_results)
                st.dataframe(final_df, use_container_width=True)
                
                csv_batch = final_df.to_csv(index=False).encode('utf-8')
                st.download_button("💾 Download Fleet Report", csv_batch, "Fleet_Report.csv", "text/csv")
            else:
                st.info("No findings for the uploaded fleet.")

        except Exception as e:
            st.error(f"Error processing file: {e}")
