# main.py

import sys
import os

# Add the project root to the Python path to resolve KeyErrors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import StringIO
import base64

# --- Import custom application modules ---
from src.parsers import AIFileParser
from src.data_processing import DataProcessor
from src.analysis import run_full_analysis
from src.document_generator import DocumentGenerator
from src.ai_capa_helper import (
    AICAPAHelper, AIEmailDrafter, MedicalDeviceClassifier,
    RiskAssessmentGenerator, UseRelatedRiskAnalyzer, AIHumanFactorsHelper
)
from src.fmea import FMEA
from src.pre_mortem import PreMortem
from src.ai_context_helper import AIContextHelper

# --- Import Tab UI modules ---
from src.tabs.dashboard import display_dashboard
from src.tabs.capa import display_capa_tab
from src.tabs.risk_safety import display_risk_safety_tab
from src.tabs.vendor_comms import display_vendor_comm_tab
from src.tabs.compliance import display_compliance_tab
from src.tabs.cost_of_quality import display_cost_of_quality_tab
from src.tabs.human_factors import display_human_factors_tab
from src.tabs.exports import display_exports_tab
from src.tabs.capa_closure import display_capa_closure_tab


def load_css():
    """Loads a custom CSS stylesheet to improve the application's appearance."""
    st.markdown("""
    <style>
        /* --- CSS Variables for Theming --- */
        :root {
            --primary-color: #005A9E; /* A professional blue */
            --primary-color-light: #E6F0F9;
            --primary-bg: #FFFFFF;
            --secondary-bg: #F8F9FA; /* Light gray for the main background */
            --text-color: #212529; /* Dark gray for text */
            --secondary-text-color: #6C757D; /* Lighter gray for secondary text */
            --border-color: #DEE2E6;
        }

        /* --- Base Styles --- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        html, body, [class*="st-"], [class*="css-"] {
            font-family: 'Inter', sans-serif;
            color: var(--text-color);
        }

        .main {
            background-color: var(--secondary-bg);
        }
        
        h1, h2, h3 {
            font-weight: 700;
            color: var(--text-color);
        }
        
        h3 {
            font-size: 1.75rem;
        }

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {
            background-color: var(--primary-bg);
            border-right: 1px solid var(--border-color);
        }

        /* --- Main Header --- */
        .main-header {
            background-color: var(--primary-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        .main-header h1 {
            color: var(--primary-color);
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        .main-header p {
            color: var(--secondary-text-color);
            font-size: 1.1rem;
        }

        /* --- Buttons --- */
        [data-testid="stButton"] button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1rem;
            border: 1px solid var(--primary-color);
            background-color: var(--primary-bg);
            color: var(--primary-color);
        }
        [data-testid="stButton"] button:hover {
            border-color: #004B82;
            background-color: var(--primary-color-light);
            color: #004B82;
        }
        
        /* Primary Button Style */
        [data-testid="stButton"] button.st-emotion-cache-19n6bnc, [data-testid="stButton"] button[kind="primary"] {
             background-color: var(--primary-color) !important;
             color: white !important;
             border: 1px solid var(--primary-color) !important;
        }
        [data-testid="stButton"] button.st-emotion-cache-19n6bnc:hover, [data-testid="stButton"] button[kind="primary"]:hover {
             background-color: #004B82 !important;
             border-color: #004B82 !important;
             color: white !important;
        }

        /* --- Containers & Expanders --- */
        [data-testid="stExpander"] {
            border: 1px solid var(--border-color);
            border-radius: 10px;
            background-color: var(--primary-bg);
        }
        
        [data-testid="stExpander"] summary {
            font-weight: 600;
            color: var(--text-color);
            font-size: 1.1rem;
        }
        
        /* --- Tabs --- */
        .stTabs [data-baseweb="tab-list"] {
            border-bottom: 2px solid var(--border-color);
            gap: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-radius: 8px 8px 0 0;
            border: none;
            margin-bottom: -2px;
            padding: 0.75rem 1.25rem;
            font-weight: 600;
            color: var(--secondary-text-color);
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--primary-bg);
            border: 2px solid var(--border-color);
            border-bottom: 2px solid var(--primary-bg) !important;
            color: var(--primary-color);
        }
        
    </style>
    """, unsafe_allow_html=True)


