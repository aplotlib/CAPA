import streamlit as st
import pandas as pd
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
            default_name = ""
            default_desc = ""
            if 'product_info' in st.session_state:
                default_name = st.session_state.product_info.get('name', '')
                default_desc = st.session_state.product_info.get('ifu', '')
            
            p_name = st.text_input("Product Name / Type", value=default_name, placeholder="e.g. Infusion Pump")
            p_desc = st.text_area("Description (for AI Context)", value=default_desc, height=68, help="AI uses this to find synonyms.")
            
        with col2:
            st.write("###") 
            st.write("###") 
            auto_expand = st.checkbox("🤖 AI-Expanded Search", value=True, help="Automatically searches synonyms (e.g. 'Cardiac' for 'Heart')")
            
            if st.button("🚀 Run Scan", type="primary", use_container_width=True):
                if not p_name:
                    st.error("Enter a product name.")
                else:
                    run_search(p_name, p_desc, auto_expand, ai)

    # --- SEARCH STATUS BOARD ---
    # This shows the user exactly what happened per agency
    if st.session_state.recall_log:
        st.write("### 📡 Database Status")
        cols = st.columns(4)
        log = st.session_state.recall_log
        
        # Helper to display metrics
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
        
        tab_list, tab_raw = st.tabs(["⚡ Smart Action View", "📋 Raw Data"])
        
        with tab_list:
            st.info("Review findings. Use buttons to draft CAPAs or update Risk Files.")
            
            for index, row in df.head(25).iterrows():
                # Color code header based on source
                icon = "💊" if "Drug" in row['Source'] else "🛠️" if "Device" in row['Source'] else "🧸"
                
                with st.expander(f"{icon} **{row['Date']}** | {row['Source']} | {row['Product'][:70]}..."):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**Reason:** {row['Reason']}")
                        st.markdown(f"**Firm:** {row['Firm']}")
                        st.caption(f"ID: {row['ID']}")
                    
                    with c2:
                        if st.button("📝 Draft CAPA", key=f"capa_{index}"):
                            create_capa_draft(row)
                        if st.button("⚠️ Add to FMEA", key=f"fmea_{index}"):
                            add_to_fmea(row)

        with tab_raw:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "regulatory_scan.csv", "text/csv")
    
    elif st.session_state.recall_log:
        st.success("No recalls found across any connected database.")

def run_search(name, desc, auto_expand, ai):
    """Orchestrates the search logic."""
    search_terms = [name]
    
    if auto_expand and ai:
        with st.spinner("AI is generating regulatory search terms..."):
            keywords = ai.generate_search_keywords(name, desc)
            if keywords:
                st.toast(f"AI added terms: {', '.join(keywords)}")
                search_terms.extend(keywords)
    
    # Clean duplicates
    search_terms = list(set(search_terms))
    
    all_results = pd.DataFrame()
    combined_log = {"FDA Device": 0, "FDA Drug": 0, "FDA Food": 0, "CPSC": 0}
    
    progress_text = "Scanning databases..."
    my_bar = st.progress(0, text=progress_text)
    
    for i, term in enumerate(search_terms):
        my_bar.progress((i + 1) / len(search_terms), text=f"Scanning sources for '{term}'...")
        
        # Returns (DataFrame, Dict)
        hits, log = RegulatoryService.search_all_sources(term, limit=5)
        
        all_results = pd.concat([all_results, hits])
        
        # Merge counts
        for k, v in log.items():
            combined_log[k] = combined_log.get(k, 0) + v
        
    my_bar.empty()
    
    # Save to session state
    if not all_results.empty:
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
    new_mode = {
        "Potential Failure Mode": f"Recall Event: {row['Reason'][:100]}...",
        "Potential Effect(s)": "Patient Harm / Regulatory Action",
        "Potential Cause(s)": f"Design/Mfg issue identified in {row['Source']} Recall #{row['ID']}",
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
