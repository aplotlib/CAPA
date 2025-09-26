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


# --- Page Configuration ---
st.set_page_config(page_title="AQMS", page_icon="https://www.vivehealth.com/cdn/shop/files/vive-logo-1_2_250x.png?v=1613713028", layout="wide")

# --- Enhanced CSS for a cleaner UI ---
def load_css():
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
        .stApp { background-color: #F9F9FB; }
        .css-1d391kg { background-color: #FFFFFF; border-right: 1px solid #E0E0E0; }
        .stTabs [data-baseweb="tab-list"] { gap: 12px; }
        .stTabs [data-baseweb="tab"] {
            height: 48px; background-color: #FFFFFF; border: 1px solid #E0E0E0;
            border-radius: 8px; padding: 0px 20px; transition: all 0.2s ease-in-out;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1a1a2e; color: white; border: 1px solid #1a1a2e;
        }
        .stMetric {
            background-color: #FFFFFF; border-radius: 10px; padding: 2rem 1.5rem;
            border: 1px solid #E0E0E0; box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        }
        .st-expander {
            border: 1px solid #E0E0E0 !important; border-radius: 10px !important;
            box-shadow: none !important;
        }
        .stButton button { height: 40px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- Session State Management ---
def initialize_session_state():
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

# --- Component Initialization ---
def initialize_components():
    if st.session_state.get('components_initialized'): return
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
    st.session_state.components_initialized = True

def check_password():
    if st.session_state.get("logged_in", False): return True
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
    if not input_str.strip(): return pd.DataFrame()
    if input_str.strip().isnumeric():
        return pd.DataFrame([{'sku': target_sku, 'quantity': int(input_str)}])
    try:
        if 'sku' not in input_str.lower() or 'quantity' not in input_str.lower():
            input_str = f"sku,quantity\n{target_sku},{input_str}"
        return pd.read_csv(StringIO(input_str))
    except Exception:
        st.error("Could not parse manual data.")
        return pd.DataFrame()

def display_header():
    st.markdown('<div class="main-header"><h1>Automated Quality Management System (AQMS)</h1><p>Your AI-powered hub for proactive quality assurance, compliance, and vendor management.</p></div>', unsafe_allow_html=True)

def display_sidebar():
    with st.sidebar:
        st.image("https://www.vivehealth.com/cdn/shop/files/vive-logo-1_2_250x.png?v=1613713028", width=150)
        st.header("Configuration")
        st.session_state.target_sku = st.text_input("Target Product SKU", st.session_state.target_sku)
        
        selected_range = st.selectbox("Select Date Range", ["Last 30 Days", "Last 7 Days", "Last 90 Days", "Year to Date", "Custom Range"])
        today = date.today()
        if selected_range == "Custom Range":
            st.session_state.start_date, st.session_state.end_date = st.date_input("Select a date range", (today - timedelta(days=30), today))
        else:
            if selected_range == "Last 7 Days": st.session_state.start_date = today - timedelta(days=7)
            elif selected_range == "Last 30 Days": st.session_state.start_date = today - timedelta(days=30)
            elif selected_range == "Last 90 Days": st.session_state.start_date = today - timedelta(days=90)
            elif selected_range == "Year to Date": st.session_state.start_date = date(today.year, 1, 1)
            st.session_state.end_date = today

        st.info(f"Period: {st.session_state.start_date.strftime('%b %d, %Y')} to {st.session_state.end_date.strftime('%b %d, %Y')}")
        
        st.header("Add Data")
        st.subheader("Manual Data Entry")
        manual_sales = st.text_area("Sales Data", placeholder=f"Total units sold for {st.session_state.target_sku} (e.g., 9502)")
        manual_returns = st.text_area("Returns Data", placeholder=f"Total units returned for {st.session_state.target_sku} (e.g., 150)")
        if st.button("Process Manual Data", type="primary", width='stretch'):
            if not manual_sales:
                st.warning("Sales data is required.")
            else:
                process_data(parse_manual_input(manual_sales, st.session_state.target_sku), parse_manual_input(manual_returns, st.session_state.target_sku))

        with st.expander("Or Upload Files"):
            uploaded_files = st.file_uploader("Upload data", accept_multiple_files=True, type=['csv', 'xlsx', 'txt', 'tsv', 'png', 'jpg'])
            if st.button("Process Uploaded Files", width='stretch'):
                if uploaded_files:
                    process_uploaded_files(uploaded_files)
                else:
                    st.warning("Please upload files to process.")

def process_data(sales_df, returns_df):
    with st.spinner("Processing data..."):
        st.session_state.sales_data = st.session_state.data_processor.process_sales_data(sales_df)
        st.session_state.returns_data = st.session_state.data_processor.process_returns_data(returns_df)
        days = (st.session_state.end_date - st.session_state.start_date).days
        st.session_state.analysis_results = run_full_analysis(
            st.session_state.sales_data, st.session_state.returns_data,
            days, st.session_state.unit_cost, st.session_state.sales_price)
    st.success("Analysis complete!")

def process_uploaded_files(uploaded_files):
    parser = st.session_state.file_parser
    sales_dfs, returns_dfs = [], []
    with st.spinner("AI is analyzing files..."):
        for file in uploaded_files:
            analysis = parser.analyze_file_structure(file, st.session_state.target_sku)
            st.write(f"File: `{file.name}` → AI identified as: `{analysis.get('content_type', 'unknown')}`")
            df = parser.extract_data(file, analysis, st.session_state.target_sku)
            if df is not None:
                if analysis.get('content_type') == 'sales': sales_dfs.append(df)
                elif analysis.get('content_type') == 'returns': returns_dfs.append(df)
    
    if sales_dfs or returns_dfs:
        process_data(pd.concat(sales_dfs) if sales_dfs else pd.DataFrame(), pd.concat(returns_dfs) if returns_dfs else pd.DataFrame())
    else:
        st.warning("AI could not identify sales or returns data in the files.")

def display_main_app():
    display_header()
    display_sidebar()

    tabs = st.tabs(["Dashboard", "CAPA", "Risk & Safety", "Human Factors", "Vendor Comms", "Compliance", "Cost of Quality", "Exports"])
    with tabs[0]: display_dashboard()
    with tabs[1]: display_capa_tab()
    with tabs[2]: display_risk_safety_tab()
    with tabs[3]: display_human_factors_tab()
    with tabs[4]: display_vendor_comm_tab()
    with tabs[5]: display_compliance_tab()
    with tabs[6]: display_cost_of_quality_tab()
    with tabs[7]: display_exports_tab()
    
    st.divider()
    if not st.session_state.api_key_missing:
        with st.expander("AI Assistant (Context-Aware)"):
            user_query = st.text_input("What would you like to know?")
            if user_query:
                with st.spinner("AI is synthesizing an answer..."):
                    st.markdown(st.session_state.ai_context_helper.generate_response(user_query))

def display_workflow_selection():
    st.header("Select Your Goal")
    st.write("Choose your primary objective to get started.")
    
    options = ["Analyze Product Quality & Start a CAPA", "Perform a Risk Analysis (FMEA)", "Conduct a Pre-Mortem for a New Product", "Analyze Customer Feedback Files", "Free Use Mode"]
    selection = st.radio("What would you like to accomplish?", options)
    
    if st.button("Begin Workflow", type="primary", width='stretch'):
        st.session_state.workflow_mode = selection
        st.rerun()

def main():
    initialize_session_state()
    if not check_password(): st.stop()
    load_css()
    initialize_components()
    if not st.session_state.workflow_mode:
        display_workflow_selection()
    else:
        display_main_app()

if __name__ == "__main__":
    main()
