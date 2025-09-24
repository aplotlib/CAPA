# main.py

import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from io import StringIO

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
from src.utils import retry_with_backoff

# --- Page Configuration and Styling ---
st.set_page_config(
    page_title="Product Lifecycle & Quality Manager",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Enhanced UI/UX Styling ---
def load_css():
    """Loads custom CSS for a modern, professional theme."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Main app background */
        .main { background-color: #F5F5F9; }

        /* Custom header */
        .main-header {
            background-color: #FFFFFF;
            padding: 2rem;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border: 1px solid #E0E0E0;
        }
        .main-header h1 {
            font-weight: 700;
            font-size: 2.5rem;
            color: #1a1a2e;
            margin-bottom: 0.5rem;
        }
        .main-header p {
            color: #555;
            font-size: 1.1rem;
        }
        
        /* Metric cards */
        .stMetric {
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 1.5rem;
            border: 1px solid #E0E0E0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 2px solid #E0E0E0;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 8px 8px 0 0;
            border: none;
            padding: 10px 16px;
            font-weight: 600;
            color: #555;
            transition: all 0.2s ease-in-out;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF;
            color: #0068C9;
            border-bottom: 2px solid #0068C9;
        }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E0E0E0;
        }
        
        /* Container styling */
        [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] {
            border: 1px solid #E0E0E0;
            border-radius: 10px;
            padding: 1.2rem;
            background-color: #FFFFFF;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Session State and Component Initialization ---
def initialize_session_state():
    """Initializes all necessary variables in Streamlit's session state."""
    STATE_DEFAULTS = {
        'components_initialized': False, 'api_key_missing': True, 'openai_api_key': None,
        'target_sku': 'SKU-12345', 'unit_cost': 15.50, 'sales_price': 49.99,
        'start_date': date.today() - timedelta(days=30), 'end_date': date.today(),
        'uploaded_files_list': [], 'ai_file_analyses': [], 'user_file_selections': {},
        'sales_data': pd.DataFrame(), 'returns_data': pd.DataFrame(),
        'analysis_results': None, 'capa_feasibility_analysis': None, 'capa_data': {},
        'fmea_data': None, 'pre_mortem_summary': None, 'medical_device_classification': None,
        'vendor_email_draft': None, 'risk_assessment': None, 'urra': None
    }
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

def initialize_components():
    """Initializes all AI-powered components and helpers with OpenAI."""
    if not st.session_state.components_initialized:
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            st.warning("OpenAI API key not found in Streamlit Secrets. AI features will be disabled.")
            st.session_state.api_key_missing = True
        else:
            st.session_state.openai_api_key = api_key
            st.session_state.api_key_missing = False
            st.session_state.file_parser = AIFileParser(api_key)
            st.session_state.data_processor = DataProcessor(api_key)
            st.session_state.ai_context_helper = AIContextHelper(api_key)
            st.session_state.ai_capa_helper = AICAPAHelper(api_key)
            st.session_state.medical_device_classifier = MedicalDeviceClassifier(api_key)
            st.session_state.risk_assessment_generator = RiskAssessmentGenerator(api_key)
            st.session_state.urra_generator = UseRelatedRiskAnalyzer(api_key)
            st.session_state.fmea_generator = FMEA(api_key)
            st.session_state.pre_mortem_generator = PreMortem(api_key)
            st.session_state.doc_generator = CapaDocumentGenerator()
        st.session_state.components_initialized = True

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
        st.image("https://www.vivehealth.com/cdn/shop/files/vive-logo-1_2_250x.png?v=1613713028", width=150)
        st.header("⚙️ Configuration")
        st.session_state.target_sku = st.text_input("🎯 Target Product SKU", value=st.session_state.target_sku)
        st.session_state.unit_cost = st.number_input("💰 Unit Cost ($)", min_value=0.0, value=st.session_state.unit_cost, format="%.2f")
        st.session_state.sales_price = st.number_input("💵 Sales Price ($)", min_value=0.0, value=st.session_state.sales_price, format="%.2f")
        st.session_state.start_date = st.date_input("🗓️ Start Date", value=st.session_state.start_date)
        st.session_state.end_date = st.date_input("🗓️ End Date", value=st.session_state.end_date)

        st.header("➕ Add Data")
        
        # --- File Uploader ---
        with st.expander("📁 Upload Files", expanded=True):
            uploaded_files = st.file_uploader(
                "Upload Sales/Returns Files",
                accept_multiple_files=True,
                type=['csv', 'xlsx', 'png', 'jpg', 'jpeg'],
                key="file_uploader_widget"
            )
            if uploaded_files:
                st.session_state.uploaded_files_list = uploaded_files

            if st.button("🤖 Process Uploaded Files", type="primary", use_container_width=True):
                if not st.session_state.uploaded_files_list:
                    st.warning("Please upload files first.")
                elif st.session_state.api_key_missing:
                    st.error("Cannot process files. OpenAI API key is missing.")
                else:
                    run_ai_file_analysis()
        
        # --- Manual Data Entry ---
        with st.expander("✍️ Manual Data Entry"):
            st.caption("Paste comma-separated data below (e.g., SKU-123,50).")
            sales_placeholder = "sku,quantity\nSKU-12345,100\nSKU-ABCDE,50"
            returns_placeholder = "sku,quantity\nSKU-12345,10"
            
            manual_sales = st.text_area("Sales Data", height=150, placeholder=sales_placeholder, key="manual_sales_input")
            manual_returns = st.text_area("Returns Data", height=150, placeholder=returns_placeholder, key="manual_returns_input")

            if st.button("Process Manual Data", use_container_width=True):
                if not manual_sales:
                    st.warning("Please provide sales data.")
                else:
                    process_manual_data()

def display_dashboard():
    """Displays the main dashboard with metrics and analyses."""
    st.header("📊 Quality Dashboard")
    
    # --- Step 1: AI File Review ---
    if st.session_state.ai_file_analyses:
        with st.container(border=True):
            st.subheader("Step 1: Review AI File Analysis")
            st.info("Our AI has analyzed your files. Please confirm which to include in the analysis.")
            
            selections = {}
            for i, analysis in enumerate(st.session_state.ai_file_analyses):
                file_name = analysis.get("filename", f"File {i+1}")
                content_type = analysis.get("content_type", "unknown").upper()
                summary = analysis.get("summary", "No summary available.")
                
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"**📄 File:** `{file_name}`")
                    st.markdown(f"**⚙️ AI Detected Type:** `{content_type}` | **Summary:** *{summary}*")
                with col2:
                    default_choice = content_type not in ["OTHER", "UNKNOWN"] and "error" not in analysis
                    selections[i] = st.checkbox("✅ Use this file", value=default_choice, key=f"select_{i}", label_visibility="collapsed")
            
            st.session_state.user_file_selections = selections
            
            if st.button("Confirm Selections & Run Full Analysis", type="primary"):
                process_and_run_full_analysis()

    # --- Step 2: Display Analysis Results ---
    if not st.session_state.analysis_results:
        st.info('**Welcome!** Configure your product, then upload files or enter data manually in the sidebar to begin.')
        return

    results = st.session_state.analysis_results
    if "error" in results:
        st.error(f"Analysis Failed: {results['error']}")
        return

    summary_df = results.get('return_summary')
    if summary_df is None or summary_df.empty:
        st.warning("No data found for the target SKU in the provided data.")
        return

    sku_specific_summary = summary_df[summary_df['sku'] == st.session_state.target_sku]
    if sku_specific_summary.empty:
        st.warning(f"No summary data could be calculated for SKU: {st.session_state.target_sku}")
        return
        
    summary_data = sku_specific_summary.iloc[0]

    st.markdown(f"### Overall Analysis for SKU: **{summary_data['sku']}**")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Return Rate", f"{summary_data['return_rate']:.2f}%", help="Percentage of units sold that were returned.")
    col2.metric("Total Returned", f"{int(summary_data['total_returned']):,}")
    col3.metric("Total Sold", f"{int(summary_data['total_sold']):,}")
    col4.metric("Quality Score", f"{results['quality_metrics'].get('quality_score', 'N/A')}/100", delta=results['quality_metrics'].get('risk_level', ''), delta_color="inverse")

    st.markdown(f"**🧠 AI Insights**: {results.get('insights', 'No insights generated.')}")

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
                        report_period_days=report_period_days, target_sku=st.session_state.target_sku
                    )

    if st.session_state.capa_feasibility_analysis:
        cb_results = st.session_state.capa_feasibility_analysis
        st.success(f"**Summary:** {cb_results['summary']}")
        with st.expander("Show detailed calculation"):
            st.table(pd.DataFrame.from_dict(cb_results['details'], orient='index', columns=["Value"]))

