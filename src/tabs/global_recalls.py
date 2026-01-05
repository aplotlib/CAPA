import streamlit as st
import pandas as pd
from src.ai_services import get_ai_service
from src.services.openfda_service import OpenFDAService

def display_recalls_tab():
    st.header("🌍 Global Regulatory Intelligence & Recalls")
    st.caption("Screen your device against **REAL-TIME** FDA Enforcement Reports (openFDA API).")

    ai = get_ai_service()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🛡️ Product Screening (FDA Database)")
        
        # Use SKU/Name from global sidebar if available
        default_desc = ""
        if 'product_info' in st.session_state:
            p_name = st.session_state.product_info.get('name', '')
            if p_name:
                default_desc = p_name
            
        device_query = st.text_input(
            "Search Term (Product Name or Keyword)", 
            value=default_desc,
            placeholder="e.g., Infusion Pump, Catheter, Knee Implant...",
            help="This searches the official FDA Device Recall database."
        )
        
        if st.button("Run Live FDA Screen", type="primary", icon="🔍"):
            if not device_query.strip():
                st.error("Please enter a search term.")
            else:
                with st.spinner(f"Querying FDA Database for '{device_query}'..."):
                    # FETCH REAL DATA
                    real_data = OpenFDAService.search_recalls(device_query, limit=15)
                    st.session_state.recall_results_df = real_data
                    
                    # Generate AI Summary of the REAL data if available
                    if not real_data.empty and ai:
                        with st.spinner("AI is analyzing the findings..."):
                            data_summary_str = real_data[['Reason', 'Class', 'Firm']].to_string()
                            prompt = f"Analyze these real FDA recall events for '{device_query}':\n{data_summary_str}\n\nSummarize the common failure modes and risks."
                            st.session_state.recall_analysis = ai.analyze_text(prompt)
                    else:
                        st.session_state.recall_analysis = "No analysis available (No records found)."

        # Display Results
        if 'recall_results_df' in st.session_state:
            df = st.session_state.recall_results_df
            
            if not df.empty:
                st.success(f"Found {len(df)} records from the FDA.")
                
                # 1. AI Analysis of Real Data
                if st.session_state.get('recall_analysis'):
                    with st.expander("🤖 AI Analysis of Trends", expanded=True):
                        st.markdown(st.session_state.recall_analysis)

                # 2. Real Data Table
                st.markdown("### 📋 Official Enforcement Reports")
                st.dataframe(
                    df,
                    column_config={
                        "Date": st.column_config.DateColumn("Initiated"),
                        "Product": st.column_config.TextColumn("Product Description", width="large"),
                        "Reason": st.column_config.TextColumn("Reason for Recall", width="large"),
                        "Recall #": st.column_config.TextColumn("ID", width="small"),
                    },
                    hide_index=True,
                    width=1000  # Deprecated in some versions but good for older streamlit, use use_container_width in newer
                )
                
                # CSV Download
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download Recall Data (CSV)",
                    csv,
                    "fda_recalls.csv",
                    "text/csv"
                )
            else:
                st.warning("No official FDA recalls found for this search term.")

    with col2:
        st.subheader("🔗 External Databases")
        st.info("The tool above searches FDA (USA). For other regions, please consult official sources directly:")
        
        sources = [
            {
                "region": "🇪🇺 EU (EUDAMED)", 
                "name": "Vigilance & Surveillance", 
                "url": "https://ec.europa.eu/tools/eudamed"
            },
            {
                "region": "🇬🇧 UK (MHRA)", 
                "name": "Drug and Device Alerts", 
                "url": "https://www.gov.uk/drug-device-alerts"
            },
            {
                "region": "🇦🇺 Australia (TGA)", 
                "name": "SARA Database", 
                "url": "https://apps.tga.gov.au/PROD/DRAC/arn-entry.aspx"
            },
            {
                "region": "🇨🇦 Canada", 
                "name": "Recalls and Safety Alerts", 
                "url": "https://recalls-rappels.canada.ca/en"
            }
        ]
        
        for source in sources:
            with st.expander(f"{source['region']}"):
                st.markdown(f"**[Open Database]({source['url']})**")
