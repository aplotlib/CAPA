# main.py

"""
Main Streamlit application for the Medical Device CAPA Tool.
This script handles the user interface and orchestrates the backend logic
from the modules located in the 'src' directory.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Import functions from the backend modules
from src.parsers import parse_file
from src.data_processing import standardize_sales_data, standardize_returns_data, combine_dataframes
from src.analysis import run_full_analysis
from src.compliance import validate_capa_data
from src.document_generator import CapaDocumentGenerator

# --- Page Configuration and Styling ---
st.set_page_config(page_title="Medical Device CAPA Tool", page_icon="🏥", layout="wide")
st.markdown("""
<style>
    .main-header { background-color: #00466B; color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 30px; }
    .stMetric { background-color: #F0F2F6; border-radius: 10px; padding: 10px; border: 1px solid #E0E0E0; }
    .stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
def initialize_session_state():
    """Initializes session state variables if they don't exist."""
    state_defaults = {
        'sales_df': pd.DataFrame(), 'returns_df': pd.DataFrame(),
        'analysis_results': None, 'capa_data': {}
    }
    for key, value in state_defaults.items():
        if key not in st.session_state: st.session_state[key] = value
initialize_session_state()

# --- UI: Application Header ---
def display_header():
    st.markdown('<div class="main-header"><h1>🏥 Medical Device CAPA Tool</h1><p>Quality Management System for Returns Analysis and CAPA Generation</p></div>', unsafe_allow_html=True)

# --- Backend Orchestration ---
def process_uploaded_files(sales_files, returns_files, report_period_days):
    """Orchestrates the parsing, cleaning, and analysis of uploaded files."""
    with st.spinner("Processing and analyzing files..."):
        all_sales = []
        for file in sales_files:
            raw_df = parse_file(file, file.name)
            if raw_df is not None:
                std_df = standardize_sales_data(raw_df, report_period_days)
                if std_df is not None: all_sales.append(std_df)
        st.session_state.sales_df = combine_dataframes(all_sales)

        all_returns = []
        for file in returns_files:
            raw_df = parse_file(file, file.name)
            if raw_df is not None:
                std_df = standardize_returns_data(raw_df)
                if std_df is not None: all_returns.append(std_df)
        st.session_state.returns_df = combine_dataframes(all_returns)

        if not st.session_state.sales_df.empty and not st.session_state.returns_df.empty:
            st.session_state.analysis_results = run_full_analysis(
                st.session_state.sales_df, st.session_state.returns_df, report_period_days
            )
            if "error" in st.session_state.analysis_results:
                st.error(f"Analysis Error: {st.session_state.analysis_results['error']}")
            else:
                st.success("✅ Files processed and analyzed successfully!")
        else:
            st.warning("⚠️ Sales or Returns file could not be processed. Please check the file format.")

# --- UI Components ---
def display_metrics_dashboard(results):
    if not results or 'overall_return_rate' not in results: return
    st.markdown(f"#### Analysis Period: {results['analysis_period_start_date']} to {results['analysis_period_end_date']}")
    st.markdown("## Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Overall Return Rate", f"{results['overall_return_rate']:.2f}%")
    with col2: st.metric("Total Units Sold", f"{int(results['total_sales']):,}")
    with col3: st.metric("Total Units Returned", f"{int(results['total_returns']):,}")
    with col4: st.metric("Products with Quality Issues", results['quality_issues_count'])

def display_capa_form():
    """Displays the CAPA form and handles validation with new relaxed rules."""
    st.markdown("## CAPA Information - ISO 13485 Compliant")
    prefill_sku = ""
    if st.session_state.analysis_results and not st.session_state.analysis_results.get('return_summary', pd.DataFrame()).empty:
        prefill_sku = st.session_state.analysis_results['return_summary'].iloc[0]['sku']
        
    with st.form("capa_form"):
        c1, c2 = st.columns(2)
        with c1:
            capa_number = st.text_input("CAPA Number*", value=f"CAPA-{datetime.now().strftime('%Y%m%d')}-001")
            product_name = st.text_input("Product Name*", value=prefill_sku)
            sku = st.text_input("Primary SKU*", value=prefill_sku)
        with c2:
            prepared_by = st.text_input("Prepared By*")
            date = st.date_input("Date*", value=datetime.now())
            severity = st.selectbox("Severity Assessment", ["Critical", "Major", "Minor"])
        
        issue_description = st.text_area("Issue Description", height=100, placeholder="Provide a detailed problem statement...")
        root_cause = st.text_area("Root Cause Analysis", height=100, placeholder="Describe the investigation methodology...")
        corrective_action = st.text_area("Corrective Actions", height=100, placeholder="Describe actions to correct the issue...")
        preventive_action = st.text_area("Preventive Actions", height=100, placeholder="Describe actions to prevent recurrence...")
        
        submitted = st.form_submit_button("💾 Save CAPA Data", type="primary")

        if submitted:
            capa_data = {
                'capa_number': capa_number, 'product': product_name, 'sku': sku,
                'prepared_by': prepared_by, 'date': date.strftime('%Y-%m-%d'),
                'severity': severity, 'issue_description': issue_description,
                'root_cause': root_cause, 'corrective_action': corrective_action,
                'preventive_action': preventive_action
            }
            # Get validation results: is_valid (bool), errors (list), warnings (list)
            is_valid, errors, warnings = validate_capa_data(capa_data)
            
            if is_valid:
                # If there are no blocking errors, save the data
                st.session_state.capa_data = capa_data
                st.success("✅ CAPA data saved successfully!")
                
                # Display any non-blocking warnings as suggestions
                for warning in warnings:
                    st.warning(warning)
            else:
                # If there are blocking errors, display them and don't save
                for error in errors:
                    st.error(f"Failed to save: {error}")

def display_document_generation():
    st.markdown("## Generate CAPA Document")
    if not st.session_state.capa_data or not st.session_state.analysis_results:
        st.warning("⚠️ Please process data and complete the CAPA form before generating a document.")
        return
    if st.button("🚀 Generate CAPA Document", type="primary"):
        with st.spinner("Generating document with AI..."):
            try:
                generator = CapaDocumentGenerator(anthropic_api_key=st.secrets.get("ANTHROPIC_API_KEY"))
                ai_content = generator.generate_ai_structured_content(st.session_state.capa_data, st.session_state.analysis_results)
                if ai_content:
                    doc_buffer = generator.export_to_docx(st.session_state.capa_data, ai_content)
                    st.download_button(label="📥 Download CAPA Document", data=doc_buffer, file_name=f"CAPA_{st.session_state.capa_data['capa_number']}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                else: st.error("Failed to generate content from AI.")
            except Exception as e: st.error(f"An error occurred: {e}")

# --- Main Application Flow ---
def main():
    display_header()
    with st.sidebar:
        st.header("⚙️ Controls")
        report_period_options = {"Last 30 Days": 30, "Last 60 Days": 60, "Last 90 Days": 90, "Last 120 Days": 120, "Last 180 Days": 180, "Last 365 Days": 365}
        selected_period_label = st.selectbox("Select Sales Report Period", options=list(report_period_options.keys()))
        report_period_days = report_period_options[selected_period_label]
        
        st.markdown("---")
        st.header("📁 Data Input")
        sales_files = st.file_uploader("Upload Sales Forecast (Odoo)", type=['csv', 'xlsx'], accept_multiple_files=True)
        returns_files = st.file_uploader("Upload Returns Report", type=['csv', 'xlsx'], accept_multiple_files=True)
        
        if st.button("Process Files", type="primary"):
            if not sales_files or not returns_files:
                st.warning("Please upload both a sales and returns file.")
            else:
                process_uploaded_files(sales_files, returns_files, report_period_days)

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 CAPA Form", "📄 Document Generation"])
    with tab1:
        if st.session_state.analysis_results and "error" not in st.session_state.analysis_results:
            display_metrics_dashboard(st.session_state.analysis_results)
            st.markdown("### Return Rate by Product")
            st.dataframe(st.session_state.analysis_results['return_summary'])
            st.markdown("### Quality Hotspots (High Volume of Quality-Related Returns)")
            st.dataframe(st.session_state.analysis_results['quality_hotspots'])
            st.markdown("### Return Reason Categories")
            st.bar_chart(st.session_state.analysis_results['categorized_returns_df']['category'].value_counts())
        else:
            st.info("Upload and process your files to see the analysis dashboard.")
    with tab2: display_capa_form()
    with tab3: display_document_generation()

if __name__ == "__main__":
    main()
