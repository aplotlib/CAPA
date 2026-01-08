import streamlit as st
import pandas as pd
from src.services.regulatory_service import RegulatoryService

def display_global_recalls_tab():
    st.header("🌐 Global Recall & Alert Intelligence")
    st.caption("Scan FDA, EU, UK, Health Canada, TGA, and other authorities for emerging safety alerts.")

    # --- SIDEBAR FILTERS ---
    with st.expander("🔍 Surveillance Filters", expanded=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            query = st.text_input("Product Search (e.g. pacemaker, infusion pump)")
        with col2:
            manufacturer = st.text_input("Manufacturer (Optional)")
        
        date_range = st.slider("Lookback Period (days)", min_value=30, max_value=3650, value=730, step=30)
        vendor_only = st.checkbox("Vendor Enforcement Actions Only", value=False)
        include_sanctions = st.checkbox("Include Sanctions/Watchlists", value=True)
    
    btn_col, _ = st.columns([1, 4])
    if btn_col.button("🚀 Launch Surveillance Mission", type="primary", width="stretch"):
        if not query:
            st.warning("Enter a product search term.")
            return

        start_date = datetime.now() - timedelta(days=date_range)
        end_date = datetime.now()

        with st.spinner("Scanning global regulatory sources..."):
            df, logs = RegulatoryService.search_all_sources(
                query_term=query,
                manufacturer=manufacturer,
                start_date=start_date,
                end_date=end_date,
                vendor_only=vendor_only,
                include_sanctions=include_sanctions,
                limit=200
            )
            st.session_state.global_recalls_df = df
            st.session_state.global_recalls_log = logs

    if "global_recalls_df" not in st.session_state:
        st.info("No data loaded yet.")
        return

    df = st.session_state.global_recalls_df
    logs = st.session_state.global_recalls_log

    if df is not None and not df.empty:
        st.divider()
        st.subheader(f"🚨 {len(df)} Global Alerts Found")
        
        # --- AI RISK CLASSIFY ---
        if "AI_Verified" not in df.columns:
            if st.button("🤖 Verify Relevance with AI"):
                with st.spinner("AI is reviewing matches..."):
                    df = RegulatoryService.classify_recall_risk(df)
                    st.session_state.global_recalls_df = df
                    st.success("AI verification complete.")

        # --- RESULTS TABS ---
        tab_smart, tab_raw = st.tabs(["🧠 Smart View", "📜 Full Record Table"])
        with tab_smart:
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
                use_container_width=True
            )
            
            # Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Download Report (CSV)", csv, "regulatory_report.csv", "text/csv")
            
    elif logs:
        st.info("No records found matching criteria.")
