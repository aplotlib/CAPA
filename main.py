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
    """Loads a custom CSS stylesheet to improve the application's appearance."""
    st.markdown("""
    <style>
        /* --- Greenlight Guru Inspired Theme --- */
        :root {
            --primary-color: #2E7D32;
            --primary-color-light: #E8F5E9;
            --primary-bg: #FFFFFF;
            --secondary-bg: #F5F7F8;
            --text-color: #263238;
            --secondary-text-color: #546E7A;
            --border-color: #CFD8DC;
            --font-family: 'Inter', sans-serif;
        }
        .breadcrumb {
            font-size: 0.9rem;
            color: var(--secondary-text-color);
            margin-bottom: 1rem;
        }

        /* --- Base Styles --- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        html, body, [class*="st-"], [class*="css-"] {
            font-family: var(--font-family);
            color: var(--text-color);
        }

        .main {
            background-color: var(--secondary-bg);
        }
        
        h1, h2, h3 {
            font-weight: 700;
            color: var(--text-color);
        }

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {
            background-color: var(--primary-bg);
            border-right: 1px solid var(--border-color);
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
             color: var(--primary-color);
        }

        /* --- Header in Main App --- */
        .main-header {
            background-color: transparent;
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
            border-bottom: 2px solid var(--border-color);
        }
        .main-header h1 {
            color: var(--text-color);
            font-size: 2.25rem;
            margin-bottom: 0.25rem;
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
            border: 2px solid var(--primary-color);
            background-color: transparent;
            color: var(--primary-color);
            transition: all 0.2s ease-in-out;
        }
        [data-testid="stButton"] button:hover {
            border-color: #1B5E20;
            background-color: var(--primary-color-light);
            color: #1B5E20;
        }
        
        /* Primary Button Style */
        [data-testid="stButton"] button[kind="primary"] {
             background-color: var(--primary-color) !important;
             color: white !important;
             border: 2px solid var(--primary-color) !important;
        }
        [data-testid="stButton"] button[kind="primary"]:hover {
             background-color: #1B5E20 !important;
             border-color: #1B5E20 !important;
             color: white !important;
        }

        /* --- Containers & Expanders --- */
        [data-testid="stContainer"], [data-testid="stExpander"] {
            border: 1px solid var(--border-color);
            border-radius: 10px;
            background-color: var(--primary-bg);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        [data-testid="stExpander"] summary {
            font-weight: 600;
            color: var(--text-color);
            font-size: 1.1rem;
        }
        
        /* --- Tabs --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 2px solid var(--border-color);
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            padding: 0.75rem 0.5rem;
            font-weight: 600;
            color: var(--secondary-text-color);
            transition: all 0.2s ease-in-out;
        }
        .stTabs [data-baswebeb="tab"]:hover {
            background-color: var(--primary-color-light);
            border-bottom: 3px solid #AED581;
        }
        .stTabs [aria-selected="true"] {
            color: var(--primary-color);
            border-bottom: 3px solid var(--primary-color) !important;
        }
        
        /* --- Metrics --- */
        [data-testid="stMetric"] {
            background-color: var(--primary-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
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
    """Initializes all required keys in Streamlit's session state with default values."""
    defaults = {
        'openai_api_key': None, 
        'api_key_missing': True, 
        'components_initialized': False,
        'loaded_modules': {},  # Track loaded modules for lazy loading
        'active_workflow': None,  # Track which workflow is active
        'product_info': {
            'sku': 'SKU-12345',
            'name': 'Example Product',
            'ifu': 'This is an example Intended for Use statement.'
        },
        'unit_cost': 15.50, 
        'sales_price': 49.99,
        'start_date': date.today() - timedelta(days=30), 
        'end_date': date.today(),
        'sales_data': pd.DataFrame(), 
        'returns_data': pd.DataFrame(),
        'analysis_results': None, 
        'capa_data': {}, 
        'fmea_data': pd.DataFrame(),
        'vendor_email_draft': None, 
        'risk_assessment': None, 
        'urra': None,
        'pre_mortem_summary': None, 
        'medical_device_classification': None,
        'human_factors_data': {}, 
        'logged_in': False, 
        'workflow_mode': 'Product Development',
        'product_dev_data': {}, 
        'final_review_summary': None,
        'capa_closure_data': {},
        'coq_results': None,
        'fmea_rows': [],
        'manual_content': {}
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
    Initializes all application components. AI helpers are initialized
    at once if the API key is available.
    """
    if st.session_state.get('components_initialized'):
        return

    api_key = get_api_key()
    st.session_state.api_key_missing = not bool(api_key)

    # Always initialize non-AI components (lightweight)
    DataProcessor = lazy_import('data_processing', 'DataProcessor')
    DocumentGenerator = lazy_import('document_generator', 'DocumentGenerator')
    st.session_state.data_processor = DataProcessor()
    st.session_state.doc_generator = DocumentGenerator() # Ensure doc generator is globally available

    # Initialize all AI components at once if API key is present
    if not st.session_state.api_key_missing:
        st.session_state.openai_api_key = api_key
        AIHelperFactory.initialize_ai_helpers(api_key)
            
    st.session_state.components_initialized = True

def check_password():
    """Displays a password input and returns True if the password is correct."""
    if st.session_state.get("logged_in", False):
        return True

    logo_base64 = get_local_image_as_base64("logo.png")
    
    st.set_page_config(
        page_title="AQMS Login", 
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    with st.container():
        if logo_base64:
            st.markdown(f'<div style="text-align: center; margin-bottom: 2rem;"><img src="data:image/png;base64,{logo_base64}" width="150"></div>', unsafe_allow_html=True)
        st.title("Automated Quality Management System")
        st.header("Login")
        
        with st.form("login_form"):
            password_input = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

            if submitted:
                if password_input == st.secrets.get("APP_PASSWORD", "admin"):
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("The password you entered is incorrect.")
    return False

def display_sidebar():
    """Renders all configuration and data input widgets in the sidebar."""
    from src.utils import parse_manual_input
    with st.sidebar:
        logo_base64 = get_local_image_as_base64("logo.png")
        if logo_base64:
            st.image(f"data:image/png;base64,{logo_base64}", width=100)
        
        st.header("Configuration")
        
        # Workflow mode selector with change detection
        st.session_state.workflow_mode = st.selectbox(
            "Workflow Mode",
            ["Product Development", "CAPA Management"]
        )
        
        with st.expander("📝 Product Information", expanded=True):
            product_info = st.session_state.product_info
            product_info['sku'] = st.text_input("Target Product SKU", product_info.get('sku', ''), key="sidebar_sku")
            product_info['name'] = st.text_input("Product Name", product_info.get('name', ''), key="sidebar_name")
            product_info['ifu'] = st.text_area("Intended for Use (IFU)", product_info.get('ifu', ''), height=100, key="sidebar_ifu")

        with st.expander("💰 Financials (Optional)"):
            st.session_state.unit_cost = st.number_input("Unit Cost ($)", value=st.session_state.get('unit_cost', 0.0), step=1.0, format="%.2f")
            st.session_state.sales_price = st.number_input("Sales Price ($)", value=st.session_state.get('sales_price', 0.0), step=1.0, format="%.2f")

        # Only show post-market data input for CAPA Management workflow
        if st.session_state.workflow_mode == "CAPA Management":
            st.header("Post-Market Data Input")
            st.caption("For CAPA Management & Kaizen")

            with st.expander("🗓️ Reporting Period"):
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
        
        st.session_state.analysis_results = run_cached_analysis(
            st.session_state.sales_data, 
            st.session_state.returns_data,
            report_days, 
            st.session_state.unit_cost,
            st.session_state.sales_price
        )
    st.toast("✅ Analysis complete!", icon="🎉")

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

def create_breadcrumb_navigation(current_tab):
    """Shows current location and allow quick navigation"""
    st.markdown(f"""
        <div class="breadcrumb">
            Home > {st.session_state.workflow_mode} > {current_tab}
        </div>
    """, unsafe_allow_html=True)

def add_guided_workflow(step, total_steps, description):
    """Step-by-step wizard for complex processes"""
    st.progress(step / total_steps)
    st.caption(f"Step {step} of {total_steps}: {description}")

def display_main_app():
    """Displays the main application interface, including header, sidebar, and tabs."""
    st.markdown(
        '<div class="main-header"><h1>Automated Quality Management System</h1>'
        f'<p>Your AI-powered hub for proactive quality assurance. Current Mode: <strong>{st.session_state.workflow_mode}</strong></p></div>',
        unsafe_allow_html=True
    )
    
    display_sidebar()

    # Dynamic tab loading based on workflow
    if st.session_state.workflow_mode == "CAPA Management":
        display_capa_workflow()
    elif st.session_state.workflow_mode == "Product Development":
        display_product_dev_workflow()

    # AI Assistant (always available if API key exists)
    if not st.session_state.api_key_missing:
        with st.expander("💬 AI Assistant (Context-Aware)"):
            if user_query := st.chat_input("Ask the AI about your current analysis..."):
                with st.spinner("AI is synthesizing an answer..."):
                    # FIX: AI Context Helper is now reliably initialized by the factory
                    response = st.session_state.ai_context_helper.generate_response(user_query)
                    st.info(response)

def display_capa_workflow():
    """Display CAPA Management workflow tabs"""
    # Lazy load tab modules
    tab_list = ["Dashboard", "CAPA", "RCA", "CAPA Closure", "Risk & Safety", "Human Factors", 
                "Vendor Comms", "Compliance", "Cost of Quality", "Final Review", "Exports"]
    icons = ["📈", "📝", "🔬", "✅", "⚠️", "👥", "📬", "⚖️", "💲", "🔍", "📄"]
    
    tabs = st.tabs([f"{icon} {name}" for icon, name in zip(icons, tab_list)])
    
    # Load tab modules on demand
    with tabs[0]: 
        create_breadcrumb_navigation("Dashboard")
        add_guided_workflow(1, 6, "Review initial performance metrics and AI insights.")
        display_dashboard = lazy_import('tabs.dashboard', 'display_dashboard')
        display_dashboard()
    with tabs[1]: 
        create_breadcrumb_navigation("CAPA")
        add_guided_workflow(2, 6, "Define the problem and initiate the CAPA form.")
        display_capa_tab = lazy_import('tabs.capa', 'display_capa_tab')
        display_capa_tab()
    with tabs[2]:
        create_breadcrumb_navigation("RCA")
        add_guided_workflow(3, 6, "Use guided tools to find the root cause.")
        display_rca_tab = lazy_import('tabs.rca', 'display_rca_tab')
        display_rca_tab()
    with tabs[3]: 
        create_breadcrumb_navigation("CAPA Closure")
        add_guided_workflow(4, 6, "Verify the effectiveness of actions and close the CAPA.")
        display_capa_closure_tab = lazy_import('tabs.capa_closure', 'display_capa_closure_tab')
        display_capa_closure_tab()
    with tabs[4]: 
        create_breadcrumb_navigation("Risk & Safety")
        add_guided_workflow(5, 6, "Conduct FMEA and other risk assessments.")
        display_risk_safety_tab = lazy_import('tabs.risk_safety', 'display_risk_safety_tab')
        display_risk_safety_tab()
    with tabs[5]: 
        create_breadcrumb_navigation("Human Factors")
        display_human_factors_tab = lazy_import('tabs.human_factors', 'display_human_factors_tab')
        display_human_factors_tab()
    with tabs[6]: 
        create_breadcrumb_navigation("Vendor Comms")
        display_vendor_comm_tab = lazy_import('tabs.vendor_comms', 'display_vendor_comm_tab')
        display_vendor_comm_tab()
    with tabs[7]: 
        create_breadcrumb_navigation("Compliance")
        display_compliance_tab = lazy_import('tabs.compliance', 'display_compliance_tab')
        display_compliance_tab()
    with tabs[8]: 
        create_breadcrumb_navigation("Cost of Quality")
        display_cost_of_quality_tab = lazy_import('tabs.cost_of_quality', 'display_cost_of_quality_tab')
        display_cost_of_quality_tab()
    with tabs[9]: 
        create_breadcrumb_navigation("Final Review")
        add_guided_workflow(6, 6, "Generate a final summary and export all documentation.")
        display_final_review_tab = lazy_import('tabs.final_review', 'display_final_review_tab')
        display_final_review_tab()
    with tabs[10]: 
        create_breadcrumb_navigation("Exports")
        display_exports_tab = lazy_import('tabs.exports', 'display_exports_tab')
        display_exports_tab()

def display_product_dev_workflow():
    """Display Product Development workflow tabs"""
    tab_list = ["Product Development", "Risk & Safety", "RCA", "Human Factors", "Manual Writer", "Compliance", "Final Review", "Exports"]
    icons = ["🚀", "⚠️", "🔬", "👥", "✍️", "⚖️", "🔍", "📄"]
    
    tabs = st.tabs([f"{icon} {name}" for icon, name in zip(icons, tab_list)])
    
    with tabs[0]: 
        create_breadcrumb_navigation("Product Development")
        display_product_development_tab = lazy_import('tabs.product_development', 'display_product_development_tab')
        display_product_development_tab()
    with tabs[1]: 
        create_breadcrumb_navigation("Risk & Safety")
        display_risk_safety_tab = lazy_import('tabs.risk_safety', 'display_risk_safety_tab')
        display_risk_safety_tab()
    with tabs[2]:
        create_breadcrumb_navigation("RCA")
        display_rca_tab = lazy_import('tabs.rca', 'display_rca_tab')
        display_rca_tab()
    with tabs[3]: 
        create_breadcrumb_navigation("Human Factors")
        display_human_factors_tab = lazy_import('tabs.human_factors', 'display_human_factors_tab')
        display_human_factors_tab()
    with tabs[4]: 
        create_breadcrumb_navigation("Manual Writer")
        display_manual_writer_tab = lazy_import('tabs.manual_writer', 'display_manual_writer_tab')
        display_manual_writer_tab()
    with tabs[5]: 
        create_breadcrumb_navigation("Compliance")
        display_compliance_tab = lazy_import('tabs.compliance', 'display_compliance_tab')
        display_compliance_tab()
    with tabs[6]: 
        create_breadcrumb_navigation("Final Review")
        display_final_review_tab = lazy_import('tabs.final_review', 'display_final_review_tab')
        display_final_review_tab()
    with tabs[7]: 
        create_breadcrumb_navigation("Exports")
        display_exports_tab = lazy_import('tabs.exports', 'display_exports_tab')
        display_exports_tab()

def main():
    """Main function to configure and run the Streamlit application."""
    st.set_page_config(
        page_title="AQMS", 
        layout="wide", 
        initial_sidebar_state="expanded"
    )
    
    load_css()
    initialize_session_state()

    # Load config from YAML
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
