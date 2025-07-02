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
    """Initializes all required session state variables."""
    defaults = {
        'analysis_results': None,
        'capa_data': {},
        'misc_df': pd.DataFrame()
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# --- UI Components ---
def display_header():
    st.markdown('<div class="main-header"><h1>🏥 Medical Device CAPA Tool</h1><p>Quality Management System for Returns Analysis and CAPA Generation</p></div>', unsafe_allow_html=True)

def process_files(sales_file, returns_file, misc_files, target_sku, report_period_days):
    with st.spinner("Processing files..."):
        sales_raw_df = parse_file(sales_file, sales_file.name)
        if sales_raw_df is None or sales_raw_df.empty:
            st.error("Could not read the Sales Forecast file.")
            return

        sales_df, debug_skus = standardize_sales_data(sales_raw_df, target_sku)
        if sales_df is None or sales_df.empty:
            st.error(f"SKU '{target_sku}' not found in the Sales file.")
            if debug_skus:
                st.warning("Here are some of the SKUs the tool found. Please compare them to your input:")
                st.json(debug_skus)
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
    if not results or 'return_summary' not in results or results['return_summary'].empty: return
    summary = results['return_summary'].iloc[0]
    st.markdown(f"### Analysis for SKU: **{summary['sku']}**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Return Rate", f"{summary['return_rate']:.2f}%")
    col2.metric("Total Units Sold", f"{int(summary['total_sold']):,}")
    col3.metric("Total Units Returned", f"{int(summary['total_returned']):,}")

def display_capa_form():
    """Displays the full CAPA form for data input."""
    st.markdown("## CAPA Information - ISO 13485 Compliant")
    
    prefill_sku = ""
    if st.session_state.analysis_results and not st.session_state.analysis_results.get('return_summary', pd.DataFrame()).empty:
        prefill_sku = st.session_state.analysis_results['return_summary'].iloc[0]['sku']
        
    with st.form("capa_form"):
        st.info("Fill out the required fields below to generate a compliant CAPA report.")
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
            is_valid, errors, warnings = validate_capa_data(capa_data)
            
            if is_valid:
                st.session_state.capa_data = capa_data
                st.success("✅ CAPA data saved successfully!")
                for warning in warnings:
                    st.warning(warning)
            else:
                for error in errors:
                    st.error(f"Failed to save: {error}")

def display_doc_gen():
    st.markdown("## Generate CAPA Document")
    if not st.session_state.capa_data:
        st.warning("Please complete and save the CAPA form before generating a document.")
        return

    if st.button("🚀 Generate Document with AI", type="primary"):
        if not st.session_state.analysis_results:
            st.error("Please process your sales and return data first.")
            return

        with st.spinner("Generating document..."):
            generator = CapaDocumentGenerator(anthropic_api_key=st.secrets.get("ANTHROPIC_API_KEY"))
            ai_content = generator.generate_ai_structured_content(st.session_state.capa_data, st.session_state.analysis_results)
            if ai_content:
                doc_buffer = generator.export_to_docx(st.session_state.capa_data, ai_content)
                st.download_button(
                    label="📥 Download CAPA Document", data=doc_buffer,
                    file_name=f"CAPA_{st.session_state.capa_data['capa_number']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                st.error("Failed to generate content from AI.")

# --- Main Application Flow ---
def main():
    display_header()
    with st.sidebar:
        st.header("⚙️ Controls")
        input_method = st.radio("Choose Input Method", ('File Upload', 'Manual Entry'))
        report_period_days = st.number_input("Report Period (Days)", min_value=1, value=30, help="Used for context and manual entry filtering.")

        st.markdown("---")
        st.header("📁 Data Input")

        if input_method == 'File Upload':
            target_sku = st.text_input("Enter SKU for Returns File*", help="Type or paste the exact SKU your Returns Report is for.")
            sales_file = st.file_uploader("1. Upload Odoo Sales Forecast", type=['csv', 'xlsx'])
            returns_file = st.file_uploader("2. Upload Pivot Return Report", type=['csv', 'xlsx'])
            misc_files = st.file_uploader("3. Upload Miscellaneous Data (Images, etc.)", accept_multiple_files=True)
            
            if st.button("Process Files", type="primary"):
                if not target_sku or not sales_file or not returns_file:
                    st.warning("Please provide an SKU and upload both a sales and returns file.")
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
    
    with tab2:
        display_capa_form()
    with tab3:
        display_doc_gen()

if __name__ == "__main__":
    main()
