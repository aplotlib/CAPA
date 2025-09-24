# main.py

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import copy

# --- Import custom modules ---
# Note: Ensure all these files exist in the 'src' directory.
from src.parsers import AIFileParser
from src.data_processing import DataProcessor
from src.analysis import run_full_analysis, calculate_cost_benefit
from src.document_generator import CapaDocumentGenerator
from src.ai_capa_helper import (
    AICAPAHelper, AIEmailDrafter, MedicalDeviceClassifier,
    RiskAssessmentGenerator, UseRelatedRiskAnalyzer
)
from src.fmea import FMEA
from src.pre_mortem import PreMortem
from src.ai_context_helper import AIContextHelper
from src.capa_form import display_capa_form

# --- Page Configuration and Styling ---
# This should be the very first Streamlit command.
st.set_page_config(
    page_title="Product Lifecycle & Quality Manager",
    page_icon="🛡️",  # Using an emoji for simplicity and robustness
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Enhanced UI/UX Styling ---
# Moved CSS to a separate function for clarity.
def load_css():
    """Loads custom CSS for styling the application."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }

        /* Main App background */
        .main {
            background-color: #F0F2F6;
        }

        /* Header styling */
        .main-header {
            background: linear-gradient(135deg, #0061ff 0%, #60efff 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .main-header h1 {
            font-weight: 700;
            font-size: 2.5rem;
        }

        /* Metric cards */
        .stMetric {
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 1.5rem;
            border: 1px solid #E0E0E0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #F0F2F6;
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF;
        }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Session State and Component Initialization ---

def initialize_session_state():
    """Initializes all necessary variables in Streamlit's session state."""
    # Central place for all session state keys
    STATE_DEFAULTS = {
        'components_initialized': False,
        'api_key_missing': True,
        'anthropic_api_key': None,
        'target_sku': 'SKU-12345',
        'unit_cost': 15.50,
        'sales_price': 49.99,
        'start_date': date.today() - timedelta(days=30),
        'end_date': date.today(),
        'sales_data': {},
        'returns_data': {},
        'pending_image_confirmations': [],
        'analysis_results': None,
        'capa_feasibility_analysis': None,
        'capa_data': {},
        'fmea_data': None,
        'pre_mortem_summary': None,
        'medical_device_classification': None,
        'vendor_email_draft': None,
        'risk_assessment': None,
        'urra': None
    }
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

def initialize_components():
    """Initializes all AI-powered components and helpers."""
    if not st.session_state.components_initialized:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if not api_key:
            st.warning("Anthropic API key not found. AI features will be limited.")
            st.session_state.api_key_missing = True
        else:
            st.session_state.anthropic_api_key = api_key
            st.session_state.api_key_missing = False

        # Initialize components, they will handle the missing key internally.
        st.session_state.file_parser = AIFileParser(api_key)
        st.session_state.data_processor = DataProcessor(api_key)
        st.session_state.ai_context_helper = AIContextHelper(api_key)
        st.session_state.ai_capa_helper = AICAPAHelper(api_key)
        st.session_state.medical_device_classifier = MedicalDeviceClassifier(api_key)
        st.session_state.risk_assessment_generator = RiskAssessmentGenerator(api_key)
        st.session_state.urra_generator = UseRelatedRiskAnalyzer(api_key)
        st.session_state.fmea_generator = FMEA(api_key)
        st.session_state.pre_mortem_generator = PreMortem(api_key)
        st.session_state.doc_generator = CapaDocumentGenerator(api_key)
        st.session_state.components_initialized = True

# --- Helper Functions ---

def trigger_final_analysis():
    """Consolidates all data and runs the main analysis."""
    # This function is a placeholder for your data processing logic
    st.info("Triggering final analysis...")
    # Add your logic to process sales_data and returns_data and then run run_full_analysis
    # For demonstration, we'll just show a success message.
    st.success("Analysis triggered (placeholder).")


# --- UI Sections ---

def display_header():
    """Displays the main header of the application."""
    st.markdown(
        '<div class="main-header">'
        '<h1>🛡️ Product Lifecycle & Quality Manager</h1>'
        '<p>Your AI-powered hub for proactive quality assurance, compliance, and vendor management.</p>'
        '</div>',
        unsafe_allow_html=True
    )

def display_sidebar():
    """Displays the sidebar for data input and configuration."""
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.session_state.target_sku = st.text_input("Target Product SKU", value=st.session_state.target_sku)
        st.session_state.unit_cost = st.number_input("Unit Cost ($)", min_value=0.0, value=st.session_state.unit_cost, format="%.2f")
        st.session_state.sales_price = st.number_input("Sales Price ($)", min_value=0.0, value=st.session_state.sales_price, format="%.2f")
        st.session_state.start_date = st.date_input("Start Date", value=st.session_state.start_date)
        st.session_state.end_date = st.date_input("End Date", value=st.session_state.end_date)

        st.header("➕ Add Data")
        uploaded_files = st.file_uploader(
            "Upload Sales/Returns Files (CSV, Excel, Images)",
            accept_multiple_files=True,
            type=['csv', 'xlsx', 'png', 'jpg', 'jpeg']
        )
        if uploaded_files:
            with st.spinner("AI is analyzing files..."):
                # File processing logic would go here
                st.success(f"{len(uploaded_files)} files uploaded and queued for processing.")

        if st.button("Process Data & Run Analysis", type="primary", use_container_width=True):
            # This is where you would call your data processing and analysis functions
            # For now, it's a placeholder.
            st.session_state.analysis_results = {
                'return_summary': pd.DataFrame({
                    'sku': [st.session_state.target_sku], 'total_sold': [1000], 'total_returned': [120], 'return_rate': [12.0]
                }),
                'quality_metrics': {'quality_score': 72, 'risk_level': 'Medium'},
                'insights': 'Return rate is slightly above industry average. Investigation recommended.'
            }
            st.success("Analysis complete!")


def display_dashboard():
    """Displays the main dashboard with metrics and analyses."""
    with st.expander("💡 Why a Proactive Approach to Quality Matters"):
        st.markdown("""
        A proactive approach to quality is a strategic business investment. By focusing on **prevention** and **monitoring**, you can significantly reduce the high costs associated with both internal and external failures, leading to lower total costs, increased revenue, and higher brand equity.
        """)

    st.header("📊 Quality Dashboard")
    if not st.session_state.analysis_results:
        st.info('**Welcome!** Start by configuring your product in the sidebar and clicking "Process Data & Run Analysis."')
        return

    results = st.session_state.analysis_results
    summary_data = results['return_summary'].iloc[0]

    st.markdown(f"### Overall Analysis for SKU: **{summary_data['sku']}**")
    cols = st.columns(4)
    cols[0].metric("Return Rate", f"{summary_data['return_rate']:.2f}%", help="Percentage of units sold that were returned.")
    cols[1].metric("Total Sold", f"{int(summary_data['total_sold']):,}", help="Total units sold.")
    cols[2].metric("Total Returned", f"{int(summary_data['total_returned']):,}", help="Total units returned.")
    cols[3].metric("Quality Score", f"{results['quality_metrics'].get('quality_score', 'N/A')}/100", delta=results['quality_metrics'].get('risk_level', ''), help="AI-calculated score based on return rate.")

    st.markdown(f"**AI Insights**: {results.get('insights', 'No insights generated.')}")

    st.markdown("---")
    st.subheader("💡 Cost-Benefit Analysis for Potential Fix")
    if st.session_state.unit_cost <= 0:
        st.warning("Please set a 'Unit Cost' greater than zero in the sidebar to run this analysis.")
    else:
        with st.form("cost_benefit_form"):
            col1, col2 = st.columns(2)
            cost_change = col1.number_input("Cost increase per unit ($)", min_value=0.0, step=0.01, format="%.2f")
            expected_rr_reduction = col2.number_input("Expected return rate reduction (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
            submitted = st.form_submit_button("Calculate Financial Impact", use_container_width=True, type="primary")

            if submitted:
                report_period_days = (st.session_state.end_date - st.session_state.start_date).days
                with st.spinner("Calculating..."):
                    st.session_state.capa_feasibility_analysis = calculate_cost_benefit(
                        analysis_results=results, current_unit_cost=st.session_state.unit_cost,
                        cost_change=cost_change, expected_rr_reduction=expected_rr_reduction,
                        report_period_days=report_period_days
                    )

    if st.session_state.capa_feasibility_analysis:
        cb_results = st.session_state.capa_feasibility_analysis
        st.success(f"**Summary:** {cb_results['summary']}")
        with st.expander("Show detailed calculation"):
            st.table(pd.DataFrame.from_dict(cb_results['details'], orient='index', columns=["Value"]))

def display_risk_safety_tab():
    st.header("🛡️ Risk & Safety Analysis")
    st.info("This section is for FMEA, ISO 14971 Risk Assessments, and other safety analyses. (Placeholder)")
    # Add your FMEA and Risk Assessment UI components here

def display_vendor_comm_tab():
    st.header("✉️ Vendor Communications")
    st.info("Draft and manage communications with your vendors. (Placeholder)")
    # Add your vendor email drafting UI here

def display_compliance_tab():
    st.header("⚖️ Compliance Center")
    st.info("Tools for ensuring regulatory compliance. (Placeholder)")
    # Add your compliance checklist and validation tools here

def display_resources_tab():
    """Displays a tab with resources and industry standards."""
    st.header("📚 Resources & Industry Standards")
    st.info("A quick reference for key regulations and standards in the medical device industry.")

    st.subheader("Key Quality & Risk Management Standards")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("##### **ISO 13485:2016**")
            st.markdown("The international standard for a Quality Management System (QMS) for medical devices.")
    with col2:
        with st.container(border=True):
            st.markdown("##### **ISO 14971**")
            st.markdown("The international standard for the application of risk management to medical devices.")

def display_exports_tab():
    st.header("📄 Exports")
    st.info("Generate and download comprehensive reports. (Placeholder)")
    st.button("Generate Combined Word Report", type="primary")
    # Add your document generation and download logic here

def display_ai_chat_interface(tab_name: str):
    """A placeholder for a contextual AI chat interface."""
    st.markdown("---")
    st.subheader(f"🤖 AI Assistant for {tab_name}")
    user_query = st.text_input("Ask the AI a question about the data on this page...")
    if user_query:
        with st.spinner("AI is thinking..."):
            # In a real implementation, you would call:
            # response = st.session_state.ai_context_helper.generate_response(user_query)
            response = "This is a placeholder response from the AI assistant."
            st.markdown(response)

# --- Main Application Flow ---

def main():
    """Main function to run the Streamlit application."""
    initialize_session_state()
    load_css()
    display_header()
    initialize_components()
    display_sidebar()

    # --- Tab Navigation ---
    tab_titles = [
        "📊 Dashboard", "📝 CAPA", "🛡️ Risk & Safety", "✉️ Vendor Comms",
        "⚖️ Compliance", "📚 Resources", "📄 Exports"
    ]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        display_dashboard()
        display_ai_chat_interface("the Dashboard")
    with tabs[1]:
        display_capa_form()
    with tabs[2]:
        display_risk_safety_tab()
    with tabs[3]:
        display_vendor_comm_tab()
    with tabs[4]:
        display_compliance_tab()
    with tabs[5]:
        display_resources_tab()
    with tabs[6]:
        display_exports_tab()

if __name__ == "__main__":
    main()
