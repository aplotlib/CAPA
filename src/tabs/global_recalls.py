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
    st.header("🌍 Regulatory Intelligence & Recall Tracker")
    st.caption("Deep-scan surveillance with Autonomous Agent capabilities.")

    ai = get_ai_service()
    
    # Initialize Session State
    if 'recall_hits' not in st.session_state or st.session_state.recall_hits is None: 
        st.session_state.recall_hits = pd.DataFrame()
    if 'recall_log' not in st.session_state: 
        st.session_state.recall_log = {}

    # Safe get for product info (used by both Agent and Manual tools)
    p_info = st.session_state.get('product_info', {})
    default_name = p_info.get('name', '')
    default_manufacturer = p_info.get('manufacturer', '')
    default_model = p_info.get('model', '')

    # --- 🤖 SECTION 1: AUTONOMOUS AGENT ---
    with st.expander("🤖 Autonomous Recall Response Agent", expanded=True):
        st.info("The Agent will scan global databases, analyze risks, and **automatically draft CAPAs and Emails** for high-risk findings.")
        
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            agent_term = st.text_input("Surveillance Target", value=default_name, placeholder="e.g. Infusion Pump", key="agent_term")
        with c2:
            agent_firm = st.text_input("My Firm Name", value=default_manufacturer, placeholder="e.g. Acme MedCorp", key="agent_firm")
        with c3:
            st.write("") # Spacer to align button
            start_btn = st.button("🚀 Launch Agent", type="primary", use_container_width=True)

        if start_btn:
            if not ai:
                st.error("AI Service not connected.")
            else:
                agent = RecallResponseAgent()
                
                # Container for live logs
                log_container = st.container()
                log_container.markdown("### 📡 Agent Live Feed")
                log_box = log_container.empty()
                
                with st.spinner("Agent is executing mission..."):
                    # Run the agent
                    # Using default_model or a placeholder if missing
                    model_id = default_model if default_model else "General Device Class"
                    logs, artifacts = agent.run_mission(agent_term, agent_firm, model_id)
                    
                    # Simulate streaming logs for UX
                    log_text = ""
                    for line in logs:
                        log_text += f"{line}  \n"
                        log_box.markdown(f"```text\n{log_text}\n```")
                        time.sleep(0.05) 
                
                # Store results
                st.session_state.agent_artifacts = artifacts
                st.success("Mission Complete!")

    # --- 📦 SECTION 2: AGENT RESULTS ---
    if 'agent_artifacts' in st.session_state and st.session_state.agent_artifacts:
        st.divider()
        st.subheader(f"📦 Agent Action Packages ({len(st.session_state.agent_artifacts)})")
        
        for i, art in enumerate(st.session_state.agent_artifacts):
            rec = art['source_record']
            risk_analysis = art.get('risk_analysis', 'N/A')
            
            with st.expander(f"🚨 ACTION ITEM: {rec['Product'][:60]}...", expanded=True):
                col_left, col_right = st.columns(2)
                
                with col_left:
                    st.markdown("### ⚠️ Threat Detected")
                    st.error(f"**Risk Analysis:** {risk_analysis}")
                    st.write(f"**Reason:** {rec['Reason']}")
                    st.write(f"**Source:** {rec['Source']}")
                    st.caption(f"Firm: {rec['Firm']}")
                
                with col_right:
                    st.markdown("### 🤖 Generated Assets")
                    
                    # CAPA DRAFT BUTTON
                    if st.button(f"📥 Save as Draft CAPA", key=f"btn_capa_{i}"):
                        if 'capa_records' not in st.session_state: st.session_state.capa_records = []
                        
                        capa_data = art.get('capa_draft', {})
                        new_capa = {
                            "id": f"AUTO-CAPA-{len(st.session_state.capa_records)+1:03d}",
                            "issue": capa_data.get('issue_description', 'Auto-generated issue'),
                            "root_cause": capa_data.get('root_cause_investigation_plan', 'TBD'),
                            "actions": capa_data.get('containment_action', 'TBD'),
                            "date": str(datetime.now().date())
                        }
                        st.session_state.capa_records.append(new_capa)
                        st.toast("CAPA saved to database!")

                    # EMAIL DRAFT POPOVER
                    email_body = art.get('email_draft', "No email generated.")
                    with st.popover("✉️ View Vendor Email Draft"):
                        st.markdown("#### Draft Vendor Communication")
                        st.text_area("Subject: Urgent - Recall Inquiry", value=email_body, height=300, key=f"email_{i}")

    st.divider()

    # --- 🛠️ SECTION 3: MANUAL TOOLS (Original Logic) ---
    with st.expander("🛠️ Manual Search & Screening Configuration", expanded=False):
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("1. Search Criteria")
            p_name = st.text_input("Search Term / Product Type", value=default_name, placeholder="e.g. Infusion Pump", key="manual_search_term")
            c_d1, c_d2 = st.columns(2)
            start_date = c_d1.date_input("Start Date", value=datetime.now() - timedelta(days=365*3))
            end_date = c_d2.date_input("End Date", value=datetime.now())

        with col2:
            st.subheader("2. 'My Product' Match Criteria")
            st.caption("AI uses this to flag high-risk matches.")
            my_firm = st.text_input("My Manufacturer Name", value=default_manufacturer, placeholder="e.g. Acme MedCorp", key="manual_firm")
            my_model = st.text_input("My Model Number/ID", value=default_model, placeholder="e.g. Model X-500", key="manual_model")

        auto_expand = st.checkbox("🤖 AI-Expanded Search (Synonyms)", value=True)
        
        if st.button("🚀 Run Deep Scan (Manual)", type="secondary", use_container_width=True):
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
                if st.button("🤖 AI Screen for Relevance", type="secondary", use_container_width=True):
                    if not ai or not ai.model:
                        st.error("AI Service not available (Check API Key).")
                    else:
                        with st.spinner(f"AI is screening {len(df)} records against '{my_firm}' / '{my_model}'..."):
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
                
                prod_name = str(row['Product'])[:60]
                label = f"{risk_color} [{risk}] {row['Date']} | {src} | {prod_name}..."
                
                with st.expander(label):
                    c1, c2 = st.columns([3, 2])
                    with c1:
                        st.markdown(f"**Product:** {row['Product']}")
                        st.markdown(f"**Firm:** {row['Firm']}")
                        st.markdown(f"**Model Info:** {row.get('Model Info', 'N/A')}")
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
            st.dataframe(df, column_config={"Link": st.column_config.LinkColumn("Source Link")}, use_container_width=True)
            st.divider()
            if st.button("📄 Generate DOCX Report"):
                if 'doc_generator' in st.session_state:
                    doc_buffer = st.session_state.doc_generator.generate_regulatory_report_docx(
                        df, 
                        p_name, 
                        st.session_state.recall_log
                    )
                    st.download_button(
                        "Download DOCX", 
                        doc_buffer, 
                        "Regulatory_Report.docx", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                else:
                    st.error("Document Generator service missing.")

def run_search_logic(term, start, end, auto_expand, ai):
    terms = [term]
    if auto_expand and ai and ai.model:
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
        # Drop duplicates based on ID if available, otherwise strict duplicate check
        all_res = all_res.drop_duplicates(subset=['ID'])
        if 'Date' in all_res.columns: all_res.sort_values('Date', ascending=False, inplace=True)
    
    st.session_state.recall_hits = all_res
    st.session_state.recall_log = logs

def run_ai_screening(df, ai, my_firm, my_model, query_term):
    # Limit to top 30 to save tokens/time for demo
    target_df = df.head(30).copy() 
    analyses = []
    risks = []
    prog = st.progress(0, "AI Analyzing relevance...")
    total = len(target_df)
    
    for i, row in target_df.iterrows():
        prog.progress((i)/total, f"Analyzing record {i+1}/{total}...")
        record_text = f"Product: {row['Product']}\nFirm: {row['Firm']}\nReason: {row['Reason']}\nModels: {row.get('Model Info', '')}"
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