def run_ai_file_analysis():
    """Runs the AI analysis on uploaded files and stores the results."""
    with st.spinner("AI is analyzing file contents..."):
        analyses = []
        for file in st.session_state.uploaded_files_list:
            analysis = st.session_state.file_parser.analyze_file_structure(file, st.session_state.target_sku)
            analyses.append(analysis)
        st.session_state.ai_file_analyses = analyses
    st.success("AI file analysis complete. Please review below.")

def process_manual_data():
    """Processes manually entered data and runs the full analysis."""
    with st.spinner("Processing manual data..."):
        try:
            sales_str = st.session_state.manual_sales_input
            returns_str = st.session_state.manual_returns_input
            
            sales_df = pd.read_csv(StringIO(sales_str)) if sales_str.strip() else pd.DataFrame()
            returns_df = pd.read_csv(StringIO(returns_str)) if returns_str.strip() else pd.DataFrame()
            
            # --- Re-use the existing analysis pipeline ---
            st.session_state.sales_data = st.session_state.data_processor.process_sales_data(sales_df)
            st.session_state.returns_data = st.session_state.data_processor.process_returns_data(returns_df)

            report_period_days = (st.session_state.end_date - st.session_state.start_date).days
            st.session_state.analysis_results = run_full_analysis(
                sales_df=st.session_state.sales_data,
                returns_df=st.session_state.returns_data,
                report_period_days=report_period_days,
                unit_cost=st.session_state.unit_cost,
                sales_price=st.session_state.sales_price
            )
            st.success("Manual data processed successfully!")
        except Exception as e:
            st.error(f"Error parsing manual data: {e}. Please ensure it's in 'sku,quantity' format.")

