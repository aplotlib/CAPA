# main.py

"""
Main Streamlit application for the Medical Device CAPA Tool.
This version implements a user-provided SKU to link sales and returns data.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO

from src.parsers import parse_file
from src.data_processing import standardize_sales_data, standardize_returns_data
from src.analysis import run_full_analysis
from src.compliance import validate_capa_data
from src.document_generator import CapaDocumentGenerator

# --- Page Configuration and Styling ---
st.set_page_config(page_title="Medical Device CAPA Tool", page_icon="🏥", layout="wide")
st.markdown("""<style>.main-header{...}</style>""", unsafe_allow_html=True) # CSS unchanged

def initialize_session_state():
    """Initializes all required session state variables."""
    defaults = {'analysis_results': None, 'capa_data': {}}
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value
initialize_session_state()

def display_header():
    st.markdown('<div class="main-header"><h1>🏥 Medical Device CAPA Tool</h1><p>Quality Management System for Returns Analysis and CAPA Generation</p></div>', unsafe_allow_html=True)

def process_files(sales_file, returns_file, target_sku, report_period_days):
    """Orchestrates the new parsing and analysis workflow."""
    with st.spinner("Processing files... This may take a moment."):
        # 1. Parse Sales Data
        sales_raw_df = parse_file(sales_file, sales_file.name)
        if sales_raw_df is None or sales_raw_df.empty:
            st.error("Could not read the Odoo Sales Forecast file.")
            return

        # 2. Standardize Sales Data for the target SKU
        sales_df = standardize_sales_data(sales_raw_df, target_sku)
        if sales_df is None or sales_df.empty:
            st.error(f"SKU '{target_sku}' not found in the Sales Forecast file. Please check for typos.")
            return

        # 3. Parse Returns Pivot Table
        returns_raw_df = parse_file(returns_file, returns_file.name)
        if returns_raw_df is None or returns_raw_df.empty:
            st.error("Could not read the Pivot Return Report file.")
            return
            
        # 4. Standardize Returns Data for the target SKU
        returns_df = standardize_returns_data(returns_raw_df, target_sku)
        if returns_df is None or returns_df.empty:
            st.error("Could not calculate total returns from the Pivot Return Report.")
            return

        # 5. Run Analysis
        # Note: The date filtering of returns is no longer possible with the pivot table format.
        # The analysis will compare total sales vs total returns for the given SKU.
        st.session_state.analysis_results = run_full_analysis(sales_df, returns_df, report_period_days)
        st.success(f"✅ Analysis complete for SKU: {target_sku}")

def main():
    display_header()
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # 1. NEW: Text input for the target SKU
        target_sku = st.text_input("Enter SKU for Returns File", help="Type the exact SKU that your Returns Report file is for.")

        # 2. Report period input
        report_period_days = st.number_input("Enter Report Period (Days)", min_value=1, max_value=365, value=30)
        
        st.markdown("---")
        st.header("📁 Data Input")

        st.info("The tool is now configured for your specific Odoo Sales Forecast and Pivot Table Returns files.")
        sales_files = st.file_uploader("1. Upload Odoo Sales Forecast", type=['csv', 'xlsx'], accept_multiple_files=False)
        returns_files = st.file_uploader("2. Upload Pivot Return Report", type=['csv', 'xlsx'], accept_multiple_files=False)
        
        if st.button("Process Files", type="primary"):
            if not target_sku:
                st.warning("Please enter the SKU for the returns file.")
            elif not sales_files or not returns_files:
                st.warning("Please upload both a sales and a returns file.")
            else:
                process_files(sales_files, returns_files, target_sku, report_period_days)

    # Main page tabs (Dashboard, CAPA Form, etc.)
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 CAPA Form", "📄 Document Generation"])
    with tab1:
        if st.session_state.analysis_results:
            # Display metrics...
            st.markdown(f"### Analysis for SKU: **{st.session_state.analysis_results['return_summary'].iloc[0]['sku']}**")
            st.dataframe(st.session_state.analysis_results['return_summary'])
        else:
            st.info("Enter an SKU, upload your files, and click 'Process Files' to see the analysis.")
            
    with tab2:
        # CAPA Form logic
        pass

    with tab3:
        # Document generation logic
        pass

if __name__ == "__main__":
    main()
