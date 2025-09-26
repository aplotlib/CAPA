# main.py

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import StringIO

# --- Import custom modules ---
from src.parsers import AIFileParser
from src.data_processing import DataProcessor
from src.analysis import run_full_analysis
from src.document_generator import DocumentGenerator
from src.ai_capa_helper import (
    AICAPAHelper, AIEmailDrafter, MedicalDeviceClassifier,
    RiskAssessmentGenerator, UseRelatedRiskAnalyzer
)
from src.fmea import FMEA
from src.pre_mortem import PreMortem
from src.ai_context_helper import AIContextHelper

# --- Import Tab UIs ---
from src.tabs.dashboard import display_dashboard
from src.tabs.capa import display_capa_tab
from src.tabs.risk_safety import display_risk_safety_tab
from src.tabs.vendor_comms import display_vendor_comm_tab
from src.tabs.compliance import display_compliance_tab
from src.tabs.cost_of_quality import display_cost_of_quality_tab
from src.tabs.human_factors import display_human_factors_tab
from src.tabs.exports import display_exports_tab


def load_css():
    """Loads custom CSS for styling the Streamlit application."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="st-"], [class*="css-"] {
            font-family: 'Inter', sans-serif;
        }
        .main-header h1 {
            font-weight: 700; font-size: 2.2rem; color: #1a1a2e; text-align: center;
        }
        .main-header p {
            color: #4F4F4F; font-size: 1.1rem; text-align: center; margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)


def initialize_session_state():
    """Initializes all required keys in Streamlit's session state with default values."""
    defaults = {
        'openai_api_key': None, 'api_key_missing': True, 'components_initialized': False,
        'target_sku': 'SKU-12345', 'unit_cost': 15.50, 'sales_price': 49.99,
        'start_date': date.today() - timedelta(days=30), 'end_date': date.today(),
        'sales_data': pd.DataFrame(), 'returns_data': pd.DataFrame(),
        'analysis_results': None, 'capa_data': {}, 'fmea_data': pd.DataFrame(),
        'vendor_email_draft': None, 'risk_assessment': None, 'urra': None,
        'pre_mortem_summary': None, 'medical_device_classification': None,
        'human_factors_data': {}, 'logged_in': False, 'workflow_mode': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def initialize_components():
    """
    Initializes all helper classes (AI, data processors, etc.) if an API key is present.
    Ensures components are only initialized once per session.
    """
    if st.session_state.get('components_initialized'):
        return

    api_key = st.secrets.get("OPENAI_API_KEY")
    st.session_state.api_key_missing = not bool(api_key)

    if not st.session_state.api_key_missing:
        st.session_state.openai_api_key = api_key
        # AI and helper class instantiations
        st.session_state.ai_capa_helper = AICAPAHelper(api_key)
        st.session_state.ai_email_drafter = AIEmailDrafter(api_key)
        st.session_state.medical_device_classifier = MedicalDeviceClassifier(api_key)
        st.session_state.risk_assessment_generator = RiskAssessmentGenerator(api_key)
        st.session_state.urra_generator = UseRelatedRiskAnalyzer(api_key)
        st.session_state.fmea_generator = FMEA(api_key)
        st.session_state.pre_mortem_generator = PreMortem(api_key)
        st.session_state.file_parser = AIFileParser(api_key)
        st.session_state.doc_generator = DocumentGenerator()
        st.session_state.data_processor = DataProcessor()
        st.session_state.ai_context_helper = AIContextHelper(api_key)
    
    st.session_state.components_initialized = True


def check_password():
    """Displays a password input and returns True if the password is correct."""
    if st.session_state.get("logged_in", False):
        return True

    st.header("AQMS Login")
    password_input = st.text_input("Password", type="password")

    if st.button("Login"):
        if password_input == st.secrets.get("APP_PASSWORD"):
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("The password you entered is incorrect.")
    return False


def parse_manual_input(input_str: str, target_sku: str) -> pd.DataFrame:
    """Parses manual string input into a DataFrame for sales or returns data."""
    if not input_str.strip():
        return pd.DataFrame()
    
    # Handle simple numeric input
    if input_str.strip().isnumeric():
        return pd.DataFrame([{'sku': target_sku, 'quantity': int(input_str)}])
    
    # Handle CSV-like input
    try:
        if 'sku' not in input_str.lower() or 'quantity' not in input_str.lower():
            # Assume the input is just a quantity if headers are missing
            input_str = f"sku,quantity\n{target_sku},{input_str}"
        return pd.read_csv(StringIO(input_str))
    except Exception:
        st.error("Could not parse manual data.")
        return pd.DataFrame()


def display_sidebar():
    """Renders all the configuration and data input widgets in the sidebar."""
    with st.sidebar:
        st.image("https://www.vivehealth.com/cdn/shop/files/vive-logo-1_2_250x.png?v=1613713028", width=150)
        st.header("Configuration")
        st.session_state.target_sku = st.text_input("Target Product SKU", st.session_state.target_sku)
        
        # Date Range Selection
        st.header("Date Range")
        # ... (rest of sidebar logic) ...


def process_data(sales_df, returns_df):
    """Processes sales and returns DataFrames to run the main analysis."""
    with st.spinner("Processing data..."):
        processor = st.session_state.data_processor
        st.session_state.sales_data = processor.process_sales_data(sales_df)
        st.session_state.returns_data = processor.process_returns_data(returns_df)
        
        days = (st.session_state.end_date - st.session_state.start_date).days
        
        st.session_state.analysis_results = run_full_analysis(
            st.session_state.sales_data,
            st.session_state.returns_data,
            days,
            st.session_state.unit_cost,
            st.session_state.sales_price
        )
    st.success("Analysis complete!")


def process_uploaded_files(uploaded_files):
    """Analyzes and processes a list of uploaded files."""
    parser = st.session_state.file_parser
    sales_dfs, returns_dfs = [], []

    with st.spinner("AI is analyzing files..."):
        for file in uploaded_files:
            analysis = parser.analyze_file_structure(file, st.session_state.target_sku)
            st.write(f"File: `{file.name}` → AI identified as: `{analysis.get('content_type', 'unknown')}`")
            df = parser.extract_data(file, analysis, st.session_state.target_sku)
            if df is not None:
                if analysis.get('content_type') == 'sales':
                    sales_dfs.append(df)
                elif analysis.get('content_type') == 'returns':
                    returns_dfs.append(df)
    
    if sales_dfs or returns_dfs:
        full_sales_df = pd.concat(sales_dfs) if sales_dfs else pd.DataFrame()
        full_returns_df = pd.concat(returns_dfs) if returns_dfs else pd.DataFrame()
        process_data(full_sales_df, full_returns_df)
    else:
        st.warning("AI could not identify relevant sales or returns data in the uploaded files.")


def display_main_app():
    """Displays the main application interface, including the header, sidebar, and tabs."""
    st.markdown('<div class="main-header"><h1>Automated Quality Management System (AQMS)</h1>'
                '<p>Your AI-powered hub for proactive quality assurance.</p></div>', unsafe_allow_html=True)
    
    display_sidebar()

    # Main application tabs
    tabs = st.tabs(["Dashboard", "CAPA", "Risk & Safety", "Human Factors", "Vendor Comms", "Compliance", "Cost of Quality", "Exports"])
    with tabs[0]: display_dashboard()
    with tabs[1]: display_capa_tab()
    with tabs[2]: display_risk_safety_tab()
    # ... (other tabs) ...
    
    # Context-aware AI Assistant
    if not st.session_state.api_key_missing:
        with st.expander("AI Assistant (Context-Aware)"):
            user_query = st.text_input("Ask the AI a question about your current analysis:")
            if user_query:
                with st.spinner("AI is synthesizing an answer..."):
                    response = st.session_state.ai_context_helper.generate_response(user_query)
                    st.markdown(response)


def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="AQMS", layout="wide")
    
    initialize_session_state()
    load_css()
    
    if not check_password():
        st.stop()
        
    initialize_components()
    
    display_main_app()


if __name__ == "__main__":
    main()
