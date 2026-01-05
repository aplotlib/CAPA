import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.ai_services import get_ai_service
from src.services.regulatory_service import RegulatoryService

def display_recalls_tab():
    st.header("🌍 Ultimate Regulatory Tracker")
    st.caption("Advanced AI-powered surveillance of FDA (USA), UK MHRA, Health Canada, and CPSC databases.")

    ai = get_ai_service()
    
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
                    
                    run_search(p_name, p_desc, start_date, end_date, auto_expand, ai)
                    st.rerun()

    # --- INTERNATIONAL MANUAL SEARCH LINKS ---
    # Since EU and LATAM often lack open JSON APIs, we provide direct deep-links.
    if p_name:
        with st.expander("🔗 Direct Links to Restricted/Manual Databases (EU, LATAM, AUS)", expanded=False):
            st.info("Some regions (EU, Brazil, Mexico) do not provide open API access. Click below to search their official portals directly.")
            l_c1, l_c2, l_c3 = st.columns(3)
            
            # EU EUDAMED
            eudamed_url = f"https://ec.europa.eu/tools/eudamed/#/screen/search-device?keywords={p_name}"
            l_c1.markdown(f"**🇪🇺 EU EUDAMED**\n[Search '{p_name}']({eudamed_url})")
            
            # Brazil ANVISA
            anvisa_url = "https://consultas.anvisa.gov.br/#/tecnovigilancia/alerta-sanitario/"
            l_c2.markdown(f"**🇧🇷 Brazil ANVISA**\n[Go to Portal (Manual Search)]({anvisa_url})")
            
            # Australia TGA (SARA)
            tga_url = f"https://apps.tga.gov.au/Prod/SARA/kui/search?q={p_name}"
            l_c3.markdown(f"**🇦🇺 Australia TGA**\n[Search '{p_name}']({tga_url})")

    # --- SEARCH STATUS BOARD ---
    if st.session_state.recall_log:
        st.write("### 📡 Surveillance Status")
        # Updated columns to include new sources
        cols = st.columns(6)
        log = st.session_state.recall_log
        
        def show_metric(col, label, key):
            count = log.get(key, 0)
            with col:
                if count > 0:
                    st.metric(label, f"{count}", delta="Alert", delta_color="inverse")
                else:
                    st.metric(label, "0", delta="Clear", delta_color="off")

        show_metric(cols[0], "FDA Devices", "FDA Device")
        show_metric(cols[1], "FDA Drugs", "FDA Drug")
        show_metric(cols[2], "FDA Food", "FDA Food")
        show_metric(cols[3], "CPSC", "CPSC")
        show_metric(cols[4], "UK MHRA", "UK MHRA")
        show_metric(cols[5], "Canada", "Health Canada")
        st.divider()

    # --- RESULTS LIST ---
    if not st.session_state.recall_hits.empty:
        df = st.session_state.recall_hits
        st.subheader(f"Detailed Findings ({len(df)})")
        
        tab_list, tab_raw = st.tabs(["⚡ Smart View", "📋 Raw Data & Export"])
        
        with tab_list:
            st.info("Showing most recent alerts first.")
            
            for index, row in df.iterrows():
                # Dynamic Icon based on Source
                src = row['Source']
                if "Drug" in src: icon = "💊"
                elif "Device" in src: icon = "🛠️"
                elif "Food" in src: icon = "🍏"
                elif "UK" in src: icon = "🇬🇧"
                elif "Canada" in src: icon = "🇨🇦"
                else: icon = "🧸"
                
                title_str = str(row['Product'])[:90] if row['Product'] else "No Description"
                
                with st.expander(f"{icon} **{row['Date']}** | {src} | {title_str}..."):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**Product:** {row['Product']}")
                        st.markdown(f"**Reason:** {row['Reason']}")
                        st.markdown(f"**Firm:** {row['Firm']}")
                    with c2:
                        st.markdown(f"**ID:** {row['ID']}")
                        st.caption(f"Status: {row['Status']}")
                        # If URL is in ID (UK/Canada), show link
                        if "http" in str(row['ID']):
                             st.markdown(f"[View Source]({row['ID']})")

        with tab_raw:
            c_ex1, c_ex2 = st.columns([1, 4])
            with c_ex1:
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
            with st.spinner("AI is analyzing regulatory context and generating synonyms..."):
                keywords = ai.generate_search_keywords(name, desc)
                if keywords:
                    st.toast(f"AI added terms: {', '.join(keywords)}")
                    search_terms.extend(keywords)
        except Exception:
            pass 
    
    search_terms = list(set([t for t in search_terms if t and t.strip()]))
    
    all_results = pd.DataFrame()
    # Initialize combined log with ALL potential keys
    combined_log = {
        "FDA Device": 0, "FDA Drug": 0, "FDA Food": 0, "CPSC": 0, 
        "UK MHRA": 0, "Health Canada": 0
    }
    
    progress_text = "Scanning databases..."
    my_bar = st.progress(0, text=progress_text)
    
    for i, term in enumerate(search_terms):
        my_bar.progress((i + 1) / len(search_terms), text=f"Scanning sources for '{term}'...")
        
        # INCREASED LIMIT TO 100
        hits, log = RegulatoryService.search_all_sources(term, start_date, end_date, limit=100)
        
        all_results = pd.concat([all_results, hits])
        
        for k, v in log.items():
            combined_log[k] = combined_log.get(k, 0) + v
        
    my_bar.empty()
    
    if not all_results.empty:
        all_results.fillna("Unknown", inplace=True)
        all_results.drop_duplicates(subset=['ID'], inplace=True)
        if 'Date' in all_results.columns:
             all_results = all_results.sort_values(by='Date', ascending=False)
    
    st.session_state.recall_hits = all_results
    st.session_state.recall_log = combined_log
