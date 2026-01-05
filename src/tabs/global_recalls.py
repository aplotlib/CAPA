# src/tabs/global_recalls.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.ai_services import get_ai_service
from src.services.regulatory_service import RegulatoryService

# --- CACHED SEARCH WRAPPER ---
@st.cache_data(ttl=3600, show_spinner=False)
def search_wrapper(term, start, end):
    return RegulatoryService.search_all_sources(term, start, end, limit=200)

def display_recalls_tab():
    st.header("🌍 Regulatory Intelligence & Recall Tracker")
    st.caption("Deep-scan surveillance of FDA (USA), UK MHRA, Health Canada, and CPSC databases.")

    ai = get_ai_service()
    
    # Initialize State
    if 'recall_hits' not in st.session_state:
        st.session_state.recall_hits = pd.DataFrame()
    if 'recall_log' not in st.session_state:
        st.session_state.recall_log = {}

    # --- INPUT SECTION ---
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Target Configuration")
            
            default_name = ""
            default_desc = ""
            if 'product_info' in st.session_state:
                default_name = st.session_state.product_info.get('name', '')
                default_desc = st.session_state.product_info.get('ifu', '')
            
            p_name = st.text_input("Search Query", value=default_name, placeholder="e.g. Medtronic Infusion Pump")
            p_desc = st.text_area("Context Description", value=default_desc, height=68, help="Used by AI to find synonyms.")
            
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                default_start = datetime.now() - timedelta(days=365*5)
                start_date = st.date_input("Start Date", value=default_start)
            with c_d2:
                end_date = st.date_input("End Date", value=datetime.now())

        with col2:
            st.write("###") 
            st.write("###") 
            auto_expand = st.checkbox("🤖 AI-Expanded Search", value=True, help="Automatically searches synonyms")
            
            if st.button("🚀 Run Deep Scan", type="primary", use_container_width=True):
                if not p_name:
                    st.error("Enter a search query.")
                else:
                    st.session_state.recall_hits = pd.DataFrame()
                    st.session_state.recall_log = {}
                    
                    run_search_logic(p_name, p_desc, start_date, end_date, auto_expand, ai)
                    st.rerun()
            
            # GOOGLE VERIFICATION LINK
            if p_name:
                google_url = f"https://www.google.com/search?q={p_name.replace(' ', '+')}+recall+FDA+MHRA+safety+notice"
                st.link_button("🔍 Verify on Google", google_url, use_container_width=True)

    # --- RESULTS LIST ---
    if not st.session_state.recall_hits.empty:
        df = st.session_state.recall_hits
        st.divider()
        st.subheader(f"Detailed Findings ({len(df)})")
        
        # Display Metrics
        cols = st.columns(6)
        log = st.session_state.recall_log
        keys = ["FDA Device", "FDA Drug", "FDA Food", "CPSC", "UK MHRA", "Health Canada"]
        for i, key in enumerate(keys):
            count = log.get(key, 0)
            cols[i].metric(key, count, delta="Alert" if count > 0 else None, delta_color="inverse")

        # Tabs for View
        tab_list, tab_table = st.tabs(["⚡ Smart View", "📊 Data Table"])
        
        with tab_list:
            for index, row in df.iterrows():
                src = row['Source']
                icon = "💊" if "Drug" in src else "🛠️" if "Device" in src else "🇬🇧" if "UK" in src else "⚠️"
                
                with st.expander(f"{icon} **{row['Date']}** | {src} | {row['Product'][:80]}..."):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**Product:** {row['Product']}")
                        st.markdown(f"**Reason:** {row['Reason']}")
                        st.markdown(f"**Firm:** {row['Firm']}")
                        if row.get('Link'):
                             st.markdown(f"👉 [**View Official Source Record**]({row['Link']})")
                    with c2:
                        st.caption(f"ID: {row['ID']}")
                        st.caption(f"Status: {row['Status']}")

        with tab_table:
            st.dataframe(
                df, 
                column_config={
                    "Link": st.column_config.LinkColumn("Source Link", display_text="Open Record"),
                    "Date": st.column_config.DateColumn("Date"),
                },
                use_container_width=True
            )

        # --- EXPORT SECTION ---
        st.divider()
        st.subheader("📤 Export Regulatory Report")
        c_ex1, c_ex2 = st.columns(2)
        with c_ex1:
            # Generate DOCX
            if st.button("📄 Generate Formal Regulatory Report (.docx)", width="stretch", type="primary"):
                with st.spinner("Generating document..."):
                    doc_buffer = st.session_state.doc_generator.generate_regulatory_report_docx(
                        df, p_name, log
                    )
                    st.download_button(
                        "Download DOCX Report",
                        data=doc_buffer,
                        file_name=f"Regulatory_Report_{p_name}_{datetime.today().date()}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        width="stretch"
                    )

        with c_ex2:
            # CSV Download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Download Raw CSV",
                data=csv,
                file_name=f"recalls_raw_{p_name}.csv",
                mime="text/csv",
                width="stretch"
            )
            
    elif st.session_state.recall_log:
        st.success("Search complete. No recalls found matching criteria.")
        if p_name:
             st.info("Tip: Try a broader search term or verify on Google using the button above.")

def run_search_logic(name, desc, start_date, end_date, auto_expand, ai):
    """Orchestrates the search logic."""
    search_terms = [name]
    
    # 1. AI Expansion
    if auto_expand and ai:
        try:
            with st.spinner("AI is analyzing regulatory context and generating synonyms..."):
                keywords = ai.generate_search_keywords(name, desc)
                if keywords:
                    st.toast(f"AI added terms: {', '.join(keywords)}")
                    search_terms.extend(keywords)
        except Exception: pass 
    
    search_terms = list(set([t for t in search_terms if t and t.strip()]))
    all_results = pd.DataFrame()
    combined_log = {}
    
    progress_bar = st.progress(0, text="Initializing scan...")
    
    for i, term in enumerate(search_terms):
        progress_bar.progress((i + 1) / len(search_terms), text=f"Scanning global databases for '{term}'...")
        
        # Call the cached wrapper
        hits, log = search_wrapper(term, start_date, end_date)
        
        all_results = pd.concat([all_results, hits])
        for k, v in log.items():
            combined_log[k] = combined_log.get(k, 0) + v
        
    progress_bar.empty()
    
    if not all_results.empty:
        all_results.fillna("Unknown", inplace=True)
        # Drop duplicates based on ID to avoid showing same recall for multiple synonyms
        all_results.drop_duplicates(subset=['ID'], inplace=True)
        if 'Date' in all_results.columns:
             all_results = all_results.sort_values(by='Date', ascending=False)
    
    st.session_state.recall_hits = all_results
    st.session_state.recall_log = combined_log
