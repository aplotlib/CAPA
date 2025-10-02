# main.py

import sys
import os
import streamlit as st
from datetime import date, timedelta
import base64

# Get the absolute path of a directory containing main.py
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# Lazy import function to load modules only when needed
def lazy_import(module_name, class_name=None):
    """Lazy import modules to reduce initial load time"""
    if module_name not in st.session_state.get('loaded_modules', {}):
        if 'loaded_modules' not in st.session_state:
            st.session_state.loaded_modules = {}
        
        module = __import__(module_name, fromlist=[class_name] if class_name else [])
        st.session_state.loaded_modules[module_name] = module
        
        if class_name:
            return getattr(module, class_name)
        return module
    else:
        module = st.session_state.loaded_modules[module_name]
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
        .stTabs [data-baseweb="tab"]:hover {
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
        
        /* --- Performance Indicator --- */
        .loading-indicator {
            position: fixed;
            top: 10px;
            right: 10px;
            background: var(--primary-color);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            z-index: 9999;
            display: none;
        }
        .loading-indicator.active {
            display: block;
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
    Initializes helper classes with intelligent lazy loading based on workflow.
    Only loads what's immediately needed.
    """
    if st.session_state.get('components_initialized'):
        return

    api_key = get_api_key()
    st.session_state.api_key_missing = not bool(api_key)

    # Always initialize non-AI components (lightweight)
    DocumentGenerator = lazy_import('src.document_generator', 'DocumentGenerator')
    DataProcessor = lazy_import('src.data_processing', 'DataProcessor')
    
    st.session_state.doc_generator = DocumentGenerator()
    st.session_state.data_processor = DataProcessor()

    # Initialize AI components only if API key is present
    if not st.session_state.api_key_missing:
        st.session_state.openai_api_key = api_key
        
        # Load AI components based on active workflow
        workflow = st.session_state.get('workflow_mode', 'Product Development')
        
        # Core AI components (always needed)
        AICAPAHelper = lazy_import('src.ai_capa_helper', 'AICAPAHelper')
        AIContextHelper = lazy_import('src.ai_context_helper', 'AIContextHelper')
        
        st.session_state.ai_capa_helper = AICAPAHelper(api_key)
        st.session_state.ai_context_helper = AIContextHelper(api_key)
        
        # Workflow-specific lazy initialization
        if workflow == 'CAPA Management':
            initialize_capa_components(api_key)
        elif workflow == 'Product Development':
            initialize_product_dev_components(api_key)
            
    st.session_state.components_initialized = True

def initialize_capa_components(api_key):
    """Initialize components specific to CAPA workflow"""
    AIEmailDrafter = lazy_import('src.ai_capa_helper', 'AIEmailDrafter')
    AIFileParser = lazy_import('src.parsers', 'AIFileParser')
    
    st.session_state.ai_email_drafter = AIEmailDrafter(api_key)
    st.session_state.file_parser = AIFileParser(api_key)

def initialize_product_dev_components(api_key):
    """Initialize components specific to Product Development workflow"""
    MedicalDeviceClassifier = lazy_import('src.ai_capa_helper', 'MedicalDeviceClassifier')
    RiskAssessmentGenerator = lazy_import('src.ai_capa_helper', 'RiskAssessmentGenerator')
    UseRelatedRiskAnalyzer = lazy_import('src.ai_capa_helper', 'UseRelatedRiskAnalyzer')
    AIDesignControlsTriager = lazy_import('src.ai_capa_helper', 'AIDesignControlsTriager')
    AIHumanFactorsHelper = lazy_import('src.ai_capa_helper', 'AIHumanFactorsHelper')
    ProductManualWriter = lazy_import('src.ai_capa_helper', 'ProductManualWriter') # NEW
    FMEA = lazy_import('src.fmea', 'FMEA')
    PreMortem = lazy_import('src.pre_mortem', 'PreMortem')
    
    st.session_state.medical_device_classifier = MedicalDeviceClassifier(api_key)
    st.session_state.risk_assessment_generator = RiskAssessmentGenerator(api_key)
    st.session_state.urra_generator = UseRelatedRiskAnalyzer(api_key)
    st.session_state.ai_design_controls_triager = AIDesignControlsTriager(api_key)
    st.session_state.ai_hf_helper = AIHumanFactorsHelper(api_key)
    st.session_state.manual_writer = ProductManualWriter(api_key) # NEW
    st.session_state.fmea_generator = FMEA(api_key)
    st.session_state.pre_mortem_generator = PreMortem(api_key)

def ensure_component_loaded(component_name):
    """Ensure a specific component is loaded when needed"""
    if component_name not in st.session_state:
        api_key = st.session_state.get('openai_api_key')
        if api_key and not st.session_state.api_key_missing:
            if component_name == 'ai_email_drafter':
                AIEmailDrafter = lazy_import('src.ai_capa_helper', 'AIEmailDrafter')
                st.session_state.ai_email_drafter = AIEmailDrafter(api_key)
            elif component_name == 'file_parser':
                AIFileParser = lazy_import('src.parsers', 'AIFileParser')
                st.session_state.file_parser = AIFileParser(api_key)
            elif component_name == 'fmea_generator':
                FMEA = lazy_import('src.fmea', 'FMEA')
                st.session_state.fmea_generator = FMEA(api_key)
            elif component_name == 'pre_mortem_generator':
                PreMortem = lazy_import('src.pre_mortem', 'PreMortem')
                st.session_state.pre_mortem_generator = PreMortem(api_key)
            # Add other components as needed

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
        
        # Workflow mode selector with change detection
        prev_workflow = st.session_state.get('workflow_mode')
        st.session_state.workflow_mode = st.selectbox(
            "Workflow Mode",
            ["Product Development", "CAPA Management"]
        )
        
        # Reinitialize components if workflow changed
        if prev_workflow != st.session_state.workflow_mode and prev_workflow is not None:
            st.session_state.active_workflow = st.session_state.workflow_mode
            if not st.session_state.api_key_missing:
                api_key = st.session_state.openai_api_key
                if st.session_state.workflow_mode == 'CAPA Management':
                    initialize_capa_components(api_key)
                else:
                    initialize_product_dev_components(api_key)
        
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

def process_data(sales_df: pd.DataFrame, returns_df: pd.DataFrame):
    """Processes sales and returns DataFrames to run and store the main analysis."""
    with st.spinner("Processing data and running analysis..."):
        data_processor = st.session_state.data_processor
        st.session_state.sales_data = data_processor.process_sales_data(sales_df)
        st.session_state.returns_data = data_processor.process_returns_data(returns_df)
        report_days = (st.session_state.end_date - st.session_state.start_date).days
        
        # Lazy load analysis module
        run_full_analysis = lazy_import('src.analysis', 'run_full_analysis')
        
        st.session_state.analysis_results = run_full_analysis(
            sales_df=st.session_state.sales_data, 
            returns_df=st.session_state.returns_data,
            report_period_days=report_days, 
            unit_cost=st.session_state.unit_cost,
            sales_price=st.session_state.sales_price
        )
    st.toast("✅ Analysis complete!", icon="🎉")

def process_uploaded_files(uploaded_files: list):
    """Analyzes and processes a list of uploaded files using the AI parser."""
    if st.session_state.api_key_missing:
        st.error("Cannot process files without an OpenAI API key.")
        return
    
    # Ensure file parser is loaded
    ensure_component_loaded('file_parser')
    
    parser = st.session_state.file_parser
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
                    response = st.session_state.ai_context_helper.generate_response(user_query)
                    st.info(response)

def display_capa_workflow():
    """Display CAPA Management workflow tabs"""
    # Lazy load tab modules
    tab_list = ["Dashboard", "CAPA", "CAPA Closure", "Risk & Safety", "Human Factors", 
                "Vendor Comms", "Compliance", "Cost of Quality", "Final Review", "Exports"]
    icons = ["📈", "📝", "✅", "⚠️", "👥", "📬", "⚖️", "💲", "🔍", "📄"]
    
    tabs = st.tabs([f"{icon} {name}" for icon, name in zip(icons, tab_list)])
    
    # Load tab modules on demand
    with tabs[0]: 
        display_dashboard = lazy_import('src.tabs.dashboard', 'display_dashboard')
        display_dashboard()
    with tabs[1]: 
        display_capa_tab = lazy_import('src.tabs.capa', 'display_capa_tab')
        display_capa_tab()
    with tabs[2]: 
        display_capa_closure_tab = lazy_import('src.tabs.capa_closure', 'display_capa_closure_tab')
        display_capa_closure_tab()
    with tabs[3]: 
        ensure_component_loaded('fmea_generator')
        display_risk_safety_tab = lazy_import('src.tabs.risk_safety', 'display_risk_safety_tab')
        display_risk_safety_tab()
    with tabs[4]: 
        display_human_factors_tab = lazy_import('src.tabs.human_factors', 'display_human_factors_tab')
        display_human_factors_tab()
    with tabs[5]: 
        ensure_component_loaded('ai_email_drafter')
        display_vendor_comm_tab = lazy_import('src.tabs.vendor_comms', 'display_vendor_comm_tab')
        display_vendor_comm_tab()
    with tabs[6]: 
        ensure_component_loaded('pre_mortem_generator')
        display_compliance_tab = lazy_import('src.tabs.compliance', 'display_compliance_tab')
        display_compliance_tab()
    with tabs[7]: 
        display_cost_of_quality_tab = lazy_import('src.tabs.cost_of_quality', 'display_cost_of_quality_tab')
        display_cost_of_quality_tab()
    with tabs[8]: 
        display_final_review_tab = lazy_import('src.tabs.final_review', 'display_final_review_tab')
        display_final_review_tab()
    with tabs[9]: 
        display_exports_tab = lazy_import('src.tabs.exports', 'display_exports_tab')
        display_exports_tab()

def display_product_dev_workflow():
    """Display Product Development workflow tabs"""
    tab_list = ["Product Development", "Risk & Safety", "Human Factors", "Manual Writer", "Compliance", "Final Review", "Exports"]
    icons = ["🚀", "⚠️", "👥", "✍️", "⚖️", "🔍", "📄"]
    
    tabs = st.tabs([f"{icon} {name}" for icon, name in zip(icons, tab_list)])
    
    with tabs[0]: 
        display_product_development_tab = lazy_import('src.tabs.product_development', 'display_product_development_tab')
        display_product_development_tab()
    with tabs[1]: 
        ensure_component_loaded('fmea_generator')
        display_risk_safety_tab = lazy_import('src.tabs.risk_safety', 'display_risk_safety_tab')
        display_risk_safety_tab()
    with tabs[2]: 
        display_human_factors_tab = lazy_import('src.tabs.human_factors', 'display_human_factors_tab')
        display_human_factors_tab()
    with tabs[3]: # NEW
        display_manual_writer_tab = lazy_import('src.tabs.manual_writer', 'display_manual_writer_tab')
        display_manual_writer_tab()
    with tabs[4]: 
        ensure_component_loaded('pre_mortem_generator')
        display_compliance_tab = lazy_import('src.tabs.compliance', 'display_compliance_tab')
        display_compliance_tab()
    with tabs[5]: 
        display_final_review_tab = lazy_import('src.tabs.final_review', 'display_final_review_tab')
        display_final_review_tab()
    with tabs[6]: 
        display_exports_tab = lazy_import('src.tabs.exports', 'display_exports_tab')
        display_exports_tab()

def main():
    """Main function to configure and run the Streamlit application."""
    # Page config with optimizations
    page_icon_path = os.path.join(APP_DIR, "logo.png")
    st.set_page_config(
        page_title="AQMS", 
        layout="wide", 
        page_icon=page_icon_path if os.path.exists(page_icon_path) else "✅",
        initial_sidebar_state="expanded"
    )
    
    load_css()
    initialize_session_state()

    if not check_password():
        st.stop()

    initialize_components()
    display_main_app()

if __name__ == "__main__":
    main()