def process_and_run_full_analysis():
    """Processes the user-selected files and runs the main analysis."""
    with st.spinner("Extracting data and running full analysis..."):
        sales_dfs = []
        returns_dfs = []

        for i, analysis in enumerate(st.session_state.ai_file_analyses):
            if st.session_state.user_file_selections.get(i, False):
                file_obj = st.session_state.uploaded_files_list[i]
                content_type = analysis.get('content_type')
                df = st.session_state.file_parser.extract_data(file_obj, analysis, st.session_state.target_sku)
                if df is not None and not df.empty:
                    if content_type == 'sales': sales_dfs.append(df)
                    elif content_type == 'returns': returns_dfs.append(df)
        
        final_sales_df = pd.concat(sales_dfs, ignore_index=True) if sales_dfs else pd.DataFrame()
        final_returns_df = pd.concat(returns_dfs, ignore_index=True) if returns_dfs else pd.DataFrame()

        st.session_state.sales_data = st.session_state.data_processor.process_sales_data(final_sales_df)
        st.session_state.returns_data = st.session_state.data_processor.process_returns_data(final_returns_df)

        report_period_days = (st.session_state.end_date - st.session_state.start_date).days
        st.session_state.analysis_results = run_full_analysis(
            sales_df=st.session_state.sales_data,
            returns_df=st.session_state.returns_data,
            report_period_days=report_period_days,
            unit_cost=st.session_state.unit_cost,
            sales_price=st.session_state.sales_price
        )
    st.success("Analysis complete!")
    st.session_state.ai_file_analyses = [] 
    st.session_state.user_file_selections = {}

def display_ai_chat_interface(tab_name: str):
    """A contextual AI chat interface that provides real answers."""
    st.subheader(f"🤖 AI Assistant for {tab_name}")
    user_query = st.text_input("Ask the AI a question about the current context...", key=f"ai_chat_{tab_name}")
    
    if user_query:
        if st.session_state.get('api_key_missing', True):
            st.error("Cannot generate response. OpenAI API key is not configured.")
        else:
            with st.spinner("AI is thinking..."):
                try:
                    response = st.session_state.ai_context_helper.generate_response(user_query)
                    st.markdown(response)
                except Exception as e:
                    st.error(f"An error occurred while contacting the AI: {e}")

# --- Placeholder Tabs ---
def display_risk_safety_tab():
    st.header("🛡️ Risk & Safety Analysis")
    st.info("This section is for FMEA, ISO 14971 Risk Assessments, and other safety analyses. (Placeholder)")

def display_vendor_comm_tab():
    st.header("✉️ Vendor Communications")
    st.info("Draft and manage communications with your vendors. (Placeholder)")

def display_compliance_tab():
    st.header("⚖️ Compliance Center")
    st.info("Tools for ensuring regulatory compliance. (Placeholder)")

def display_resources_tab():
    st.header("📚 Resources & Industry Standards")
    st.info("A quick reference for key regulations and standards in the medical device industry.")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True): st.markdown("##### **ISO 13485:2016**\nThe QMS standard for medical devices.")
    with col2:
        with st.container(border=True): st.markdown("##### **ISO 14971**\nThe standard for risk management for medical devices.")

def display_exports_tab():
    st.header("📄 Exports")
    st.info("Generate and download comprehensive reports. (Placeholder)")
    st.button("Generate Combined Word Report", type="primary")

# --- Main Application Flow ---
def main():
    """Main function to run the Streamlit application."""
    load_css()
    initialize_session_state()
    initialize_components()
    display_header()
    display_sidebar()

    tab_titles = ["📊 Dashboard", "📝 CAPA", "🛡️ Risk & Safety", "✉️ Vendor Comms", "⚖️ Compliance", "📚 Resources", "📄 Exports"]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        display_dashboard()
        display_ai_chat_interface("the Dashboard")
    with tabs[1]: display_capa_form()
    with tabs[2]: display_risk_safety_tab()
    with tabs[3]: display_vendor_comm_tab()
    with tabs[4]: display_compliance_tab()
    with tabs[5]: display_resources_tab()
    with tabs[6]: display_exports_tab()

if __name__ == "__main__":
    main()
