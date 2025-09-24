# main.py

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from io import BytesIO
import json
import os
from typing import Dict, Optional, Any
import time
import copy

# Import custom modules
from src.parsers import AIFileParser
from src.data_processing import DataProcessor
from src.analysis import run_full_analysis, calculate_cost_benefit
from src.compliance import validate_capa_data
from src.document_generator import CapaDocumentGenerator
from src.ai_capa_helper import AICAPAHelper, AIEmailDrafter, MedicalDeviceClassifier, RiskAssessmentGenerator, UseRelatedRiskAnalyzer
from src.fmea import FMEA
from src.pre_mortem import PreMortem
from src.fba_returns_processor import ReturnsProcessor
from src.ai_context_helper import AIContextHelper
from src.capa_form import display_capa_form

# --- Page Configuration and Styling ---
st.set_page_config(
    page_title="Product Lifecycle & Quality Manager",
    page_icon="
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-shield"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Enhanced UI/UX Styling ---
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
    }

    /* Custom info, success, warning, error boxes */
    .info-box, .success-box, .warning-box, .error-box {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
        border-left: 5px solid;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .info-box { background-color: #E3F2FD; border-color: #1E88E5; }
    .success-box { background-color: #E8F5E9; border-color: #43A047; }
    .warning-box { background-color: #FFF8E1; border-color: #FFB300; }
    .error-box { background-color: #FFEBEE; border-color: #E53935; }

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

# --- AI and Component Initialization ---
def initialize_components():
    """Initialize all AI-powered components and helpers."""
    if 'components_initialized' not in st.session_state:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if not api_key:
            st.warning("Anthropic API key not found. AI features will be limited.")
            # Set a flag to indicate that the API key is missing
            st.session_state.api_key_missing = True
        else:
            st.session_state.anthropic_api_key = api_key
            st.session_state.api_key_missing = False

        # Even if the API key is missing, we can still initialize the components
        # The individual methods in the components will handle the missing key gracefully
        st.session_state.file_parser = AIFileParser(api_key)
        st.session_state.data_processor = DataProcessor(api_key)
        st.session_state.ai_context_helper = AIContextHelper(api_key)
        st.session_state.ai_capa_helper = AICAPAHelper(api_key)
        st.session_state.medical_device_classifier = MedicalDeviceClassifier(api_key)
        st.session_state.risk_assessment_generator = RiskAssessmentGenerator(api_key)
        st.session_state.urra_generator = UseRelatedRiskAnalyzer(api_key)
        st.session_state.components_initialized = True
# --- UI Sections ---
def display_header():
    st.markdown(
        '<div class="main-header">'
        '<h1><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-shield"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg> Product Lifecycle & Quality Manager</h1>'
        '<p>Your AI-powered hub for proactive quality assurance, compliance, and vendor management.</p>'
        '</div>',
        unsafe_allow_html=True
    )
def display_resources_tab():
    """Displays a tab with resources and information based on provided infographics."""
    st.header("📚 Resources & Industry Standards")
    st.info(
        "This section provides an overview of key regulations and standards for the medical device industry, "
        "inspired by the 'Industry Standards Infographic'. Use this as a quick reference."
    )

    st.subheader("Key Quality & Risk Management Standards")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("##### **ISO 13485:2016**")
            st.markdown("The international standard for a Quality Management System (QMS) for medical devices. It ensures consistency in the design, development, production, and delivery of medical devices that are safe for their intended purpose.")
    with col2:
        with st.container(border=True):
            st.markdown("##### **ISO 14971**")
            st.markdown("The international standard for the application of risk management to medical devices. It outlines a process for identifying hazards, estimating and evaluating risks, and implementing risk controls.")

    st.subheader("Major Regulatory Frameworks")
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown("##### **FDA 21 CFR Part 820 (QSR)**")
            st.markdown("The US Food and Drug Administration's Quality System Regulation (QSR) outlines Current Good Manufacturing Practice (CGMP) requirements for medical device manufacturers.")
    with col2:
        with st.container(border=True):
            st.markdown("##### **EU MDR (Medical Device Regulation)**")
            st.markdown("The regulatory framework for medical devices in the European Union. It places a strong emphasis on a life-cycle approach to safety, backed by clinical data.")
    with col3:
        with st.container(border=True):
            st.markdown("##### **MDSAP**")
            st.markdown("The Medical Device Single Audit Program allows a single regulatory audit of a medical device manufacturer's QMS to satisfy the requirements of multiple regulatory authorities (USA, Canada, Brazil, Australia, Japan).")

    st.subheader("Data Integrity & Documentation")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("##### **21 CFR Part 11**")
            st.markdown("This FDA regulation provides criteria for the acceptance of electronic records, electronic signatures, and handwritten signatures executed to electronic records as equivalent to paper records.")
    with col2:
        with st.container(border=True):
            st.markdown("##### **Annex 11 (EU)**")
            st.markdown("Part of the European Union's GMP guidelines, Annex 11 provides guidance on the management of electronic records and systems within the pharmaceutical and medical device industries.")
def display_dashboard():
    # ... (rest of the dashboard function, with an added section at the top)
    with st.expander("💡 Why a Proactive Approach to Quality Matters", expanded=False):
        st.markdown(
            """
            *Inspired by the 'Value of True Quality Infographic'.*

            A proactive approach to quality is not just about compliance; it's a strategic business investment. By focusing on **prevention** and **monitoring**, you can significantly reduce the high costs associated with both internal and external failures.

            - **Cost of Poor Quality**: Includes scrap, rework, recalls, warranty claims, and damage to your brand's reputation.
            - **Benefits of True Quality**: Leads to lower total costs, increased revenue, faster innovation, higher brand equity, and reduced regulatory risk.

            This tool is designed to help you shift from a reactive to a proactive quality culture.
            """
        )
    # ... (the rest of your original display_dashboard function)
    st.info(
        "**🎯 Welcome!**\n\n"
        "1.  **Start in the sidebar**: Enter your product's SKU, cost/price, and date range.\n"
        "2.  **Add Data**: Enter sales/returns manually or upload files for the AI to parse.\n"
        "3.  **Analyze**: This dashboard will then show your key quality and financial metrics."
    )
    if st.session_state.get('pending_image_confirmations'):
        st.header("🖼️ Image Data Confirmation")
        st.warning("Action Required: Review the data extracted from your images.")

        for analysis in st.session_state.pending_image_confirmations[:]:
            with st.form(key=f"image_confirm_{analysis['file_id']}"):
                st.image(analysis['file_bytes'], width=300, caption=analysis['filename'])
                key_data = analysis.get('key_data', {})
                content_type = st.selectbox("Detected Content Type", ['sales', 'returns', 'other'], index=['sales', 'returns', 'other'].index(analysis.get('content_type', 'other')), key=f"type_{analysis['file_id']}")
                quantity = st.number_input("Detected Quantity", min_value=0, value=int(key_data.get('total_quantity', 0)), step=1, key=f"qty_{analysis['file_id']}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Confirm and Add Data", type="primary"):
                        if content_type in ['sales', 'returns']:
                            df = pd.DataFrame([{'sku': st.session_state.target_sku, 'quantity': quantity}])
                            (st.session_state.sales_data if content_type == 'sales' else st.session_state.returns_data).setdefault('image_uploads', []).append(df)
                        st.session_state.pending_image_confirmations.remove(analysis)
                        st.rerun()
                with col2:
                    if st.form_submit_button("❌ Discard"):
                        st.session_state.pending_image_confirmations.remove(analysis)
                        st.rerun()
        st.markdown("---")
        if not st.session_state.pending_image_confirmations:
            trigger_final_analysis()


    st.header("📊 Quality Dashboard")
    if not st.session_state.analysis_results:
        st.markdown('👆 **Enter data in the sidebar to view your dashboard.**')
        return

    results = st.session_state.analysis_results
    summary = results.get('return_summary')
    if summary is None or not isinstance(summary, pd.DataFrame) or summary.empty:
        st.warning("Analysis did not produce a valid summary. Please process data first.")
        return

    summary_data = summary.iloc[0]
    st.markdown(f"### Overall Analysis for SKU: **{summary_data['sku']}**")
    cols = st.columns(4)
    cols[0].metric("Return Rate", f"{summary_data['return_rate']:.2f}%", help="Percentage of units sold that were returned.")
    cols[1].metric("Total Sold", f"{int(summary_data['total_sold']):,}", help="Total units sold.")
    cols[2].metric("Total Returned", f"{int(summary_data['total_returned']):,}", help="Total units returned.")
    cols[3].metric("Quality Score", f"{results['quality_metrics'].get('quality_score', 'N/A')}/100", delta=results['quality_metrics'].get('risk_level', ''), help="AI-calculated score based on return rate.")
    st.markdown(results.get('insights', ''))

    st.markdown("---")
    st.subheader("💡 Cost-Benefit Analysis for Potential Fix")
    st.info("Project the financial impact of a proposed quality improvement.")

    with st.form("cost_benefit_form"):
        col1, col2 = st.columns(2)
        with col1:
            cost_change = st.number_input("Cost increase per unit ($)", min_value=0.0, step=0.01, format="%.2f", help="How much will the fix add to the unit cost?")
        with col2:
            expected_rr_reduction = st.number_input("Expected return rate reduction (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", help="How much do you expect the return rate to drop by?")
        
        submitted = st.form_submit_button("Calculate Financial Impact", use_container_width=True, type="primary")

        if submitted:
            if st.session_state.unit_cost > 0:
                report_period_days = (st.session_state.end_date - st.session_state.start_date).days
                with st.spinner("Calculating cost-benefit..."):
                    cost_benefit_results = calculate_cost_benefit(
                        analysis_results=st.session_state.analysis_results, current_unit_cost=st.session_state.unit_cost,
                        cost_change=cost_change, expected_rr_reduction=expected_rr_reduction, report_period_days=report_period_days
                    )
                    st.session_state.capa_feasibility_analysis = cost_benefit_results
            else:
                st.warning("Please set a 'Unit Cost' in the sidebar to run this analysis.")

    if st.session_state.capa_feasibility_analysis:
        cb_results = st.session_state.capa_feasibility_analysis
        st.success(f"**Summary:** {cb_results['summary']}")
        with st.expander("Show detailed calculation"):
            st.table(pd.DataFrame.from_dict(cb_results['details'], orient='index', columns=["Value"]))

    display_ai_chat_interface("the Dashboard")

# --- Main Application Flow ---
def main():
    # --- (Your existing functions: initialize_session_state, initialize_components, etc. remain here) ---
    initialize_session_state()
    display_header()
    initialize_components()
    display_sidebar()

    # --- Updated Tab Navigation ---
    tab_list = [
        "📊 Dashboard",
        "📝 CAPA",
        "🛡️ Risk & Safety",
        "✉️ Vendor Comms",
        "⚖️ Compliance",
        "📚 Resources & Standards", # New Tab
        "📄 Exports"
    ]
    tabs = st.tabs(tab_list)

    with tabs[0]: display_dashboard()
    with tabs[1]: display_capa_form()
    with tabs[2]: display_risk_safety_tab()
    with tabs[3]: display_vendor_comm_tab()
    with tabs[4]: display_compliance_tab()
    with tabs[5]: display_resources_tab() # New Tab Content
    with tabs[6]: display_exports_tab()

if __name__ == "__main__":
    main()
