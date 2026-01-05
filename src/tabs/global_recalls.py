import streamlit as st
import pandas as pd
from src.ai_services import get_ai_service
from src.services.regulatory_service import RegulatoryService

def display_recalls_tab():
    st.header("🌍 Global Regulatory Intelligence Agent")
    st.caption("AI-powered surveillance of FDA (Devices, Drugs, Food) and CPSC databases.")

    ai = get_ai_service()
    
    # Initialize session state for recalls if needed
    if 'recall_hits' not in st.session_state:
        st.session_state.recall_hits = pd.DataFrame()

    # --- INPUT SECTION ---
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("1. Configure Search Target")
            # Default to active product info
            default_name = ""
            default_desc = ""
            
            if 'product_info' in st.session_state:
                default_name = st.session_state.product_info.get('name', '')
                default_desc = st.session_state.product_info.get('ifu', '')
            
            p_name = st.text_input("Product Name / Type", value=default_name)
            p_desc = st.text_area("Description (for AI Context)", value=default_desc, height=68, 
                                help="The AI uses this to find synonyms and judge relevance.")
            
        with col2:
            st.write("###") # Spacing
            st.write("###") 
            auto_expand = st.checkbox("🤖 AI-Expanded Search", value=True, help="Allow AI to generate synonyms (e.g. 'Heart' -> 'Cardiac')")
            
            if st.button("🚀 Run Scan", type="primary", use_container_width=True):
                if not p_name:
                    st.error("Enter a product name.")
                else:
                    run_search(p_name, p_desc, auto_expand, ai)

    # --- RESULTS SECTION ---
    if not st.session_state.recall_hits.empty:
        df = st.session_state.recall_hits
        st.divider()
        st.subheader(f"Found {len(df)} Regulatory Events")
        
        # Tabs for different views
        tab_list, tab_raw = st.tabs(["⚡ Smart Action View", "📋 Raw Data"])
        
        with tab_list:
            st.info("Review these findings. Use the buttons to immediately create actions in your Quality System.")
            
            # Pagination or Limit to first 20 for performance in list view
            for index, row in df.head(20).iterrows():
                with st.expander(f"**{row['Date']}** | {row['Source']} | {row['Product'][:80]}..."):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**Reason:** {row['Reason']}")
                        st.markdown(f"**Firm:** {row['Firm']}")
                        st.caption(f"ID: {row['ID']}")
                    
                    with c2:
                        # ACTION BUTTONS
                        # We use a unique key for every button
                        if st.button("📝 Draft CAPA", key=f"capa_{row['ID']}_{index}"):
                            create_capa_draft(row)
                        
                        if st.button("⚠️ Add to FMEA", key=f"fmea_{row['ID']}_{index}"):
                            add_to_fmea(row)

        with tab_raw:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "regulatory_scan.csv", "text/csv")

def run_search(name, desc, auto_expand, ai):
    """Orchestrates the search logic."""
    search_terms = [name]
    
    if auto_expand and ai:
        with st.spinner("AI is generating regulatory search terms..."):
            # We call the new AI method we added
            keywords = ai.generate_search_keywords(name, desc)
            if keywords:
                st.toast(f"AI added terms: {', '.join(keywords)}")
                search_terms.extend(keywords)
    
    # Remove duplicates
    search_terms = list(set(search_terms))
    
    all_results = pd.DataFrame()
    progress_text = "Scanning databases..."
    my_bar = st.progress(0, text=progress_text)
    
    for i, term in enumerate(search_terms):
        my_bar.progress((i + 1) / len(search_terms), text=f"Scanning sources for '{term}'...")
        hits = RegulatoryService.search_all_sources(term, limit=5)
        all_results = pd.concat([all_results, hits])
        
    my_bar.empty()
    
    if not all_results.empty:
        # Deduplicate based on ID
        all_results.drop_duplicates(subset=['ID'], inplace=True)
        st.session_state.recall_hits = all_results
        st.success("Scan Complete!")
    else:
        st.warning("No recalls found for these terms.")

def create_capa_draft(row):
    """Pushes data to the CAPA tab."""
    draft = {
        "issue_description": f"Regulatory Surveillance Hit ({row['Source']}): {row['Product']}. \n\nReason: {row['Reason']}",
        "root_cause": "External Recall Investigation Required",
        "immediate_actions": f"1. Review affected inventory for Recall #{row['ID']}.\n2. Contact manufacturer {row['Firm']}."
    }
    # Update the session state used by src/tabs/capa.py
    st.session_state.capa_entry_draft = draft
    st.sidebar.success("Draft created! Go to 'CAPA' tab to finalize.")

def add_to_fmea(row):
    """Pushes data to the Risk/FMEA tab."""
    new_mode = {
        "Potential Failure Mode": f"Recall Event: {row['Reason'][:100]}...",
        "Potential Effect(s)": "Patient Harm / Regulatory Action",
        "Potential Cause(s)": f"Design/Mfg issue identified in {row['Source']} Recall #{row['ID']}",
        "Severity": 8, # Default to high for recalls
        "Occurrence": 5,
        "Detection": 3,
        "RPN": 120
    }
    
    # Update the session state used by src/tabs/risk_safety.py
    if 'fmea_rows' not in st.session_state:
        st.session_state.fmea_rows = []
    
    st.session_state.fmea_rows.append(new_mode)
    
    # Also update the dataframe wrapper if it exists
    if 'fmea_data' in st.session_state:
        st.session_state.fmea_data = pd.DataFrame(st.session_state.fmea_rows)
        
    st.sidebar.success("Added to FMEA! Go to 'Risk' tab to review.")