def get_local_image_as_base64(path):
    """Helper function to embed a local image reliably."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return None

def initialize_session_state():
    """Initializes all required keys in Streamlit's session state with default values."""
    defaults = {
        'openai_api_key': None, 'api_key_missing': True, 'components_initialized': False,
        'product_info': {
            'sku': 'SKU-12345',
            'name': 'Example Product',
            'ifu': 'This is an example Intended for Use statement.'
        },
        'unit_cost': 15.50, 'sales_price': 49.99,
        'start_date': date.today() - timedelta(days=30), 'end_date': date.today(),
        'sales_data': pd.DataFrame(), 'returns_data': pd.DataFrame(),
        'analysis_results': None, 'capa_data': {}, 'fmea_data': pd.DataFrame(),
        'vendor_email_draft': None, 'risk_assessment': None, 'urra': None,
        'pre_mortem_summary': None, 'medical_device_classification': None,
        'human_factors_data': {}, 'logged_in': False, 'workflow_mode': 'CAPA Management'
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
        st.session_state.ai_hf_helper = AIHumanFactorsHelper(api_key)

    st.session_state.components_initialized = True


def check_password():
    """Displays a password input and returns True if the password is correct."""
    if st.session_state.get("logged_in", False):
        return True

    logo_base64 = get_local_image_as_base64("logo.png")
    if logo_base64:
        st.markdown(f'<div style="text-align: center; margin-bottom: 2rem;"><img src="data:image/png;base64,{logo_base64}" width="150"></div>', unsafe_allow_html=True)

    st.title("Automated Quality Management System")
    st.header("Login")
    
    with st.form("login_form"):
        password_input = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
        submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

        if submitted:
            if password_input == st.secrets.get("APP_PASSWORD", "admin"): # Added a default password for easy testing
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("The password you entered is incorrect.")
    return False


def parse_manual_input(input_str: str, target_sku: str) -> pd.DataFrame:
    """Parses manual string input into a DataFrame for sales or returns data."""
    if not input_str.strip():
        return pd.DataFrame()

    if input_str.strip().isnumeric():
        return pd.DataFrame([{'sku': target_sku, 'quantity': int(input_str)}])

    try:
        if 'sku' not in input_str.lower() or 'quantity' not in input_str.lower():
            input_str = f"sku,quantity\n{target_sku},{input_str}"
        return pd.read_csv(StringIO(input_str))
    except Exception:
        st.error("Could not parse manual data.")
        return pd.DataFrame()


def display_sidebar():
    """Renders all configuration and data input widgets in the sidebar."""
    with st.sidebar:
        logo_base64 = get_local_image_as_base64("logo.png")
        if logo_base64:
            st.image(f"data:image/png;base64,{logo_base64}", width=100)
        
        st.header("Configuration")
        
        st.session_state.workflow_mode = st.selectbox(
            "Workflow Mode",
            ["CAPA Management", "New Product Introduction", "Post-Market Surveillance"]
        )
        
        with st.expander("📝 Product Information", expanded=True):
            product_info = st.session_state.product_info
            product_info['sku'] = st.text_input("Target Product SKU", product_info['sku'])
            product_info['name'] = st.text_input("Product Name", product_info['name'])
            product_info['ifu'] = st.text_area("Intended for Use (IFU)", product_info['ifu'], height=100)

        with st.expander("🗓️ Reporting Period"):
            date_ranges = {
                "Last 7 Days": timedelta(days=7), "Last 30 Days": timedelta(days=30),
                "Last 90 Days": timedelta(days=90), "Year to Date": "ytd", "Custom Range": "custom"
            }
            selected_range = st.selectbox("Select Date Range", list(date_ranges.keys()), index=1)
            today = date.today()
            if selected_range == "Custom Range":
                st.session_state.start_date, st.session_state.end_date = st.date_input(
                    "Select a date range", (today - timedelta(days=30), today)
                )
            elif date_ranges[selected_range] == "ytd":
                st.session_state.start_date = date(today.year, 1, 1); st.session_state.end_date = today
            else:
                st.session_state.start_date = today - date_ranges[selected_range]; st.session_state.end_date = today
            st.caption(f"Period: {st.session_state.start_date.strftime('%b %d, %Y')} to {st.session_state.end_date.strftime('%b %d, %Y')}")

        st.header("Data Input")
        target_sku = st.session_state.product_info['sku']
        with st.expander("✍️ Manual Data Entry"):
            manual_sales = st.text_area("Sales Data", placeholder=f"Total units sold for {target_sku}...")
            manual_returns = st.text_area("Returns Data", placeholder=f"Total units returned for {target_sku}...")
            if st.button("Process Manual Data", type="primary", use_container_width=True):
                if manual_sales:
                    process_data(parse_manual_input(manual_sales, target_sku), parse_manual_input(manual_returns, target_sku))
                else:
                    st.warning("Sales data is required.")

        with st.expander("📄 File Upload"):
            uploaded_files = st.file_uploader("Upload sales, returns, etc.", accept_multiple_files=True, type=['csv', 'xlsx', 'txt', 'tsv', 'png', 'jpg'])
            if st.button("Process Uploaded Files", type="primary", use_container_width=True):
                if uploaded_files:
                    process_uploaded_files(uploaded_files)
                else:
                    st.warning("Please upload at least one file.")


def process_data(sales_df: pd.DataFrame, returns_df: pd.DataFrame):
    """Processes sales and returns DataFrames to run and store the main analysis."""
    with st.spinner("Processing data and running analysis..."):
        data_processor = st.session_state.data_processor
        st.session_state.sales_data = data_processor.process_sales_data(sales_df)
        st.session_state.returns_data = data_processor.process_returns_data(returns_df)
        report_days = (st.session_state.end_date - st.session_state.start_date).days
        st.session_state.analysis_results = run_full_analysis(
            sales_df=st.session_state.sales_data, returns_df=st.session_state.returns_data,
            report_period_days=report_days, unit_cost=st.session_state.unit_cost,
            sales_price=st.session_state.sales_price
        )
    st.success("Analysis complete!")


def process_uploaded_files(uploaded_files: list):
    """Analyzes and processes a list of uploaded files using the AI parser."""
    parser = st.session_state.file_parser
    sales_dfs, returns_dfs = [], []
    target_sku = st.session_state.product_info['sku']
    with st.spinner("AI is analyzing file structures..."):
        for file in uploaded_files:
            analysis = parser.analyze_file_structure(file, target_sku)
            st.caption(f"`{file.name}` → AI identified as: `{analysis.get('content_type', 'unknown')}`")
            df = parser.extract_data(file, analysis, target_sku)
            if df is not None:
                content_type = analysis.get('content_type')
                if content_type == 'sales': sales_dfs.append(df)
                elif content_type == 'returns': returns_dfs.append(df)
    if sales_dfs or returns_dfs:
        process_data(pd.concat(sales_dfs) if sales_dfs else pd.DataFrame(), pd.concat(returns_dfs) if returns_dfs else pd.DataFrame())
    else:
        st.warning("AI could not identify relevant sales or returns data in the uploaded files.")


def display_main_app():
    """Displays the main application interface, including header, sidebar, and tabs."""
    st.markdown(
        '<div class="main-header"><h1>Automated Quality Management System</h1>'
        '<p>Your AI-powered hub for proactive quality assurance, compliance, and vendor management.</p></div>',
        unsafe_allow_html=True
    )
    display_sidebar()
    tab_list = ["Dashboard", "CAPA", "CAPA Closure", "Risk & Safety", "Human Factors", "Vendor Comms", "Compliance", "Cost of Quality", "Exports"]
    tabs = st.tabs(tab_list)
    with tabs[0]: display_dashboard()
    with tabs[1]: display_capa_tab()
    with tabs[2]: display_capa_closure_tab()
    with tabs[3]: display_risk_safety_tab()
    with tabs[4]: display_human_factors_tab()
    with tabs[5]: display_vendor_comm_tab()
    with tabs[6]: display_compliance_tab()
    with tabs[7]: display_cost_of_quality_tab()
    with tabs[8]: display_exports_tab()
    if not st.session_state.api_key_missing:
        with st.expander("💬 AI Assistant (Context-Aware)"):
            user_query = st.text_input("Ask the AI about your current analysis:", key="ai_assistant_query")
            if user_query:
                with st.spinner("AI is synthesizing an answer..."):
                    st.markdown(st.session_state.ai_context_helper.generate_response(user_query))

def main():
    """Main function to configure and run the Streamlit application."""
    st.set_page_config(page_title="AQMS", layout="wide", page_icon="logo.png")
    initialize_session_state()
    load_css()
    if not check_password():
        st.stop()
    initialize_components()
    display_main_app()

if __name__ == "__main__":
    main()
