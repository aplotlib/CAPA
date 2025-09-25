# main.py

import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import os
from io import StringIO
import json
import copy

# --- Import custom modules ---
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
st.set_page_config(
    page_title="Product Lifecycle & Quality Manager",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Enhanced UI/UX Styling ---
def load_css():
    """
    Loads custom CSS. This version is simplified to prevent conflicts with Streamlit's base styles,
    fixing the overlapping text and layout issues.
    """
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        html, body, [class*="st-"], [class*="css-"] {
            font-family: 'Inter', sans-serif;
        }
        
        .main-header {
            text-align: center;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }

        .main-header h1 {
            font-weight: 700;
            font-size: 2.2rem;
            color: #1a1a2e;
            margin-bottom: 0.25rem;
        }

        .main-header p {
            color: #555;
            font-size: 1.1rem;
        }

        [data-testid="stMetric"] {
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 1rem;
            border: 1px solid #E0E0E0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E0E0E0;
        }
        
        /* Ensure tabs don't cause layout shifts */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 2px solid #E0E0E0;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border: none;
            padding: 10px 16px;
            font-weight: 600;
            color: #555;
        }
        .stTabs [aria-selected="true"] {
            color: #0068C9;
            border-bottom: 3px solid #0068C9;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Session State Management ---
def initialize_session_state():
    """Initializes all necessary variables in Streamlit's session state."""
    STATE_DEFAULTS = {
        'components_initialized': False, 'api_key_missing': True, 'openai_api_key': None,
        'target_sku': 'SKU-12345', 'unit_cost': 15.50, 'sales_price': 49.99,
        'start_date': date.today() - timedelta(days=30), 'end_date': date.today(),
        'uploaded_files_list': [], 'ai_file_analyses': [],
        'sales_data': pd.DataFrame(), 'returns_data': pd.DataFrame(),
        'analysis_results': None, 'capa_feasibility_analysis': None, 'capa_data': {},
        'fmea_data': None, 'pre_mortem_summary': None, 'medical_device_classification': None,
        'vendor_email_draft': None, 'risk_assessment': None, 'urra': None,
        'chat_history': {}, 'pre_mortem_data': []
    }
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- Component Initialization ---
def initialize_components():
    """Initializes all AI-powered components safely."""
    if st.session_state.get('components_initialized', False):
        return

    api_key = st.secrets.get("OPENAI_API_KEY")
    st.session_state.api_key_missing = not bool(api_key)
    
    if not st.session_state.api_key_missing:
        st.session_state.openai_api_key = api_key
        # Use a consistent client object across helpers
        st.session_state.ai_capa_helper = AICAPAHelper(api_key)
        st.session_state.ai_email_drafter = AIEmailDrafter(api_key)
        st.session_state.medical_device_classifier = MedicalDeviceClassifier(api_key)
        st.session_state.risk_assessment_generator = RiskAssessmentGenerator(api_key)
        st.session_state.urra_generator = UseRelatedRiskAnalyzer(api_key)
        st.session_state.fmea_generator = FMEA(api_key)
        st.session_state.pre_mortem_generator = PreMortem(api_key)
        # These don't need the key but are part of the core components
        st.session_state.file_parser = AIFileParser(api_key)
        st.session_state.data_processor = DataProcessor()
        st.session_state.ai_context_helper = AIContextHelper(api_key)
        st.session_state.doc_generator = CapaDocumentGenerator()
    
    st.session_state.components_initialized = True

# --- UI Sections ---
def display_header():
    """Displays the main application header."""
    st.markdown("""
        <div class="main-header">
            <h1>🛡️ Product Lifecycle & Quality Manager</h1>
            <p>Your AI-powered hub for proactive quality assurance, compliance, and vendor management.</p>
        </div>
    """, unsafe_allow_html=True)

def display_sidebar():
    """Displays the sidebar for configuration and data input."""
    with st.sidebar:
        st.image("https://www.vivehealth.com/cdn/shop/files/vive-logo-1_2_250x.png?v=1613713028", width=150)
        
        st.header("⚙️ Configuration")
        st.session_state.target_sku = st.text_input("🎯 Target Product SKU", st.session_state.target_sku)
        st.session_state.unit_cost = st.number_input("💰 Unit Cost ($)", 0.0, value=st.session_state.unit_cost, format="%.2f")
        st.session_state.sales_price = st.number_input("💵 Sales Price ($)", 0.0, value=st.session_state.sales_price, format="%.2f")
        
        with st.expander("🗓️ Reporting Period", expanded=True):
            st.session_state.start_date = st.date_input("Start Date", st.session_state.start_date)
            st.session_state.end_date = st.date_input("End Date", st.session_state.end_date)
        
        st.header("➕ Add Data")
        uploaded_files = st.file_uploader(
            "Upload Sales/Returns Files",
            accept_multiple_files=True,
            type=['csv', 'xlsx'],
            key="file_uploader_widget"
        )
        if uploaded_files:
            process_uploaded_files(uploaded_files)

def display_dashboard():
    """Displays the main dashboard with metrics and insights."""
    st.header("📊 Quality Dashboard")
    
    if not st.session_state.analysis_results:
        st.info('**Welcome!** Upload sales and returns data in the sidebar to begin your analysis.')
        return

    results = st.session_state.analysis_results
    if "error" in results:
        st.error(f"Analysis Failed: {results['error']}")
        return
    
    summary_df = results.get('return_summary')
    if summary_df is None or summary_df.empty:
        st.warning("No data found for the target SKU. Please check your uploaded files.")
        return
    
    sku_summary = summary_df[summary_df['sku'] == st.session_state.target_sku]
    if sku_summary.empty:
        st.warning(f"No summary data could be calculated for SKU: **{st.session_state.target_sku}**")
        return
    
    summary_data = sku_summary.iloc[0]
    
    with st.container(border=True):
        st.markdown(f"### Analysis for SKU: **{summary_data['sku']}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Return Rate", f"{summary_data['return_rate']:.2f}%")
        c2.metric("Total Returned", f"{int(summary_data['total_returned']):,}")
        c3.metric("Total Sold", f"{int(summary_data['total_sold']):,}")
        
        quality_score = results['quality_metrics'].get('quality_score', 'N/A')
        risk_level = results['quality_metrics'].get('risk_level', '')
        c4.metric("Quality Score", f"{quality_score}/100", delta=risk_level, delta_color="inverse")
        
        st.markdown(f"**🧠 AI Insights**: {results.get('insights', 'N/A')}")

    with st.container(border=True):
        st.subheader("💡 Cost-Benefit Analysis")
        with st.form("cost_benefit_form"):
            c1, c2 = st.columns(2)
            cost_change = c1.number_input("Cost increase per unit ($)", min_value=0.0, format="%.2f")
            expected_rr_reduction = c2.number_input("Expected return rate reduction (%)", min_value=0.0, max_value=100.0, format="%.1f")
            
            if st.form_submit_button("Calculate Financial Impact", type="primary", use_container_width=True):
                days = (st.session_state.end_date - st.session_state.start_date).days
                st.session_state.capa_feasibility_analysis = calculate_cost_benefit(
                    results, st.session_state.unit_cost, cost_change, expected_rr_reduction,
                    days, st.session_state.target_sku
                )

        if st.session_state.capa_feasibility_analysis:
            res = st.session_state.capa_feasibility_analysis
            st.success(f"**Summary:** {res['summary']}")
            with st.expander("Show Calculation Details"):
                st.table(pd.DataFrame.from_dict(res['details'], orient='index', columns=["Value"]))

# --- Process Functions ---
def process_uploaded_files(uploaded_files):
    """Processes uploaded files to extract sales and returns data."""
    with st.spinner("Processing and analyzing files..."):
        sales_dfs, returns_dfs = [], []
        # Use AI file parser to identify file types
        parser = st.session_state.file_parser
        processor = st.session_state.data_processor
        
        for file in uploaded_files:
            analysis = parser.analyze_file_structure(file, st.session_state.target_sku)
            df = parser.extract_data(file, analysis, st.session_state.target_sku)
            if df is not None:
                if analysis.get('content_type') == 'sales':
                    sales_dfs.append(df)
                elif analysis.get('content_type') == 'returns':
                    returns_dfs.append(df)

        # Concatenate and process all identified dataframes
        all_sales = pd.concat(sales_dfs, ignore_index=True) if sales_dfs else pd.DataFrame()
        all_returns = pd.concat(returns_dfs, ignore_index=True) if returns_dfs else pd.DataFrame()

        st.session_state.sales_data = processor.process_sales_data(all_sales)
        st.session_state.returns_data = processor.process_returns_data(all_returns)
        
        # Run the full analysis
        days = (st.session_state.end_date - st.session_state.start_date).days
        st.session_state.analysis_results = run_full_analysis(
            st.session_state.sales_data, st.session_state.returns_data,
            days, st.session_state.unit_cost, st.session_state.sales_price
        )
    st.success("File processing and analysis complete!")

# --- Main App Flow ---
def main():
    """Main function to run the Streamlit application."""
    load_css()
    initialize_session_state()
    initialize_components()
    
    display_header()
    display_sidebar()

    tab_titles = ["📊 Dashboard", "📝 CAPA", "🛡️ Risk & Safety"]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        display_dashboard()

    with tabs[1]:
        display_capa_form()

    with tabs[2]:
        # Placeholder for future Risk & Safety content
        st.header("🛡️ Risk & Safety Analysis Hub")
        st.info("The FMEA, Risk Assessment, and URRA features will be integrated here.")


if __name__ == "__main__":
    main()
