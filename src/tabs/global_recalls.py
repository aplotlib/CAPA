import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from src.services.regulatory_service import RegulatoryService
from src.services.agent_service import RecallResponseAgent

def get_ai_service():
    """Retrieves AI Service from session state."""
    return st.session_state.get('ai_service')

@st.cache_data(ttl=3600, show_spinner=False)
def search_wrapper(term, start, end):
    return RegulatoryService.search_all_sources(term, start, end, limit=200)

def display_recalls_tab():
    st.header("🌍 Regulatory Intelligence & Reputation Monitor")
    st.caption("Deep-scan surveillance: Recalls, Adverse Events (MAUDE), and Negative Media.")

    ai = get_ai_service()
    
    # Initialize Session State
    if 'recall_hits' not in st.session_state or st.session_state.recall_hits is None: 
        st.session_state.recall_hits = pd.DataFrame()
    if 'recall_log' not in st.session_state: 
        st.session_state.recall_log = {}

    p_info = st.session_state.get('product_info', {})
    default_name = p_info.get('name', '')
    default_manufacturer = p_info.get('manufacturer', '')
    default_model = p_info.get('model', '')

    # --- TABS FOR MODES ---
    tab_single, tab_bulk = st.tabs(["🤖 Single Agent Mode", "🚀 Bulk Fleet Surveillance"])

    # =========================================================================
    # TAB 1: SINGLE AGENT (Existing Logic)
    # =========================================================================
    with tab_single:
        with st.expander("🤖 Autonomous Safety & Media Agent", expanded=True):
            st.info("The Agent scans Recalls, Adverse Events, and Global News. It drafts CAPAs for safety risks and PR Statements for media risks.")
            
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                agent_term = st.text_input("Surveillance Target", value=default_name, placeholder="e.g. Infusion Pump", key="agent_term")
            with c2:
                agent_firm = st.text_input("My Firm Name", value=default_manufacturer, placeholder="e.g. Acme MedCorp", key="agent_firm")
            with c3:
                st.write("") 
                start_btn = st.button("🚀 Launch Agent", type="primary", width="stretch")

            if start_btn:
                if not ai:
                    st.error("AI Service not connected.")
                else:
                    agent = RecallResponseAgent()
                    log_container = st.container()
                    log_container.markdown("### 📡 Agent Live Feed")
                    log_box = log_container.empty()
                    
                    with st.spinner("Agent is scanning global data sources..."):
                        model_id = default_model if default_model else "General Device Class"
                        logs, artifacts = agent.run_mission(agent_term, agent_firm, model_id)
                        
                        log_text = ""
                        for line in logs:
                            log_text += f"{line}  \n"
                            log_box.markdown(f"```text\n{log_text}\n```")
                            time.sleep(0.05) 
                    
                    st.session_state.agent_artifacts = artifacts
                    st.success("Mission Complete!")

        # --- SINGLE AGENT RESULTS ---
        if 'agent_artifacts' in st.session_state and st.session_state.agent_artifacts:
            st.divider()
            st.subheader(f"📦 Agent Action Packages ({len(st.session_state.agent_artifacts)})")
            
            for i, art in enumerate(st.session_state.agent_artifacts):
                rec = art['source_record']
                source_type = art.get('source_type', 'Unknown')
                risk_analysis = art.get('risk_analysis', 'N/A')
                
                icon = "📰" if "Media" in source_type else "💀" if "MAUDE" in source_type else "🚨"
                
                with st.expander(f"{icon} ALERT [{source_type}]: {rec['Product'][:60]}...", expanded=True):
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        st.markdown("### ⚠️ Threat Detected")
                        st.error(f"**Risk Analysis:** {risk_analysis}")
                        st.write(f"**Issue:** {rec['Reason']}")
                        st.write(f"**Source:** {rec['Source']}")
                    
                    with col_right:
                        st.markdown("### 🤖 Generated Assets")
                        
                        if art.get('capa_draft'):
                            if st.button(f"📥 Save Draft CAPA", key=f"btn_capa_{i}"):
                                if 'capa_records' not in st.session_state: st.session_state.capa_records = []
                                cd = art['capa_draft']
                                new_capa = {
                                    "id": f"AUTO-{len(st.session_state.capa_records)+1:03d}",
                                    "issue": cd.get('issue_description', 'Auto-generated'),
                                    "root_cause": cd.get('root_cause_investigation_plan', 'TBD'),
                                    "actions": cd.get('containment_action', 'TBD'),
                                    "date": str(datetime.now().date())
                                }
                                st.session_state.capa_records.append(new_capa)
                                st.toast("CAPA saved!")

                        if art.get('email_draft'):
                            with st.popover("✉️ View Vendor Email"):
                                st.text_area("Subject: Urgent Inquiry", value=art['email_draft'], height=200, key=f"email_{i}")

                        if art.get('pr_draft'):
                            with st.popover("🎤 View PR Statement"):
                                st.info("Holding Statement for Media Inquiries:")
                                st.text_area("PR Draft", value=art['pr_draft'], height=200, key=f"pr_{i}")

        # --- MANUAL SEARCH SECTION (Moved inside Tab 1) ---
        st.divider()
        with st.expander("🛠️ Manual Search & Screening Configuration", expanded=False):
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("1. Search Criteria")
                p_name = st.text_input("Search Term / Product Type", value=default_name, placeholder="e.g. Infusion Pump", key="manual_search_term")
                
                # Date Presets logic
                st.write("Date Range Presets:")
                d_cols = st.columns(5)
                days_lookup = {0: 30, 1: 60, 2: 90, 3: 180, 4: 365}
                preset_clicked = None
                
                for idx, days in days_lookup.items():
                     if d_cols[idx].button(f"{days}D", key=f"d_btn_{days}"):
                         preset_clicked = days
                
                if 'manual_start_date' not in st.session_state: st.session_state.manual_start_date = datetime.now() - timedelta(days=90)
                if 'manual_end_date' not in st.session_state: st.session_state.manual_end_date = datetime.now()

                if preset_clicked:
                    st.session_state.manual_start_date = datetime.now() - timedelta(days=preset_clicked)
                    st.session_state.manual_end_date = datetime.now()
                    st.rerun()

                c_d1, c_d2 = st.columns(2)
                start_date = c_d1.date_input("Start Date", value=st.session_state.manual_start_date, key="man_start")
                end_date = c_d2.date_input("End Date", value=st.session_state.manual_end_date, key="man_end")

            with col2:
                st.subheader("2. 'My Product' Match Criteria")
                my_firm = st.text_input("My Manufacturer Name", value=default_manufacturer, placeholder="e.g. Acme MedCorp", key="manual_firm")
                my_model = st.text_input("My Model Number/ID", value=default_model, placeholder="e.g. Model X-500", key="manual_model")

            auto_expand = st.checkbox("🤖 AI-Expanded Search (Synonyms)", value=True)
            
            if st.button("🚀 Run Deep Scan (Manual)", type="secondary", width="stretch"):
                if not p_name:
                    st.error("Enter a search query.")
                else:
                    st.session_state.recall_hits = pd.DataFrame()
                    st.session_state.recall_log = {}
                    run_search_logic(p_name, start_date, end_date, auto_expand, ai)
                    st.rerun()

        if not st.session_state.recall_hits.empty:
            df = st.session_state.recall_hits
            
            st.divider()
            c_act1, c_act2 = st.columns([2, 1])
            with c_act1: st.subheader(f"Findings: {len(df)} Records")
            with c_act2:
                if "AI_Risk_Level" not in df.columns:
                    if st.button("🤖 AI Screen for Relevance", type="secondary", width="stretch"):
                        if not ai or not ai.client:
                            st.error("AI Service not available.")
                        else:
                            with st.spinner(f"AI is screening {len(df)} records..."):
                                df = run_ai_screening(df, ai, my_firm, my_model, p_name)
                                st.session_state.recall_hits = df
                                st.rerun()

            tab_smart, tab_raw = st.tabs(["⚡ Smart Analysis View", "📊 Raw Data & Links"])
            with tab_smart:
                if "AI_Risk_Level" in df.columns:
                    risk_order = {"High": 0, "Medium": 1, "Low": 2, "TBD": 3}
                    df['sort_key'] = df['AI_Risk_Level'].map(risk_order).fillna(3)
                    df = df.sort_values('sort_key')
                    
                for index, row in df.iterrows():
                    risk = row.get("AI_Risk_Level", "Unscreened")
                    risk_color = "🔴" if risk == "High" else "🟠" if risk == "Medium" else "🟢" if risk == "Low" else "⚪"
                    src = row['Source']
                    icon = "📰" if "Media" in src else "💀" if "MAUDE" in src else "🏛️"
                    prod_name = str(row['Product'])[:60]
                    label = f"{risk_color} {icon} [{risk}] {row['Date']} | {src} | {prod_name}..."
                    
                    with st.expander(label):
                        c1, c2 = st.columns([3, 2])
                        with c1:
                            st.markdown(f"**Product:** {row['Product']}")
                            st.markdown(f"**Firm:** {row['Firm']}")
                            st.info(f"**Reason/Problem:** {row['Reason']}")
                            if row.get('Link') and row.get('Link') != "N/A":
                                st.markdown(f"👉 [**Open Official Source Record**]({row['Link']})")
                        with c2:
                            if "AI_Analysis" in row and row["AI_Analysis"]:
                                st.markdown("### 🤖 AI Analysis")
                                st.success(row["AI_Analysis"])
                            else:
                                st.caption("Click 'AI Screen for Relevance' to analyze this record.")
            with tab_raw:
                st.dataframe(df, column_config={"Link": st.column_config.LinkColumn("Source Link")}, width=1200)

    # =========================================================================
    # TAB 2: BULK SURVEILLANCE
    # =========================================================================
    with tab_bulk:
        st.subheader("🚀 Bulk Fleet Surveillance")
        st.info("Upload a list of products (SKU & Name) to scan regulatory databases for the entire fleet at once.")

        c_file, c_conf = st.columns([1, 1])
        
        with c_file:
            uploaded_file = st.file_uploader("Upload Product List (Excel/CSV)", type=['xlsx', 'csv'], help="Column A: SKU, Column B: Product Name")
            if uploaded_file:
                st.success(f"Loaded: {uploaded_file.name}")

        with c_conf:
            st.markdown("**Search Date Range**")
            # Presets for Bulk
            b_cols = st.columns(5)
            bulk_days_map = {0: 30, 1: 60, 2: 90, 3: 180, 4: 365}
            bulk_preset = None
            for idx, days in bulk_days_map.items():
                if b_cols[idx].button(f"{days}d", key=f"b_d_{days}"):
                    bulk_preset = days
            
            if 'bulk_lookback' not in st.session_state: st.session_state.bulk_lookback = 90
            if bulk_preset: 
                st.session_state.bulk_lookback = bulk_preset
                st.rerun()

            lookback = st.number_input("Lookback Period (Days)", value=st.session_state.bulk_lookback, min_value=1, max_value=3650)
            
            fuzzy_threshold = st.slider("Fuzzy Match Sensitivity", 0.0, 1.0, 0.6, 0.1, help="Higher = Stricter matching between your product name and the recall description.")

        st.divider()
        
        if st.button("🚀 Run Bulk Fleet Scan", type="primary", width="stretch"):
            if not uploaded_file:
                st.error("Please upload a file first.")
            else:
                agent = RecallResponseAgent()
                progress_bar = st.progress(0, "Initializing Bulk Scan...")
                status_text = st.empty()
                
                # Calculate start date
                b_start = datetime.now() - timedelta(days=lookback)
                
                with st.spinner("Processing fleet... This may take time based on fleet size."):
                    results_df, audit_log = agent.run_bulk_scan(
                        uploaded_file, 
                        b_start, 
                        datetime.now(),
                        fuzzy_threshold,
                        progress_callback=lambda p, msg: (progress_bar.progress(p), status_text.text(msg))
                    )
                
                progress_bar.empty()
                status_text.success("Bulk Scan Complete!")
                st.session_state.bulk_results = results_df
                st.balloons()

        # --- BULK RESULTS ---
        if 'bulk_results' in st.session_state and not st.session_state.bulk_results.empty:
            res = st.session_state.bulk_results
            
            st.subheader("📊 Fleet Scan Results")
            
            # KPI Cards
            k1, k2, k3 = st.columns(3)
            total_scanned = res['My SKU'].nunique()
            total_hits = len(res)
            high_risk = len(res[res['Risk Level'] == 'High'])
            
            k1.metric("Products Scanned", total_scanned)
            k2.metric("Total Matches Found", total_hits)
            k3.metric("High Risk Flags", high_risk)
            
            # Interactive Dataframe
            st.dataframe(
                res,
                column_config={
                    "Link": st.column_config.LinkColumn("Source Link"),
                    "Risk Level": st.column_config.Column(
                        "Risk",
                        help="Calculated based on source and keyword match",
                        width="small"
                    )
                },
                width=1200
            )
            
            # CSV Download
            csv = res.to_csv(index=False).encode('utf-8')
            st.download_button(
                "💾 Download Full Surveillance Report (CSV)",
                data=csv,
                file_name=f"Fleet_Surveillance_Report_{datetime.now().date()}.csv",
                mime="text/csv",
                type="primary",
                width="stretch"
            )
        elif 'bulk_results' in st.session_state:
            st.info("No relevant regulatory events found for the uploaded fleet in this time period.")


