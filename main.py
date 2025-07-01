# main.py

"""
Main Streamlit application for the Medical Device CAPA Tool.
This script handles the user interface and orchestrates the backend logic
from the modules located in the 'src' directory.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Import functions from the new backend modules
from src.parsers import parse_file
from src.data_processing import standardize_sales_data, standardize_returns_data, combine_dataframes
from src.analysis import run_full_analysis
from src.compliance import validate_capa_data
from src.document_generator import CapaDocumentGenerator

# --- Page Configuration and Styling ---
st.set_page_config(
    page_title="Medical Device CAPA Tool",
    page_icon="🏥",
    layout="wide"
)

# Professional medical device styling (remains unchanged)
st.markdown("""
<style>
    /* CSS Styles go here - unchanged from your original file */
    /* ... */
</style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
def initialize_session_state():
    """Initializes session state variables if they don't exist."""
    state_defaults = {
        'sales_df': pd.DataFrame(),
        'returns_df': pd.DataFrame(),
        'analysis_results': None,
        'capa_data': {}
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()


# --- UI: Application Header ---
def display_header():
    """Displays the main application header."""
    st.markdown("""
    <div class="main-header">
        <h1>🏥 Medical Device CAPA Tool</h1>
        <p>Quality Management System for Returns Analysis and CAPA Generation</p>
    </div>
    """, unsafe_allow_html=True)


# --- Backend Orchestration ---
def process_uploaded_files(sales_files, returns_files):
    """
    Orchestrates the parsing, cleaning, and analysis of uploaded files.
    """
    with st.spinner("Processing and analyzing files... This may take a moment."):
        # Process Sales Files
        all_sales = []
        for file in sales_files:
            raw_df = parse_file(file, file.name)
            if raw_df is not None:
                std_df = standardize_sales_data(raw_df)
                if std_df is not None:
                    all_sales.append(std_df)
        st.session_state.sales_df = combine_dataframes(all_sales)

        # Process Returns Files
        all_returns = []
        for file in returns_files:
            raw_df = parse_file(file, file.name)
            if raw_df is not None:
                std_df = standardize_returns_data(raw_df)
                if std_df is not None:
                    all_returns.append(std_df)
        st.session_state.returns_df = combine_dataframes(all_returns)

        # Run Analysis
        if not st.session_state.sales_df.empty and not st.session_state.returns_df.empty:
            st.session_state.analysis_results = run_full_analysis(
                st.session_state.sales_df,
                st.session_state.returns_df
            )
            st.success("✅ Files processed and analyzed successfully!")
        else:
            st.warning("⚠️ Could not process all files or data is missing. Please check files and try again.")


# --- UI Components ---
def display_metrics_dashboard(results):
    """Displays the main metrics dashboard."""
    if not results or 'overall_return_rate' not in results:
        return

    st.markdown("## Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Overall Return Rate", f"{results['overall_return_rate']:.2f}%")
    with col2:
        st.metric("Total Units Sold", f"{int(results['total_sales']):,}")
    with col3:
        st.metric("Total Units Returned", f"{int(results['total_returns']):,}")
    with col4:
        st.metric("Products with Quality Issues", results['quality_issues_count'])


def display_capa_form():
    """Displays the form for entering CAPA details."""
    st.markdown("## CAPA Information - ISO 13485 Compliant")

    with st.form("capa_form"):
        # CAPA Form fields remain the same as your original file
        # ...
        capa_number = st.text_input("CAPA Number*", value=f"CAPA-{datetime.now().strftime('%Y%m%d')}-001")
        # ... more fields ...
        preventive_action = st.text_area("Preventive Actions*", height=150)
        
        submitted = st.form_submit_button("💾 Save CAPA Data", type="primary")

        if submitted:
            capa_data = {
                'capa_number': capa_number,
                # ... gather all other form fields ...
                'preventive_action': preventive_action
            }
            # Validate and save
            is_valid, issues = validate_capa_data(capa_data)
            if is_valid:
                st.session_state.capa_data = capa_data
                st.success("✅ CAPA data saved and validated!")
            else:
                for issue in issues:
                    st.error(f"Compliance Issue: {issue}")


def display_document_generation():
    """Handles the UI for generating the final CAPA document."""
    st.markdown("## Generate CAPA Document")

    if not st.session_state.capa_data or not st.session_state.analysis_results:
        st.warning("⚠️ Please upload data and complete the CAPA form before generating a document.")
        return

    if st.button("🚀 Generate CAPA Document", type="primary"):
        with st.spinner("Generating document with AI..."):
            try:
                # Initialize the generator with API key from secrets
                generator = CapaDocumentGenerator(
                    anthropic_api_key=st.secrets.get("ANTHROPIC_API_KEY")
                )
                # Generate structured content using AI
                ai_content = generator.generate_ai_structured_content(
                    st.session_state.capa_data,
                    st.session_state.analysis_results
                )
                
                if ai_content:
                    # Export the content to a DOCX file
                    doc_buffer = generator.export_to_docx(st.session_state.capa_data, ai_content)
                    st.download_button(
                        label="📥 Download CAPA Document",
                        data=doc_buffer,
                        file_name=f"CAPA_{st.session_state.capa_data['capa_number']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                else:
                    st.error("Failed to generate content from AI. Please check API keys and try again.")
            except Exception as e:
                st.error(f"An error occurred during document generation: {e}")

# --- Main Application Flow ---
def main():
    """Main function to run the Streamlit application."""
    display_header()

    with st.sidebar:
        st.header("📁 Data Input")
        sales_files = st.file_uploader(
            "Upload Sales Data",
            type=['csv', 'xlsx', 'xls', 'txt'],
            accept_multiple_files=True
        )
        returns_files = st.file_uploader(
            "Upload Returns Data",
            type=['csv', 'xlsx', 'xls', 'txt', 'pdf', 'docx'],
            accept_multiple_files=True
        )
        if st.button("Process Files", type="primary"):
            if not sales_files or not returns_files:
                st.warning("Please upload both sales and returns data.")
            else:
                process_uploaded_files(sales_files, returns_files)

    # Main page tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 CAPA Form", "📄 Document Generation"])

    with tab1:
        if st.session_state.analysis_results:
            display_metrics_dashboard(st.session_state.analysis_results)
            # You can add more charts and tables here using the data in st.session_state.analysis_results
            st.markdown("### Return Rate by Product")
            st.dataframe(st.session_state.analysis_results['return_summary'])
        else:
            st.info("Upload and process files to see the dashboard.")

    with tab2:
        display_capa_form()

    with tab3:
        display_document_generation()

if __name__ == "__main__":
    main()
