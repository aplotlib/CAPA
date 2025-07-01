# main.py

"""
Main Streamlit application for the Medical Device CAPA Tool.
This script handles the user interface and orchestrates the backend logic
from the modules located in the 'src' directory.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO

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

st.markdown("""
<style>
    .main-header {
        background-color: #00466B;
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 30px;
    }
    .stMetric {
        background-color: #F0F2F6;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #E0E0E0;
    }
    .stButton>button {
        width: 100%;
    }
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
def display_manual_entry_form():
    """Displays a form for manual data entry."""
    st.markdown("#### Manually Enter Sales and Returns Data")
    
    with st.form("manual_data_form"):
        st.subheader("Sales Data")
        sales_manual_data = st.text_area(
            "Enter sales data (CSV format). Required columns: sku, quantity.",
            "sku,quantity\nSKU001,50\nSKU002,30",
            height=150
        )

        st.subheader("Returns Data")
        returns_manual_data = st.text_area(
            "Enter returns data (CSV format). Required columns: return_date, sku, quantity, reason.",
            "return_date,sku,quantity,reason\n2023-10-03,SKU001,2,Defective\n2023-10-04,SKU002,1,Wrong size",
            height=150
        )
        
        submitted = st.form_submit_button("Process Manual Data")

        if submitted:
            with st.spinner("Processing manual data..."):
                try:
                    # Process manual sales data
                    sales_df = pd.read_csv(StringIO(sales_manual_data))
                    st.session_state.sales_df = standardize_sales_data(sales_df)
                    
                    # Process manual returns data
                    returns_df = pd.read_csv(StringIO(returns_manual_data))
                    st.session_state.returns_df = standardize_returns_data(returns_df)

                    # Run Analysis
                    if st.session_state.sales_df is not None and not st.session_state.sales_df.empty and \
                       st.session_state.returns_df is not None and not st.session_state.returns_df.empty:
                        st.session_state.analysis_results = run_full_analysis(
                            st.session_state.sales_df,
                            st.session_state.returns_df
                        )
                        st.success("✅ Manual data processed and analyzed successfully!")
                    else:
                        st.error("⚠️ Could not process the manual data. Please ensure the data has the correct column headers (e.g., 'sku', 'quantity', 'return_date', 'reason').")
                except Exception as e:
                    st.error(f"An error occurred while processing manual data: {e}")


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

    # Pre-fill form with data from analysis if available
    prefill_sku = ""
    prefill_product = ""
    if st.session_state.analysis_results and not st.session_state.analysis_results['return_summary'].empty:
        top_returned_sku = st.session_state.analysis_results['return_summary'].iloc[0]['sku']
        prefill_sku = top_returned_sku
        prefill_product = top_returned_sku # Assuming SKU is the product identifier

    with st.form("capa_form"):
        capa_number = st.text_input("CAPA Number*", value=f"CAPA-{datetime.now().strftime('%Y%m%d')}-001")
        product_name = st.text_input("Product Name*", value=prefill_product)
        sku = st.text_input("Primary SKU*", value=prefill_sku)
        prepared_by = st.text_input("Prepared By*")
        date = st.date_input("Date*", value=datetime.now())
        
        severity = st.selectbox("Severity Assessment*", ["Critical", "Major", "Minor"])
        
        issue_description = st.text_area("Issue Description*", height=150, placeholder="Provide a detailed problem statement including scope and impact.")
        root_cause = st.text_area("Root Cause Analysis*", height=150, placeholder="Describe the investigation methodology (e.g., 5 Whys, Fishbone) and findings.")
        corrective_action = st.text_area("Corrective Actions*", height=150, placeholder="Describe the actions to correct the issue, including an implementation timeline.")
        preventive_action = st.text_area("Preventive Actions*", height=150, placeholder="Describe actions to prevent recurrence and include a plan for monitoring effectiveness.")
        
        submitted = st.form_submit_button("💾 Save CAPA Data", type="primary")

        if submitted:
            capa_data = {
                'capa_number': capa_number,
                'product': product_name,
                'sku': sku,
                'prepared_by': prepared_by,
                'date': date.strftime('%Y-%m-%d'),
                'severity': severity,
                'issue_description': issue_description,
                'root_cause': root_cause,
                'corrective_action': corrective_action,
                'preventive_action': preventive_action
            }
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
        st.warning("⚠️ Please process data and complete the CAPA form before generating a document.")
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
        input_method = st.radio(
            "Choose your data input method:",
            ('File Upload', 'Manual Entry'),
            help="Choose 'File Upload' to analyze Excel, CSV, or other documents. Choose 'Manual Entry' to paste in your own data."
        )

        st.markdown("---")

        if input_method == 'File Upload':
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
        
        elif input_method == 'Manual Entry':
            display_manual_entry_form()

    # Main page tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 CAPA Form", "📄 Document Generation"])

    with tab1:
        if st.session_state.analysis_results:
            display_metrics_dashboard(st.session_state.analysis_results)
            st.markdown("### Return Rate by Product")
            st.dataframe(st.session_state.analysis_results['return_summary'])

            st.markdown("### Quality Hotspots (High Volume of Quality-Related Returns)")
            st.dataframe(st.session_state.analysis_results['quality_hotspots'])
            
            st.markdown("### Return Reason Categories")
            st.bar_chart(st.session_state.analysis_results['categorized_returns_df']['category'].value_counts())
        else:
            st.info("Upload and process files or enter data manually to see the dashboard.")

    with tab2:
        display_capa_form()

    with tab3:
        display_document_generation()

if __name__ == "__main__":
    main()
