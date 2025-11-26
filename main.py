# main.py

import sys
import os
import streamlit as st
from datetime import date, timedelta
import base64
import yaml
from functools import lru_cache

# FIX: Disable file watcher to prevent resource exhaustion on some systems
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'

# Get the absolute path of the app and src directories
APP_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(APP_DIR, 'src')

# FIX: Add both app and src directories to the Python path
sys.path.insert(0, APP_DIR)
sys.path.insert(0, SRC_DIR)

# FIX: Centralize AI helper initialization with a factory
from ai_factory import AIHelperFactory
# NEW: Import the audit logger
from audit_logger import AuditLogger

# Lazy import function to load modules only when needed
def lazy_import(module_name, class_name=None):
    """Lazy import modules to reduce initial load time"""
    # Imports are now relative to the 'src' directory
    module = __import__(module_name, fromlist=[class_name] if class_name else [])
    if class_name:
        return getattr(module, class_name)
    return module

# Core imports that are always needed
import pandas as pd
from io import StringIO

# CSS and UI setup functions
def load_css():
    """Loads the ORION Cyberpunk/Space Custom CSS."""
    st.markdown("""
    <style>
        /* --- ORION THEME: Cyberpunk / Outer Space --- */
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;700&family=Inter:wght@300;400;600&display=swap');

        :root {
            --bg-deep-space: #0B0E14;
            --bg-panel: #151922;
            --bg-panel-transparent: rgba(21, 25, 34, 0.85);
            --neon-cyan: #00F3FF;
            --neon-pink: #FF00FF;
            --neon-green: #00FF9D;
            --text-primary: #E0E6ED;
            --text-secondary: #94A3B8;
            --border-color: #2D3748;
            --glass-border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* --- Global Styles --- */
        .stApp {
            background-color: var(--bg-deep-space);
            background-image: radial-gradient(circle at 50% 0%, #1a202c 0%, var(--bg-deep-space) 70%);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
        }
        
        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif;
            color: var(--text-primary);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        h1 {
            background: linear-gradient(90deg, var(--neon-cyan), var(--text-primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0px 0px 20px rgba(0, 243, 255, 0.3);
        }

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {
            background-color: var(--bg-panel);
            border-right: 1px solid var(--border-color);
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            font-family: 'Rajdhani', sans-serif;
        }

        /* --- Containers & Expanders (Glassmorphism) --- */
        [data-testid="stContainer"], [data-testid="stExpander"] {
            background-color: var(--bg-panel-transparent);
            border: var(--glass-border);
            border-radius: 8px;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            margin-bottom: 1rem;
        }
        
        [data-testid="stExpander"] summary {
            font-family: 'Rajdhani', sans-serif;
            font-weight: 600;
            font-size: 1.1rem;
            color: var(--neon-cyan);
        }
        [data-testid="stExpander"] summary:hover {
            color: var(--neon-green);
        }

        /* --- Buttons --- */
        [data-testid="stButton"] button {
            border-radius: 4px;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: 1px solid var(--neon-cyan);
            background-color: transparent;
            color: var(--neon-cyan);
            transition: all 0.3s ease;
        }
        [data-testid="stButton"] button:hover {
            background-color: rgba(0, 243, 255, 0.1);
            box-shadow: 0 0 10px rgba(0, 243, 255, 0.5);
            border-color: var(--neon-cyan);
            color: #fff;
        }
        [data-testid="stButton"] button[kind="primary"] {
             background: linear-gradient(45deg, #007bb5, #00F3FF);
             color: #000;
             border: none;
        }
        [data-testid="stButton"] button[kind="primary"]:hover {
             box-shadow: 0 0 15px var(--neon-cyan);
        }

        /* --- Inputs --- */
        .stTextInput input, .stTextArea textarea, .stSelectbox, .stDateInput input {
            background-color: rgba(0, 0, 0, 0.3);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: 4px;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: var(--neon-cyan);
            box-shadow: 0 0 5px rgba(0, 243, 255, 0.3);
        }

        /* --- Tabs --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        .stTabs [data-baseweb="tab"] {
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.1rem;
            color: var(--text-secondary);
        }
        .stTabs [aria-selected="true"] {
            color: var(--neon-cyan) !important;
            border-bottom-color: var(--neon-cyan) !important;
            text-shadow: 0 0 8px rgba(0, 243, 255, 0.6);
        }

        /* --- Metrics --- */
        [data-testid="stMetric"] {
            background-color: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border-color);
            border-left: 3px solid var(--neon-pink);
        }
        [data-testid="stMetric"] label {
            color: var(--text-secondary);
            font-family: 'Rajdhani', sans-serif;
        }
        [data-testid="stMetric"] .st-emotion-cache-1g8sfyr {
            color: var(--text-primary);
            font-family: 'Orbitron', sans-serif;
        }
    </style>
    """, unsafe_allow_html=True)

