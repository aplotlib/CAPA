import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.ai_services import get_ai_service
from src.services.regulatory_service import RegulatoryService

def display_recalls_tab():
    st.header("🌍 Global Regulatory Intelligence Agent")
    st.caption("AI-powered surveillance of FDA (Devices, Drugs, Food) and CPSC databases.")

    ai = get_ai_service()
    
    if 'recall_hits' not in st.session_state:
        st.session_state.recall_hits = pd.DataFrame()
    if 'recall_log' not in st.session_state:
        st.session_state.recall_log = {}

    # --- INPUT SECTION ---
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("1. Configure Search Target")
            
            # Default Values
            default_name = ""
            default_desc = ""
            if 'product_info' in st.session_state:
                default_name = st.session_state.product_info.get('name', '')
                default_desc = st.session_state.product_info.get('ifu', '')
            
            p_name = st.text_input("Product Name / Type / Firm", value=default_name, placeholder="e.g. Infusion Pump OR Medtronic")
            p_desc = st.text_area("Description (for AI Context)", value=default_desc, height=68, help="AI uses this to find synonyms.")
            
            # NEW: Date Range Filter
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                # Default to last 3 years
                default_start = datetime.now() - timedelta(days=365*3)
                start_date = st.date_input("Start Date", value=default_start)
            with c_d2:
                end_date = st.date_input("End Date", value=datetime.now())

        with col2:
            st.write("###") 
            st.write("###") 
            auto_expand = st.checkbox("🤖 AI-Expanded Search", value=True, help="Automatically searches synonyms (e.g. 'Cardiac' for 'Heart')")
            
            if st.button("🚀 Run Scan", type="primary", use_container_width=True):
                if not p_name:
                    st.error("Enter a product or firm name.")
                else:
                    # Clear previous results
                    st.session_state.recall_hits = pd.DataFrame()
                    st.session_state.recall_log = {}
                    
                    run_search(p_name, p_desc, start_date, end_date, auto_expand, ai)
                    st.rerun()

    # --- SEARCH STATUS BOARD ---
    if st.session_state.recall_log:
        st.write("### 📡 Database Status")
        cols = st.columns(4)
        log = st.session_state.recall_log
        
        def show_metric(col, label, key):
            count = log.get(key, 0)
            with col:
                if count > 0:
                    st.metric(label, f"{count} Found", delta="Active Hits", delta_color="inverse")
                else:
                    st.metric(label, "0 Found", delta="Clear", delta_color="off")

        show_metric(cols[0], "FDA Devices", "FDA Device")
        show_metric(cols[1], "FDA Drugs", "FDA Drug")
        show_metric(cols[2], "FDA Food", "FDA Food")
        show_metric(cols[3], "CPSC (Consumer)", "CPSC")
        st.divider()

    # --- RESULTS LIST ---
    if not st.session_state.recall_hits.empty:
        df = st.session_state.recall_hits
        st.subheader(f"Detailed Findings ({len(df)})")
        
        # Tabs for View vs Export
        tab_list, tab_raw = st.tabs(["⚡ Smart Action View", "📋 Raw Data & Export"])
        
        with tab_list:
            st.info("Review findings. Use buttons to draft CAPAs or update Risk Files.")
            
            # Show top 50 to keep UI snappy
            for index, row in df.head(50).iterrows():
                icon = "💊" if "Drug" in row['Source'] else "🛠️" if "Device" in row['Source'] else "🧸"
                
                # Title string handling
                title_str = str(row['Product'])[:70] if row['Product'] else "No Description"
                
                with st.expander(f"{icon} **{row['Date']}** | {row['Source']} | {title_str}..."):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**Reason:** {row['Reason']}")
                        st.markdown(f"**Firm:** {row['Firm']}")
                        st.caption(f"ID: {row['ID']}")
                    
                    with c2:
                        # Unique keys for buttons
                        if st.button("📝 Draft CAPA", key=f"capa_{row['ID']}_{index}"):
                            create_capa_draft(row)
                        if st.button("⚠️ Add to FMEA", key=f"fmea_{row['ID']}_{index}"):
                            add_to_fmea(row)

        with tab_raw:
            c_ex1, c_ex2 = st.columns([1, 4])
            with c_ex1:
                # EXPORT BUTTON
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name="regulatory_search_results.csv",
                    mime="text/csv",
                    type="primary"
                )
            
            st.dataframe(df, use_container_width=True)
    
    elif st.session_state.recall_log:
        st.success("Search complete. No recalls found matching criteria.")

def run_search(name, desc, start_date, end_date, auto_expand, ai):
    """Orchestrates the search logic."""
    search_terms = [name]
    
    # 1. AI Expansion
    if auto_expand and ai:
        try:
            with st.spinner("AI is analyzing regulatory context..."):
                keywords = ai.generate_search_keywords(name, desc)
                if keywords:
                    st.toast(f"AI added terms: {', '.join(keywords)}")
                    search_terms.extend(keywords)
        except Exception:
            pass # Fail silently on AI error and just search base term
    
    # 2. Deduplicate terms
    search_terms = list(set([t for t in search_terms if t and t.strip()]))
    
    all_results = pd.DataFrame()
    combined_log = {"FDA Device": 0, "FDA Drug": 0, "FDA Food": 0, "CPSC": 0}
    
    progress_text = "Scanning databases..."
    my_bar = st.progress(0, text=progress_text)
    
    # 3. Execution Loop
    for i, term in enumerate(search_terms):
        my_bar.progress((i + 1) / len(search_terms), text=f"Scanning sources for '{term}'...")
        
        # Increase limit to 20 per source per term to ensure we capture relevant hits
        hits, log = RegulatoryService.search_all_sources(term, start_date, end_date, limit=20)
        
        all_results = pd.concat([all_results, hits])
        
        # Merge counts
        for k, v in log.items():
            combined_log[k] = combined_log.get(k, 0) + v
        
    my_bar.empty()
    
    # 4. Clean Results
    if not all_results.empty:
        # Fill NA for safe string ops
        all_results.fillna("Unknown", inplace=True)
        # Deduplicate based on ID
        all_results.drop_duplicates(subset=['ID'], inplace=True)
    
    st.session_state.recall_hits = all_results
    st.session_state.recall_log = combined_log

def create_capa_draft(row):
    draft = {
        "issue_description": f"Regulatory Surveillance Hit ({row['Source']}): {row['Product']}. \n\nReason: {row['Reason']}",
        "root_cause": "External Recall Investigation Required",
        "immediate_actions": f"1. Review affected inventory for Recall #{row['ID']}.\n2. Contact manufacturer {row['Firm']}."
    }
    st.session_state.capa_entry_draft = draft
    st.sidebar.success("Draft created! Go to 'CAPA' tab to finalize.")

def add_to_fmea(row):
    # Ensure string slicing is safe
    reason_txt = str(row['Reason'])
    
    new_mode = {
        "Potential Failure Mode": f"Recall Event: {reason_txt[:100]}...",
        "Potential Effect(s)": "Patient Harm / Regulatory Action",
        "Potential Cause(s)": f"Issue identified in {row['Source']} Recall #{row['ID']}",
        "Severity": 8,
        "Occurrence": 5,
        "Detection": 3,
        "RPN": 120
    }
    if 'fmea_rows' not in st.session_state:
        st.session_state.fmea_rows = []
    st.session_state.fmea_rows.append(new_mode)
    if 'fmea_data' in st.session_state:
        st.session_state.fmea_data = pd.DataFrame(st.session_state.fmea_rows)
    st.sidebar.success("Added to FMEA! Go to 'Risk' tab to review.")
