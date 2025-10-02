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
            --primary-color: #0068C9;
            --primary-color-light: #E6F0F9;
            --primary-bg: #FFFFFF;
            --secondary-bg: #F0F2F6;
            --text-color: #0B1A3D;
            --secondary-text-color: #475569;
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
        
        h3 {
            font-size: 1.75rem;
            color: var(--text-color);
            font-weight: 700;
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
            text-align: center;
        }
        .main-header h1 {
            font-weight: 700;
            color: var(--text-color);
            font-size: 2.25rem;
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
            border-color: var(--primary-color);
            background-color: var(--primary-color-light);
            color: var(--primary-color);
        }
        /* Primary Button Style */
        [data-testid="stButton"] button.st-emotion-cache-19n6bnc {
             background-color: var(--primary-color);
             color: white;
        }
        [data-testid="stButton"] button.st-emotion-cache-19n6bnc:hover {
             opacity: 0.9;
             color: white;
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
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .st-emotion-cache-12w0qpk { 
            border-radius: 10px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        }
        
        /* --- Tabs --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            border-bottom: 2px solid var(--border-color);
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #F8F9FA;
            border-radius: 8px 8px 0 0;
            border: 1px solid var(--border-color);
            margin-bottom: -1px;
            padding: 0.75rem 1.25rem;
            font-weight: 600;
            color: var(--secondary-text-color);
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--primary-bg);
            border-bottom-color: var(--primary-bg) !important;
            color: var(--primary-color);
        }
        
        /* --- Info/Warning Boxes --- */
        [data-testid="stAlert"] {
            border-radius: 8px;
        }

    </style>
    """, unsafe_allow_html=True)


def get_image_as_base64(path):
    """Helper function to embed a local image."""
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


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
        # Replaced URL with an embedded SVG for reliability
        logo_svg = """
        <svg width="150" height="40" viewBox="0 0 250 66" xmlns="http://www.w3.org/2000/svg">
        <path d="M65.882 23.366c0-13.01-10.55-23.56-23.56-23.56-13.01 0-23.56 10.55-23.56 23.56 0 13.01 10.55 23.56 23.56 23.56 13.01 0 23.56-10.55 23.56-23.56zm-38.35 0c0-8.167 6.623-14.79 14.79-14.79s14.79 6.623 14.79 14.79-6.623 14.79-14.79 14.79-14.79-6.623-14.79-14.79z" fill="#000"/>
        <path d="M96.65 11.536V46.92h-8.825V11.536h8.825zM128.508 11.536l-8.43 14.59-8.423-14.59h-9.74l13.29 22.99v12.394h8.824V34.526l13.29-22.99h-9.81zM161.417 11.536V46.92h-8.825V11.536h8.825z" fill="#000"/>
        <path d="M211.503 24.38c0-5.32-4.31-9.63-9.63-9.63s-9.63 4.31-9.63 9.63 4.31 9.63 9.63 9.63 9.63-4.31 9.63-9.63zm-27.483 22.54h-8.825V11.536h8.825v7.2c1.94-2.85 5.2-4.73 8.94-4.73 7.93 0 14.36 6.43 14.36 14.36s-6.43 14.36-14.36 14.36c-3.74 0-7-1.88-8.94-4.73v11.12h0zM249.03 24.38c0-5.32-4.31-9.63-9.63-9.63s-9.63 4.31-9.63 9.63 4.31 9.63 9.63 9.63 9.63-4.31 9.63-9.63zm-27.483 22.54h-8.825V11.536h8.825v7.2c1.94-2.85 5.2-4.73 8.94-4.73 7.93 0 14.36 6.43 14.36 14.36s-6.43 14.36-14.36 14.36c-3.74 0-7-1.88-8.94-4.73v11.12h0z" fill="#000"/>
        </svg>
        """
        st.markdown(f'<div style="margin-bottom: 2rem;">{logo_svg}</div>', unsafe_allow_html=True)
        
        st.header("Configuration")
        st.session_state.target_sku = st.text_input("Target Product SKU", st.session_state.target_sku)

        date_ranges = {
            "Last 7 Days": timedelta(days=7),
            "Last 30 Days": timedelta(days=30),
            "Last 90 Days": timedelta(days=90),
            "Year to Date": "ytd",
            "Custom Range": "custom"
        }
        selected_range = st.selectbox("Select Date Range", list(date_ranges.keys()))

        today = date.today()
        if selected_range == "Custom Range":
            st.session_state.start_date, st.session_state.end_date = st.date_input(
                "Select a date range", (today - timedelta(days=30), today)
            )
        elif date_ranges[selected_range] == "ytd":
            st.session_state.start_date = date(today.year, 1, 1)
            st.session_state.end_date = today
        else:
            st.session_state.start_date = today - date_ranges[selected_range]
            st.session_state.end_date = today

        st.info(f"Period: {st.session_state.start_date.strftime('%b %d, %Y')} to {st.session_state.end_date.strftime('%b %d, %Y')}")

        st.header("Add Data")
        with st.expander("Manual Data Entry", icon="✍️"):
            manual_sales = st.text_area("Sales Data", placeholder=f"Total units sold for {st.session_state.target_sku} (e.g., 9502)")
            manual_returns = st.text_area("Returns Data", placeholder=f"Total units returned for {st.session_state.target_sku} (e.g., 150)")
            if st.button("Process Manual Data"):
                if not manual_sales:
                    st.warning("Sales data is required.")
                else:
                    sales_df = parse_manual_input(manual_sales, st.session_state.target_sku)
                    returns_df = parse_manual_input(manual_returns, st.session_state.target_sku)
                    process_data(sales_df, returns_df)

        with st.expander("Or Upload Files", icon="📄"):
            uploaded_files = st.file_uploader(
                "Upload sales, returns, or other data files",
                accept_multiple_files=True,
                type=['csv', 'xlsx', 'txt', 'tsv', 'png', 'jpg']
            )
            if st.button("Process Uploaded Files"):
                if uploaded_files:
                    process_uploaded_files(uploaded_files)
                else:
                    st.warning("Please upload at least one file to process.")


def process_data(sales_df: pd.DataFrame, returns_df: pd.DataFrame):
    """Processes sales and returns DataFrames to run and store the main analysis."""
    with st.spinner("Processing data and running analysis..."):
        data_processor = st.session_state.data_processor
        st.session_state.sales_data = data_processor.process_sales_data(sales_df)
        st.session_state.returns_data = data_processor.process_returns_data(returns_df)

        report_days = (st.session_state.end_date - st.session_state.start_date).days
        st.session_state.analysis_results = run_full_analysis(
            sales_df=st.session_state.sales_data,
            returns_df=st.session_state.returns_data,
            report_period_days=report_days,
            unit_cost=st.session_state.unit_cost,
            sales_price=st.session_state.sales_price
        )
    st.success("Analysis complete!")


def process_uploaded_files(uploaded_files: list):
    """Analyzes and processes a list of uploaded files using the AI parser."""
    parser = st.session_state.file_parser
    sales_dfs, returns_dfs = [], []

    with st.spinner("AI is analyzing file structures..."):
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
        combined_sales = pd.concat(sales_dfs) if sales_dfs else pd.DataFrame()
        combined_returns = pd.concat(returns_dfs) if returns_dfs else pd.DataFrame()
        process_data(combined_sales, combined_returns)
    else:
        st.warning("AI could not identify relevant sales or returns data in the uploaded files.")


def display_main_app():
    """Displays the main application interface, including header, sidebar, and tabs."""
    st.markdown(
        '<div class="main-header"><h1>Automated Quality Management System (AQMS)</h1>'
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
        st.divider()
        with st.expander("AI Assistant (Context-Aware)", icon="💬"):
            user_query = st.text_input("Ask the AI about your current analysis:")
            if user_query:
                with st.spinner("AI is synthesizing an answer..."):
                    response = st.session_state.ai_context_helper.generate_response(user_query)
                    st.markdown(response)


def main():
    """Main function to configure and run the Streamlit application."""
    st.set_page_config(
        page_title="AQMS",
        page_icon="https://www.vivehealth.com/cdn/shop/files/vive-logo-1_2_250x.png?v=1613713028",
        layout="wide"
    )

    initialize_session_state()
    load_css()

    if not check_password():
        st.stop()

    initialize_components()
    display_main_app()


if __name__ == "__main__":
    main()