def get_local_image_as_base64(path):
    """Helper function to embed a local image reliably."""
    abs_path = os.path.join(APP_DIR, path)
    try:
        with open(abs_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return None

def initialize_session_state():
    """Initializes all required keys in Streamlit's session state."""
    defaults = {
        'openai_api_key': None,
        'api_key_missing': True,
        'components_initialized': False,
        'loaded_modules': {},
        'active_workflow': None,
        'product_info': {
            'sku': 'SKU-ORION-01',
            'name': 'Neural Interface Beta',
            'ifu': 'Intended for direct neural link monitoring.'
        },
        'unit_cost': 150.00,
        'sales_price': 500.00,
        'start_date': date.today() - timedelta(days=30),
        'end_date': date.today(),
        'sales_data': pd.DataFrame(),
        'returns_data': pd.DataFrame(),
        'analysis_results': None,
        'capa_data': {}, # Stores current working CAPA
        'capa_closure_data': {}, # Maintained for compatibility, but logic merged to capa_data
        'fmea_data': pd.DataFrame(),
        'vendor_email_draft': None,
        'risk_assessment': None,
        'urra': None,
        'pre_mortem_summary': None,
        'medical_device_classification': None,
        'human_factors_data': {},
        'logged_in': False,
        'workflow_mode': 'CAPA Management',
        'product_dev_data': {},
        'final_review_summary': None,
        'coq_results': None,
        'fmea_rows': [],
        'manual_content': {},
        'project_charter_data': {},
        'capa_current_stage': 'Intake' 
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

@st.cache_resource
def get_api_key():
    """Cache the API key retrieval"""
    return st.secrets.get("OPENAI_API_KEY")

def initialize_components():
    """
    Initializes all application components.
    """
    if st.session_state.get('components_initialized'):
        return

    api_key = get_api_key()
    st.session_state.api_key_missing = not bool(api_key)

    DataProcessor = lazy_import('data_processing', 'DataProcessor')
    DocumentGenerator = lazy_import('document_generator', 'DocumentGenerator')
    st.session_state.data_processor = DataProcessor()
    st.session_state.doc_generator = DocumentGenerator()
    st.session_state.audit_logger = AuditLogger()

    if not st.session_state.api_key_missing:
        st.session_state.openai_api_key = api_key
        AIHelperFactory.initialize_ai_helpers(api_key)

    st.session_state.components_initialized = True

def check_password():
    """Displays a password input and returns True if the password is correct."""
    if st.session_state.get("logged_in", False):
        return True

    # Use a simpler layout for login but keep the styles
    st.set_page_config(page_title="ORION Login", layout="centered", initial_sidebar_state="collapsed")
    load_css() 

    with st.container():
        st.markdown("<h1 style='text-align: center;'>ORION SYSTEM</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: var(--neon-cyan);'>Operational Risk & Incident Oversight Network</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            password_input = st.text_input("Access Code", type="password", label_visibility="collapsed", placeholder="Enter Code")
            submitted = st.form_submit_button("INITIALIZE LINK", use_container_width=True, type="primary")

            if submitted:
                if password_input == st.secrets.get("APP_PASSWORD", "admin"):
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("ACCESS DENIED")
    return False

def display_sidebar():
    """Renders all configuration and data input widgets in the sidebar."""
    from utils import parse_manual_input
    with st.sidebar:
        st.title("ORION")
        st.caption("v3.0.1 // STABLE")
        st.divider()

        st.session_state.workflow_mode = st.selectbox(
            "System Module",
            ["CAPA Management", "Product Development"]
        )

        with st.expander("Target Asset", expanded=True):
            product_info = st.session_state.product_info
            product_info['sku'] = st.text_input("Asset SKU", product_info.get('sku', ''), key="sidebar_sku")
            product_info['name'] = st.text_input("Asset Name", product_info.get('name', ''), key="sidebar_name")
            product_info['ifu'] = st.text_area("Primary Directive (IFU)", product_info.get('ifu', ''), height=100, key="sidebar_ifu")

        with st.expander("Financials (Optional)"):
            st.session_state.unit_cost = st.number_input("Unit Cost ($)", value=st.session_state.get('unit_cost', 0.0), step=1.0, format="%.2f")
            st.session_state.sales_price = st.number_input("Sales Price ($)", value=st.session_state.get('sales_price', 0.0), step=1.0, format="%.2f")

        if st.session_state.workflow_mode == "CAPA Management":
            st.header("Telemetry Input")
            st.caption("Upload recent field data")

            with st.expander("Reporting Period"):
                st.session_state.start_date, st.session_state.end_date = st.date_input(
                    "Select a date range",
                    (st.session_state.start_date, st.session_state.end_date)
                )

            target_sku = st.session_state.product_info['sku']
            
            input_tabs = st.tabs(["Manual Entry", "File Upload"])

            with input_tabs[0]:
                with st.form("manual_data_form"):
                    manual_sales = st.text_area("Sales Data", placeholder=f"Total units sold for {target_sku}...")
                    manual_returns = st.text_area("Returns Data", placeholder=f"Total units returned for {target_sku}...")
                    if st.form_submit_button("Process Manual Data", type="primary", use_container_width=True):
                        if manual_sales:
                            process_data(parse_manual_input(manual_sales, target_sku), parse_manual_input(manual_returns, target_sku))
                        else:
                            st.warning("Sales data is required.")

            with input_tabs[1]:
                with st.form("file_upload_form"):
                    uploaded_files = st.file_uploader("Upload sales, returns, etc.", accept_multiple_files=True, type=['csv', 'xlsx', 'txt', 'tsv', 'png', 'jpg'])
                    if st.form_submit_button("Process Uploaded Files", type="primary", use_container_width=True):
                        if uploaded_files:
                            process_uploaded_files(uploaded_files)
                        else:
                            st.warning("Please upload at least one file.")

@st.cache_data
def run_cached_analysis(sales_df, returns_df, report_days, unit_cost, sales_price):
    """Wrapper to cache the full analysis function."""
    run_full_analysis = lazy_import('analysis', 'run_full_analysis')
    return run_full_analysis(sales_df, returns_df, report_days, unit_cost, sales_price)

def process_data(sales_df: pd.DataFrame, returns_df: pd.DataFrame):
    """Processes sales and returns DataFrames to run and store the main analysis."""
    with st.spinner("Processing data and running analysis..."):
        st.session_state.sales_data = st.session_state.data_processor.process_sales_data(sales_df)
        st.session_state.returns_data = st.session_state.data_processor.process_returns_data(returns_df)
        report_days = (st.session_state.end_date - st.session_state.start_date).days

        results = run_cached_analysis(
            st.session_state.sales_data,
            st.session_state.returns_data,
            report_days,
            st.session_state.unit_cost,
            st.session_state.sales_price
        )
        st.session_state.analysis_results = results

        if results and 'return_summary' in results and not results['return_summary'].empty:
            summary = results['return_summary'].iloc[0]
            st.session_state.audit_logger.log_action(
                user="system",
                action="run_data_analysis",
                entity="dashboard_metrics",
                details={
                    "sku": summary.get('sku'),
                    "return_rate": f"{summary.get('return_rate', 0):.2f}%",
                    "total_sold": summary.get('total_sold'),
                    "total_returned": summary.get('total_returned')
                }
            )
    st.toast("Analysis complete!", icon="✅")

def process_uploaded_files(uploaded_files: list):
    """Analyzes and processes a list of uploaded files using the AI parser."""
    if st.session_state.api_key_missing:
        st.error("Cannot process files without an OpenAI API key.")
        return

    parser = st.session_state.parser
    sales_dfs, returns_dfs = [], []
    target_sku = st.session_state.product_info['sku']

    with st.spinner("AI is analyzing file structures..."):
        for file in uploaded_files:
            analysis = parser.analyze_file_structure(file, target_sku)
            st.caption(f"`{file.name}` → AI identified as: `{analysis.get('content_type', 'unknown')}`")
            df = parser.extract_data(file, analysis, target_sku)
            if df is not None and not df.empty:
                content_type = analysis.get('content_type')
                if content_type == 'sales':
                    sales_dfs.append(df)
                elif content_type == 'returns':
                    returns_dfs.append(df)

    if sales_dfs or returns_dfs:
        process_data(
            pd.concat(sales_dfs) if sales_dfs else pd.DataFrame(),
            pd.concat(returns_dfs) if returns_dfs else pd.DataFrame()
        )
    else:
        st.warning("AI could not identify relevant sales or returns data in the uploaded files.")

def display_main_app():
    """Displays the main application interface, including header, sidebar, and tabs."""
    st.markdown(
        '<div class="main-header"><h1>ORION <span style="font-size: 0.5em; color: var(--neon-cyan); vertical-align: middle;">// SYSTEM ACTIVE</span></h1>'
        f'<p>Module Loaded: <strong style="color: var(--neon-green)">{st.session_state.workflow_mode.upper()}</strong></p></div>',
        unsafe_allow_html=True
    )

    display_sidebar()

    if st.session_state.workflow_mode == "CAPA Management":
        display_capa_workflow()
    elif st.session_state.workflow_mode == "Product Development":
        display_product_dev_workflow()

    with st.expander("AI Assistant (Context-Aware)"):
        if user_query := st.chat_input("Ask the AI about your current analysis..."):
            with st.spinner("AI is synthesizing an answer..."):
                response = st.session_state.ai_context_helper.generate_response(user_query)
                st.info(response)

def display_capa_workflow():
    """Display CAPA Management workflow tabs"""
    # Note: "CAPA Closure" removed as a separate tab, now integrated into CAPA Lifecycle Hub
    tab_list = ["Mission Control (Dashboard)", "CAPA Lifecycle Hub", "Root Cause Tools", "Risk & Safety", "Human Factors",
                "Vendor Comms", "Compliance", "Cost of Quality", "Final Review", "Data Exports"]

    tabs = st.tabs(tab_list)

    with tabs[0]:
        display_dashboard = lazy_import('tabs.dashboard', 'display_dashboard')
        display_dashboard()
    with tabs[1]:
        display_capa_tab = lazy_import('tabs.capa', 'display_capa_tab')
        display_capa_tab()
    with tabs[2]:
        display_rca_tab = lazy_import('tabs.rca', 'display_rca_tab')
        display_rca_tab()
    with tabs[3]:
        display_risk_safety_tab = lazy_import('tabs.risk_safety', 'display_risk_safety_tab')
        display_risk_safety_tab()
    with tabs[4]:
        display_human_factors_tab = lazy_import('tabs.human_factors', 'display_human_factors_tab')
        display_human_factors_tab()
    with tabs[5]:
        display_vendor_comm_tab = lazy_import('tabs.vendor_comms', 'display_vendor_comm_tab')
        display_vendor_comm_tab()
    with tabs[6]:
        display_compliance_tab = lazy_import('tabs.compliance', 'display_compliance_tab')
        display_compliance_tab()
    with tabs[7]:
        display_cost_of_quality_tab = lazy_import('tabs.cost_of_quality', 'display_cost_of_quality_tab')
        display_cost_of_quality_tab()
    with tabs[8]:
        display_final_review_tab = lazy_import('tabs.final_review', 'display_final_review_tab')
        display_final_review_tab()
    with tabs[9]:
        display_exports_tab = lazy_import('tabs.exports', 'display_exports_tab')
        display_exports_tab()

def display_product_dev_workflow():
    """Display Product Development workflow tabs"""
    tab_list = ["Project Charter", "Product Development", "Risk & Safety", "RCA", "Human Factors", "Manual Writer", "Compliance", "Final Review", "Exports"]

    tabs = st.tabs(tab_list)

    with tabs[0]:
        display_project_charter_tab = lazy_import('tabs.project_charter', 'display_project_charter_tab')
        display_project_charter_tab()
    with tabs[1]:
        display_product_development_tab = lazy_import('tabs.product_development', 'display_product_development_tab')
        display_product_development_tab()
    with tabs[2]:
        display_risk_safety_tab = lazy_import('tabs.risk_safety', 'display_risk_safety_tab')
        display_risk_safety_tab()
    with tabs[3]:
        display_rca_tab = lazy_import('tabs.rca', 'display_rca_tab')
        display_rca_tab()
    with tabs[4]:
        display_human_factors_tab = lazy_import('tabs.human_factors', 'display_human_factors_tab')
        display_human_factors_tab()
    with tabs[5]:
        display_manual_writer_tab = lazy_import('tabs.manual_writer', 'display_manual_writer_tab')
        display_manual_writer_tab()
    with tabs[6]:
        display_compliance_tab = lazy_import('tabs.compliance', 'display_compliance_tab')
        display_compliance_tab()
    with tabs[7]:
        display_final_review_tab = lazy_import('tabs.final_review', 'display_final_review_tab')
        display_final_review_tab()
    with tabs[8]:
        display_exports_tab = lazy_import('tabs.exports', 'display_exports_tab')
        display_exports_tab()

def main():
    """Main function to configure and run the Streamlit application."""
    st.set_page_config(
        page_title="ORION QMS",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    load_css()
    initialize_session_state()

    try:
        with open("config.yaml", "r") as f:
            st.session_state.config = yaml.safe_load(f)
    except FileNotFoundError:
        st.error("Configuration file (config.yaml) not found.")
        st.stop()

    if not check_password():
        st.stop()

    initialize_components()
    display_main_app()

if __name__ == "__main__":
    main()