def run_search_logic(term, start, end, auto_expand, ai):
    terms = [term]
    if auto_expand and ai and ai.client:
        try:
            kws = ai.generate_search_keywords(term, "")
            if kws:
                st.toast(f"AI added synonyms: {', '.join(kws)}")
                terms.extend(kws)
        except: pass
    
    terms = list(set(terms))
    all_res = pd.DataFrame()
    logs = {}
    
    prog = st.progress(0, "Starting scan...")
    for i, t in enumerate(terms):
        prog.progress((i+1)/len(terms), f"Scanning for '{t}'...")
        hits, log = search_wrapper(t, start, end)
        all_res = pd.concat([all_res, hits])
        for k,v in log.items(): logs[k] = logs.get(k, 0) + v
        
    prog.empty()
    if not all_res.empty:
        all_res = all_res.drop_duplicates(subset=['ID'])
        if 'Date' in all_res.columns: all_res.sort_values('Date', ascending=False, inplace=True)
    
    st.session_state.recall_hits = all_res
    st.session_state.recall_log = logs

def run_ai_screening(df, ai, my_firm, my_model, query_term):
    target_df = df.head(30).copy() 
    analyses = []
    risks = []
    prog = st.progress(0, "AI Analyzing relevance...")
    total = len(target_df)
    
    for i, row in target_df.iterrows():
        prog.progress((i)/total, f"Analyzing record {i+1}/{total}...")
        record_text = f"Source: {row['Source']}\nProduct: {row['Product']}\nFirm: {row['Firm']}\nReason: {row['Reason']}"
        my_context = f"My Firm: {my_firm}\nMy Model: {my_model}\nSearch Term: {query_term}"
        
        try:
            result = ai.assess_relevance_json(my_context, record_text)
            analyses.append(result.get("analysis", "Analysis Failed"))
            risks.append(result.get("risk", "TBD"))
        except Exception as e:
            analyses.append(f"Error: {str(e)}")
            risks.append("TBD")
            
    prog.empty()
    target_df["AI_Analysis"] = analyses
    target_df["AI_Risk_Level"] = risks
    return target_df
