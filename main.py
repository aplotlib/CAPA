# main.py

"""
Main Streamlit application for the Medical Device CAPA Tool.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO

from src.parsers import parse_file
from src.data_processing import standardize_sales_data, standardize_returns_data, combine_dataframes
from src.analysis import run_full_analysis
from src.compliance import validate_capa_data
from src.document_generator import CapaDocumentGenerator

st.set_page_config(page_title="Medical Device CAPA Tool", page_icon="🏥", layout="wide")
st.markdown("""<style>.main-header{background-color:#00466B;color:white;padding:20px;border-radius:10px;text-align:center;margin-bottom:30px;}.stMetric{background-color:#F0F2F6;border-radius:10px;padding:10px;border:1px solid #E0E0E0;}</style>""", unsafe_allow_html=True)

def initialize_session_state():
    defaults = {'sales_df': pd.DataFrame(), 'returns_df': pd.DataFrame(), 'misc_df': pd.DataFrame(), 'analysis_results': None, 'capa_data': {}}
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value
initialize_session_state()

def display_header():
    st.markdown('<div class="main-header"><h1>🏥 Medical Device CAPA Tool</h1><p>Quality Management System for Returns Analysis and CAPA Generation</p></div>', unsafe_allow_html=True)

def process_uploaded_files(sales_files, returns_files, misc_files, report_period_days):
    with st.spinner("Processing files..."):
        all_sales, all_returns, all_misc = [], [], []
        for file in sales_files:
            raw_df = parse_file(file, file.name)
            if raw_df is not None:
                std_df = standardize_sales_data(raw_df)
                if std_df is not None: all_sales.append(std_df)
        st.session_state.sales_df = combine_dataframes(all_sales)

        for file in returns_files:
            raw_df = parse_file(file, file.name)
            if raw_df is not None:
                std_df = standardize_returns_data(raw_df)
                if std_df is not None: all_returns.append(std_df)
        st.session_state.returns_df = combine_dataframes(all_returns)
        
        for file in misc_files:
            parsed_df = parse_file(file, file.name)
            if parsed_df is not None: all_misc.append(parsed_df)
        st.session_state.misc_df = combine_dataframes(all_misc)

        sales_ok = not st.session_state.sales_df.empty
        returns_ok = not st.session_state.returns_df.empty

        if sales_ok and returns_ok:
            st.session_state.analysis_results = run_full_analysis(st.session_state.sales_df, st.session_state.returns_df, report_period_days)
            st.success("✅ Sales and Returns data processed successfully!")
        else:
            if sales_files and not sales_ok:
                st.error("⚠️ Sales file processing failed. Please ensure it is the correct Odoo format with headers on the second row and contains 'SKU' and 'Sales' columns.")
            if returns_files and not returns_ok:
                st.error("⚠️ Returns file processing failed. Please ensure you upload a standard (non-pivot) returns report containing a column for 'SKU' or 'FNSKU'.")
        
        if not st.session_state.misc_df.empty:
            st.success("✅ Miscellaneous files processed.")

def main():
    display_header()
    with st.sidebar:
        st.header("⚙️ Controls")
        report_period_days = st.number_input("Enter Report Period (Days)", min_value=1, max_value=365, value=30, help="Enter the number of days back to analyze for returns.")
        
        st.markdown("---")
        st.header("📁 Data Input")
        input_method = st.radio("Choose Input Method", ('File Upload', 'Manual Entry'))

        if input_method == 'File Upload':
            st.info("The tool is now configured for your specific Odoo Sales Forecast file format.")
            sales_files = st.file_uploader("Upload Odoo Sales Forecast", type=['csv', 'xlsx'], accept_multiple_files=True)
            st.warning("Please upload a standard (non-pivot) returns report with SKU-level data.")
            returns_files = st.file_uploader("Upload Returns Report", type=['csv', 'xlsx'], accept_multiple_files=True)
            misc_files = st.file_uploader("Upload Miscellaneous Data", type=['png', 'jpg', 'pdf', 'docx', 'csv', 'xlsx'], accept_multiple_files=True)
            
            if st.button("Process Files", type="primary"):
                process_uploaded_files(sales_files, returns_files, misc_files, report_period_days)
        
        # Manual Entry logic can be added here if needed

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 CAPA Form", "📄 Document Generation"])
    with tab1:
        if st.session_state.analysis_results and "error" not in st.session_state.analysis_results:
            # Dashboard display logic
            st.markdown("### Analysis Results")
            st.dataframe(st.session_state.analysis_results.get('return_summary', pd.DataFrame()))
        else:
            st.info("Upload and process your files to see the analysis dashboard.")
        if not st.session_state.misc_df.empty:
            st.markdown("---")
            st.markdown("### Miscellaneous Uploaded Data")
            st.dataframe(st.session_state.misc_df)

    with tab2:
        # CAPA Form display logic
        st.info("Complete CAPA Form")
    with tab3:
        # Document Generation logic
        st.info("Generate Document")

if __name__ == "__main__":
    main()
