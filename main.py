# main.py

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import StringIO

# --- Import custom modules ---
from src.parsers import AIFileParser
from src.data_processing import DataProcessor
from src.analysis import run_full_analysis, calculate_cost_benefit
from src.document_generator import DocumentGenerator
from src.ai_capa_helper import (
    AICAPAHelper, AIEmailDrafter, MedicalDeviceClassifier,
    RiskAssessmentGenerator, UseRelatedRiskAnalyzer
)
from src.fmea import FMEA
from src.pre_mortem import PreMortem
from src.ai_context_helper import AIContextHelper
from src.capa_form import display_capa_form

# --- Page Configuration ---
st.set_page_config(page_title="Product Quality Manager", page_icon="🛡️", layout="wide")

# --- Fixed CSS ---
def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .main-header { text-align: center; margin-bottom: 2rem; }
        .main-header h1 { font-weight: 700; font-size: 2.5rem; color: #1a1a2e; margin-bottom: 0.5rem; }
        .main-header p { color: #555; font-size: 1.1rem; }
        .stMetric {
            background-color: #FFFFFF; border-radius: 10px; padding: 1.5rem;
            border: 1px solid #E0E0E0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        /* FIX: Removed fixed height and adjusted padding to prevent overlap */
        .stTabs [data-baseweb="tab"] {
            padding: 12px 16px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Session State Management ---
def initialize_session_state():
    defaults = {
        'openai_api_key': None, 'api_key_missing': True, 'components_initialized': False,
        'target_sku': 'SKU-12345', 'unit_cost': 15.50, 'sales_price': 49.99,
        'start_date': date.today() - timedelta(days=30), 'end_date': date.today(),
        'sales_data': pd.DataFrame(), 'returns_data': pd.DataFrame(),
        'analysis_results': None, 'capa_data': {}, 'fmea_data': None,
        'vendor_email_draft': None, 'risk_assessment': None, 'urra': None,
        'pre_mortem_summary': None, 'medical_device_classification': None
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
    st.session_state.components_initialized = True

def parse_manual_input(input_str: str, target_sku: str) -> pd.DataFrame:
    if not input_str.strip(): return pd.DataFrame()
    if input_str.strip().isnumeric():
        return pd.DataFrame([{'sku': target_sku, 'quantity': int(input_str)}])
    try:
        if 'sku' not in input_str.lower() or 'quantity' not in input_str.lower():
            input_str = f"sku,quantity\n{target_sku},{input_str}"
        return pd.read_csv(StringIO(input_str))
    except Exception:
        st.error("Could not parse manual data. Please enter a single number or a CSV with 'sku' and 'quantity' columns.")
        return pd.DataFrame()

# --- UI Sections ---
def display_header():
    st.markdown('<div class="main-header"><h1>🛡️ Product Lifecycle & Quality Manager</h1><p>Your AI-powered hub for proactive quality assurance, compliance, and vendor management.</p></div>', unsafe_allow_html=True)

def display_sidebar():
    with st.sidebar:
        st.image("https://www.vivehealth.com/cdn/shop/files/vive-logo-1_2_250x.png?v=1613713028", width=150)
        st.header("⚙️ Configuration")
        st.session_state.target_sku = st.text_input("🎯 Target Product SKU", st.session_state.target_sku)
        st.session_state.start_date = st.date_input("🗓️ Start Date", st.session_state.start_date)
        st.session_state.end_date = st.date_input("🗓️ End Date", st.session_state.end_date)
        
        st.header("➕ Add Data")
        st.subheader("✍️ Manual Data Entry (Default)")
        manual_sales = st.text_area("Sales Data", placeholder="Enter total units sold (e.g., 9502) or paste CSV content.", key="manual_sales")
        manual_returns = st.text_area("Returns Data", placeholder="Enter total units returned (e.g., 150) or paste CSV content.", key="manual_returns")
        if st.button("Process Manual Data", type="primary", use_container_width=True):
            if not manual_sales:
                st.warning("Sales data is required.")
            else:
                sales_df = parse_manual_input(manual_sales, st.session_state.target_sku)
                returns_df = parse_manual_input(manual_returns, st.session_state.target_sku)
                process_data(sales_df, returns_df)

        with st.expander("📁 Or Upload Files (Optional)"):
            uploaded_files = st.file_uploader("Upload sales or returns files", accept_multiple_files=True, type=['csv', 'xlsx'])
            if st.button("Process Uploaded Files", use_container_width=True):
                if not uploaded_files:
                    st.warning("Please upload files to process.")
                elif st.session_state.api_key_missing:
                    st.error("Cannot process files without an OpenAI API key.")
                else:
                    process_uploaded_files(uploaded_files)

def display_dashboard():
    st.header("📊 Quality Dashboard")
    if not st.session_state.analysis_results:
        st.info('**Welcome!** Enter data in the sidebar to begin.')
        return
    
    results = st.session_state.analysis_results
    if "error" in results: st.error(f"Analysis Failed: {results['error']}"); return
    
    summary_df = results.get('return_summary')
    if summary_df is None or summary_df.empty: st.warning("No data found for the target SKU."); return
    
    sku_summary = summary_df[summary_df['sku'] == st.session_state.target_sku]
    if sku_summary.empty: st.warning(f"No summary data for SKU: {st.session_state.target_sku}"); return
    
    summary_data = sku_summary.iloc[0]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Return Rate", f"{summary_data['return_rate']:.2f}%")
    c2.metric("Total Returned", f"{int(summary_data['total_returned']):,}")
    c3.metric("Total Sold", f"{int(summary_data['total_sold']):,}")
    c4.metric("Quality Score", f"{results['quality_metrics'].get('quality_score', 'N/A')}/100", delta=results['quality_metrics'].get('risk_level', ''), delta_color="inverse")
    
    st.markdown(f"**🧠 AI Insights**: {results.get('insights', 'N/A')}")

def display_risk_safety_tab():
    st.header("🛡️ Risk & Safety Analysis Hub")
    if st.session_state.api_key_missing: st.error("AI features are disabled. Please configure your API key."); return

    with st.expander("🔬 Failure Mode and Effects Analysis (FMEA)", expanded=True):
        c1, c2 = st.columns(2)
        if c1.button("🤖 Suggest Failure Modes with AI", use_container_width=True):
            if st.session_state.analysis_results:
                with st.spinner("AI is suggesting failure modes..."):
                    insights = st.session_state.analysis_results.get('insights', 'High return rate observed.')
                    suggestions = st.session_state.fmea_generator.suggest_failure_modes(insights, st.session_state.analysis_results)
                    st.session_state.fmea_data = pd.DataFrame(suggestions)
            else: st.warning("Run an analysis on the dashboard first.")
        if c2.button("➕ Add Manual FMEA Row", use_container_width=True):
            new_row = pd.DataFrame([{"Potential Failure Mode": "", "Potential Effect(s)": "", "Severity": 1, "Potential Cause(s)": "", "Occurrence": 1, "Current Controls": "", "Detection": 1, "RPN": 1}])
            st.session_state.fmea_data = pd.concat([st.session_state.fmea_data, new_row], ignore_index=True) if st.session_state.fmea_data is not None else new_row

        if st.session_state.fmea_data is not None:
            edited_df = st.data_editor(st.session_state.fmea_data, num_rows="dynamic", use_container_width=True)
            edited_df['RPN'] = pd.to_numeric(edited_df['Severity'], errors='coerce').fillna(1) * pd.to_numeric(edited_df['Occurrence'], errors='coerce').fillna(1) * pd.to_numeric(edited_df['Detection'], errors='coerce').fillna(1)
            st.session_state.fmea_data = edited_df

def display_vendor_comm_tab():
    st.header("✉️ Vendor Communications Center")
    if st.session_state.api_key_missing: st.error("AI features are disabled."); return
    if not st.session_state.analysis_results: st.info("Run an analysis on the Dashboard tab first to activate this feature."); return
    
    with st.form("vendor_email_form"):
        st.subheader("Draft a Vendor Email with AI")
        c1, c2 = st.columns(2)
        vendor_name = c1.text_input("Vendor Name")
        contact_name = c2.text_input("Contact Name")
        po_numbers = st.text_input("Relevant Purchase Order #s (optional)")
        
        firmness = st.slider("Firmness of Tone", 1, 5, 2, help="1: Soft inquiry, 5: Politely demanding")
        english_ability = st.slider("Recipient's English Proficiency", 1, 5, 3)
        
        submitted = st.form_submit_button("Draft Email", type="primary")
        if submitted:
            with st.spinner("AI is drafting email..."):
                st.session_state.vendor_email_draft = st.session_state.ai_email_drafter.draft_vendor_email(
                    st.session_state.analysis_results, st.session_state.capa_data, st.session_state.target_sku,
                    vendor_name, contact_name, po_numbers, english_ability, firmness
                )
    
    if st.session_state.vendor_email_draft:
        st.text_area("Generated Draft", st.session_state.vendor_email_draft, height=300)
        
        if st.button("Generate Formal SCAR Document"):
            with st.spinner("Generating SCAR document..."):
                scar_buffer = st.session_state.doc_generator.generate_scar_docx(st.session_state.capa_data, vendor_name)
                st.download_button(
                    "📥 Download SCAR (.docx)", scar_buffer, 
                    f"SCAR_{st.session_state.target_sku}_{date.today()}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

def display_compliance_tab():
    st.header("⚖️ Compliance Center")
    if st.session_state.api_key_missing: st.error("AI features are disabled."); return

    with st.expander("Medical Device Classification (U.S. FDA)"):
        with st.form("classification_form"):
            device_desc = st.text_area("Describe your device's intended use:", height=150)
            if st.form_submit_button("Classify Device", type="primary"):
                with st.spinner("AI is classifying..."):
                    st.session_state.medical_device_classification = st.session_state.medical_device_classifier.classify_device(device_desc)
        if st.session_state.medical_device_classification:
            res = st.session_state.medical_device_classification
            st.success(f"**Classification:** {res.get('classification', 'N/A')}")
            st.markdown(f"**Rationale:** {res.get('rationale', 'N/A')}")

    with st.expander("Pre-Mortem Analysis"):
        scenario = st.text_input("Define failure scenario:", "Our new product launch failed.")
        if st.button("Generate Pre-Mortem Questions"):
            # Implementation for Pre-Mortem questions can be added here
            st.info("Pre-mortem feature to be fully implemented.")

def display_exports_tab():
    st.header("📄 Document Exports")
    st.info("Generate formal reports based on your session data.")
    
    if st.button("Generate CAPA Report (.docx)", type="primary", use_container_width=True):
        if not st.session_state.capa_data.get('issue_description'):
            st.warning("Please fill out the CAPA form before generating a report.")
        else:
            with st.spinner("Generating CAPA document..."):
                capa_buffer = st.session_state.doc_generator.generate_capa_docx(st.session_state.capa_data)
                st.download_button(
                    "📥 Download CAPA Report", capa_buffer,
                    f"CAPA_{st.session_state.capa_data.get('capa_number', st.session_state.target_sku)}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

# --- Process Functions ---
def process_data(sales_df: pd.DataFrame, returns_df: pd.DataFrame):
    """Processes dataframes and runs the main analysis."""
    with st.spinner("Processing data and running analysis..."):
        processor = st.session_state.data_processor
        st.session_state.sales_data = processor.process_sales_data(sales_df)
        st.session_state.returns_data = processor.process_returns_data(returns_df)
        
        days = (st.session_state.end_date - st.session_state.start_date).days
        st.session_state.analysis_results = run_full_analysis(
            st.session_state.sales_data, st.session_state.returns_data,
            days, st.session_state.unit_cost, st.session_state.sales_price
        )
    st.success("Analysis complete!")

def process_uploaded_files(uploaded_files):
    """Uses AI to parse uploaded files and runs analysis."""
    parser = st.session_state.file_parser
    sales_dfs, returns_dfs = [], []
    for file in uploaded_files:
        analysis = parser.analyze_file_structure(file, st.session_state.target_sku)
        df = parser.extract_data(file, analysis, st.session_state.target_sku)
        if df is not None:
            if analysis.get('content_type') == 'sales': sales_dfs.append(df)
            elif analysis.get('content_type') == 'returns': returns_dfs.append(df)
    
    sales_df = pd.concat(sales_dfs, ignore_index=True) if sales_dfs else pd.DataFrame()
    returns_df = pd.concat(returns_dfs, ignore_index=True) if returns_dfs else pd.DataFrame()
    process_data(sales_df, returns_df)

# --- Main App Flow ---
def main():
    load_css()
    initialize_session_state()
    initialize_components()
    display_header()
    display_sidebar()

    tabs = st.tabs(["📊 Dashboard", "📝 CAPA", "🛡️ Risk & Safety", "✉️ Vendor Comms", "⚖️ Compliance", "📄 Exports"])
    
    with tabs[0]: display_dashboard()
    with tabs[1]: display_capa_form()
    with tabs[2]: display_risk_safety_tab()
    with tabs[3]: display_vendor_comm_tab()
    with tabs[4]: display_compliance_tab()
    with tabs[5]: display_exports_tab()

if __name__ == "__main__":
    main()
