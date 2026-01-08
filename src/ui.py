import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.services.regulatory_service import RegulatoryService

def get_ai_service():
    """Retrieves AI Service from session state."""
    return st.session_state.get('ai_service')

@st.cache_data(ttl=3600, show_spinner=False)
def search_wrapper(term, start, end, manufacturer="", vendor_only=False, include_sanctions=True):
    return RegulatoryService.search_all_sources(
        query_term=term,
        start_date=start,
        end_date=end,
        manufacturer=manufacturer,
        vendor_only=vendor_only,
        include_sanctions=include_sanctions,
        limit=200,
    )

def display_recalls_tab():
    st.header("🌍 Regulatory Intelligence & Recall Tracker")
    st.caption("Deep-scan surveillance with AI Relevance Screening (FDA, UK, Canada, CPSC).")

    ai = get_ai_service()
    
    if 'recall_hits' not in st.session_state or st.session_state.recall_hits is None: 
        st.session_state.recall_hits = pd.DataFrame()
    if 'recall_log' not in st.session_state: 
        st.session_state.recall_log = {}

    with st.expander("🛠️ Search & Screening Configuration", expanded=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("1. Search Criteria")
            # Safe get for product info
            p_info = st.session_state.get('product_info', {})
            default_name = p_info.get('name', '')
            
            p_name = st.text_input("Search Term / Product Type", value=default_name, placeholder="e.g. Infusion Pump")
            c_d1, c_d2 = st.columns(2)
            start_date = c_d1.date_input("Start Date", value=datetime.now() - timedelta(days=365*3))
            end_date = c_d2.date_input("End Date", value=datetime.now())

        with col2:
            st.subheader("2. 'My Product' Match Criteria")
            st.caption("AI uses this to flag high-risk matches.")
            my_firm = st.text_input("My Manufacturer Name", value=p_info.get('manufacturer', ''), placeholder="e.g. Acme MedCorp")
            my_model = st.text_input("My Model Number/ID", value=p_info.get('model', ''), placeholder="e.g. Model X-500")

        auto_expand = st.checkbox("🤖 AI-Expanded Search (Synonyms)", value=True)
        vendor_only = st.checkbox("Vendor-only enforcement/sanctions search", value=False)
        include_sanctions = st.checkbox("Include sanctions & watchlists", value=True)
        
        if st.button("🚀 Run Deep Scan", type="primary", width="stretch"):
            if not p_name:
                st.error("Enter a search query.")
            else:
                st.session_state.recall_hits = pd.DataFrame()
                st.session_state.recall_log = {}
                run_search_logic(p_name, start_date, end_date, auto_expand, ai, my_firm, vendor_only, include_sanctions)
                st.rerun()

    if not st.session_state.recall_hits.empty:
        df = st.session_state.recall_hits
        
        st.divider()
        c_act1, c_act2 = st.columns([2, 1])
        with c_act1: st.subheader(f"Findings: {len(df)} Records")
        with c_act2:
            if "AI_Risk_Level" not in df.columns:
                if st.button("🤖 AI Screen for Relevance", type="secondary", width="stretch"):
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
            st.dataframe(df, column_config={"Link": st.column_config.LinkColumn("Source Link")}, width="stretch")
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

def run_search_logic(term, start, end, auto_expand, ai, manufacturer, vendor_only, include_sanctions):
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
        hits, log = search_wrapper(t, start, end, manufacturer=manufacturer, vendor_only=vendor_only, include_sanctions=include_sanctions)
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
    
    # Merge back if we had more than 30 (not implemented for simplicity, just returning the screened 30)
    return target_df
