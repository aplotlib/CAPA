# main.py

import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO
from src.parsers import parse_file
from src.data_processing import standardize_sales_data, standardize_returns_data
from src.analysis import run_full_analysis
from src.compliance import validate_capa_data
from src.document_generator import CapaDocumentGenerator

st.set_page_config(page_title="Medical Device CAPA Tool", page_icon="🏥", layout="wide")
st.markdown("""<style>.main-header{...}</style>""", unsafe_allow_html=True)  # CSS unchanged

def initialize_session_state():
    defaults = {'analysis_results': None, 'capa_data': {}, 'misc_df': pd.DataFrame()}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

def display_header():
    st.markdown('<div class="main-header"><h1>🏥 Medical Device CAPA Tool</h1><p>Quality Management System for Returns Analysis and CAPA Generation</p></div>', unsafe_allow_html=True)

def process_files(sales_file, returns_file, misc_files, target_sku, report_period_days):
    with st.spinner("Processing files..."):
        st.session_state.analysis_results = None
        st.session_state.misc_df = pd.DataFrame()

        sales_raw_df = parse_file(sales_file, sales_file.name)
        if sales_raw_df is None or sales_raw_df.empty:
            st.error("Could not read the Sales Forecast file.")
            return

        sales_df = standardize_sales_data(sales_raw_df, target_sku)
        if sales_df is None or sales_df.empty:
            st.error(f"SKU '{target_sku}' not found in the Sales file. Please check for typos or formatting issues.")
            return

        returns_raw_df = parse_file(returns_file, returns_file.name)
        if returns_raw_df is None or returns_raw_df.empty:
            st.error("Could not read the Returns Report file.")
            return

        returns_df = standardize_returns_data(returns_raw_df, target_sku)
        if returns_df is None or returns_df.empty:
            st.error("Could not calculate total returns from the Pivot Report.")
            return

        st.session_state.analysis_results = run_full_analysis(sales_df, returns_df, report_period_days)
        st.success(f"✅ Analysis complete for SKU: {target_sku}")

        if misc_files:
            all_misc = [parse_file(file, file.name) for file in misc_files]
            st.session_state.misc_df = pd.concat([df for df in all_misc if df is not None], ignore_index=True)
            if not st.session_state.misc_df.empty:
                st.success("✅ Miscellaneous files processed.")

def display_manual_entry_form(report_period_days):
    st.markdown("#### Manually Enter Data")
    with st.form("manual_data_form"):
        target_sku = st.text_input("Enter SKU for Analysis*")
        sales_units = st.number_input("Enter Total Sales Units for SKU", min_value=0)
        return_units = st.number_input("Enter Total Return Units for SKU", min_value=0)
        submitted = st.form_submit_button("Process Manual Data")

        if submitted:
            if not target_sku or sales_units <= 0:
                st.warning("Please provide an SKU and sales quantity.")
            else:
                sales_df = pd.DataFrame([{'sku': target_sku, 'quantity': sales_units}])
                returns_df = pd.DataFrame([{'sku': target_sku, 'quantity': return_units}])
                st.session_state.analysis_results = run_full_analysis(sales_df, returns_df, report_period_days)
                st.success(f"✅ Manual analysis complete for SKU: {target_sku}")

def display_metrics_dashboard(results):
    if not results or 'return_summary' not in results or results['return_summary'].empty:
        return
    summary = results['return_summary'].iloc[0]
    st.markdown(f"### Analysis for SKU: **{summary['sku']}**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Return Rate", f"{summary['return_rate']:.2f}%")
    col2.metric("Total Units Sold", f"{int(summary['total_sold']):,}")
    col3.metric("Total Units Returned", f"{int(summary['total_returned']):,}")

def main():
    display_header()
    with st.sidebar:
        st.header("⚙️ Controls")
        input_method = st.radio("Choose Input Method", ('File Upload', 'Manual Entry'))
        report_period_days = st.number_input("Report Period (Days)", min_value=1, value=30, help="Used for context and manual entry filtering.")

        st.markdown("---")
        st.header("📁 Data Input")

        if input_method == 'File Upload':
            target_sku = st.text_input("Enter SKU for Returns File*", help="Type the exact SKU your Returns Report is for.")
            sales_file = st.file_uploader("1. Upload Odoo Sales Forecast", type=['csv', 'xlsx'])
            returns_file = st.file_uploader("2. Upload Pivot Return Report", type=['csv', 'xlsx'])
            misc_files = st.file_uploader("3. Upload Miscellaneous Data (Images, etc.)", accept_multiple_files=True)
            
            if st.button("Process Files", type="primary"):
                if not target_sku:
                    st.warning("Please enter the SKU for the returns file.")
                elif not sales_file or not returns_file:
                    st.warning("Please upload both a sales and a returns file.")
                else:
                    process_files(sales_file, returns_file, misc_files, target_sku, report_period_days)
        
        elif input_method == 'Manual Entry':
            display_manual_entry_form(report_period_days)

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 CAPA Form", "📄 Document Generation"])
    with tab1:
        if st.session_state.analysis_results:
            display_metrics_dashboard(st.session_state.analysis_results)
        else:
            st.info("Enter data and click 'Process' to see the analysis.")

        if not st.session_state.misc_df.empty:
            st.markdown("---")
            st.markdown("### Miscellaneous Uploaded Data")
            st.dataframe(st.session_state.misc_df)

    # Placeholder for other tabs
    with tab2:
        st.info("CAPA Form will be displayed here.")
    with tab3:
        st.info("Document Generation will be available here.")

if __name__ == "__main__":
    main()
