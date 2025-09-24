# main.py

import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import os
from io import StringIO, BytesIO
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
    """Loads custom CSS for a modern, professional theme."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }
        
        .main { background-color: #F5F5F9; }

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
        
        .stMetric {
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 1.5rem;
            border: 1px solid #E0E0E0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }
        
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

        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E0E0E0;
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
        'uploaded_files_list': [], 'ai_file_analyses': [], 'user_file_selections': {},
        'sales_data': pd.DataFrame(), 'returns_data': pd.DataFrame(),
        'analysis_results': None, 'capa_feasibility_analysis': None, 'capa_data': {},
        'fmea_data': None, 'pre_mortem_summary': None, 'medical_device_classification': None,
        'vendor_email_draft': None, 'risk_assessment': None, 'urra': None,
        'chat_history': {}, 'pre_mortem_questions': []
    }
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

def get_serializable_state() -> str:
    """Creates a JSON-serializable representation of the session state, excluding non-serializable items."""
    serializable_keys = [
        'target_sku', 'unit_cost', 'sales_price', 'start_date', 'end_date',
        'analysis_results', 'capa_feasibility_analysis', 'capa_data',
        'fmea_data', 'pre_mortem_summary', 'medical_device_classification',
        'vendor_email_draft', 'risk_assessment', 'urra', 'chat_history',
        'pre_mortem_questions', 'sales_data', 'returns_data'
    ]
    
    state_to_save = {key: st.session_state.get(key) for key in serializable_keys}
    
    # Custom serialization for complex objects
    def serialize_value(v):
        if isinstance(v, pd.DataFrame):
            return v.to_json(orient='split')
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        if isinstance(v, (dict, list)):
            return json.loads(json.dumps(v, default=str)) # A trick to serialize nested structures
        return v

    state_copy = copy.deepcopy(state_to_save)
    for k, v in state_copy.items():
        state_copy[k] = serialize_value(v)
        # Special handling for nested dataframes
        if k == 'analysis_results' and isinstance(v, dict) and 'return_summary' in v:
            state_copy[k]['return_summary'] = serialize_value(v['return_summary'])
            
    return json.dumps(state_copy, indent=2, default=str)


def load_state_from_json(uploaded_file):
    """Loads session state from an uploaded JSON file."""
    try:
        loaded_state = json.load(uploaded_file)
        for key, value in loaded_state.items():
            if key in st.session_state:
                if isinstance(value, str):
                     try:
                        # Attempt to parse as DataFrame
                        st.session_state[key] = pd.read_json(StringIO(value), orient='split')
                     except (ValueError, TypeError):
                        # Attempt to parse as date
                        try:
                            st.session_state[key] = date.fromisoformat(value)
                        except (ValueError, TypeError):
                            st.session_state[key] = value # Assign as string
                elif key == 'analysis_results' and isinstance(value, dict) and 'return_summary' in value:
                    value['return_summary'] = pd.read_json(StringIO(value['return_summary']), orient='split')
                    st.session_state[key] = value
                else:
                    st.session_state[key] = value
        st.success("Session loaded successfully!")
    except Exception as e:
        st.error(f"Failed to load session: {e}")


# --- Component Initialization ---
def initialize_components():
    """Initializes all AI-powered components."""
    if not st.session_state.components_initialized:
        api_key = st.secrets.get("OPENAI_API_KEY")
        st.session_state.api_key_missing = not bool(api_key)
        
        if not st.session_state.api_key_missing:
            st.session_state.openai_api_key = api_key
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

# --- Helper Functions ---
def parse_manual_input(input_str: str, target_sku: str) -> pd.DataFrame:
    """Intelligently parses manual string input."""
    input_str = input_str.strip()
    if not input_str: return pd.DataFrame()
    if input_str.isnumeric():
        return pd.DataFrame([{'sku': target_sku, 'quantity': int(input_str)}])
    try:
        if 'sku' not in input_str.lower() or 'quantity' not in input_str.lower():
             input_str = f"sku,quantity\n{input_str}"
        return pd.read_csv(StringIO(input_str))
    except Exception as e:
        st.error(f"Could not parse data. Error: {e}")
        return pd.DataFrame()

# --- UI Sections ---
def display_header():
    st.markdown('<div class="main-header"><h1>🛡️ Product Lifecycle & Quality Manager</h1><p>Your AI-powered hub for proactive quality assurance, compliance, and vendor management.</p></div>', unsafe_allow_html=True)

def display_sidebar():
    with st.sidebar:
        st.image("https://www.vivehealth.com/cdn/shop/files/vive-logo-1_2_250x.png?v=1613713028", width=150)
        
        with st.expander("💾 Session Management", expanded=True):
            st.download_button("📤 Export Session", get_serializable_state(), f"session_{date.today()}.json", "application/json", use_container_width=True)
            uploaded_state = st.file_uploader("📥 Import Session", type="json")
            if uploaded_state: load_state_from_json(uploaded_state)

        st.header("⚙️ Configuration")
        st.session_state.target_sku = st.text_input("🎯 Target Product SKU", st.session_state.target_sku)
        st.session_state.unit_cost = st.number_input("💰 Unit Cost ($)", 0.0, value=st.session_state.unit_cost, format="%.2f")
        st.session_state.sales_price = st.number_input("💵 Sales Price ($)", 0.0, value=st.session_state.sales_price, format="%.2f")
        st.session_state.start_date = st.date_input("🗓️ Start Date", st.session_state.start_date)
        st.session_state.end_date = st.date_input("🗓️ End Date", st.session_state.end_date)
        
        st.header("➕ Add Data")
        st.subheader("✍️ Manual Data Entry")
        manual_sales = st.text_area("Sales Data", "", key="manual_sales_input", placeholder="e.g., 9502\nOr paste CSV...")
        manual_returns = st.text_area("Returns Data", "", key="manual_returns_input", placeholder="e.g., 150\nOr paste CSV...")
        if st.button("Process Manual Data", type="primary", use_container_width=True):
            if not manual_sales: st.warning("Please provide sales data.")
            else: process_manual_data()
        
        with st.expander("📁 Or Upload Files"):
            uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True, type=['csv', 'xlsx', 'png', 'jpg'], key="file_uploader_widget")
            if uploaded_files: st.session_state.uploaded_files_list = uploaded_files
            if st.button("🤖 Process Uploaded Files", use_container_width=True):
                if not st.session_state.uploaded_files_list: st.warning("Please upload files.")
                elif st.session_state.api_key_missing: st.error("Cannot process files. OpenAI API key is missing.")
                else: run_ai_file_analysis()

def display_dashboard():
    st.header("📊 Quality Dashboard")
    if st.session_state.ai_file_analyses:
        with st.container(border=True):
            st.subheader("Step 1: Review AI File Analysis")
            selections = {}
            for i, analysis in enumerate(st.session_state.ai_file_analyses):
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"**📄 File:** `{analysis.get('filename', f'File {i+1}')}` | **Type:** `{analysis.get('content_type', 'N/A').upper()}`")
                with col2:
                    selections[i] = st.checkbox("✅ Use", value=True, key=f"select_{i}", label_visibility="collapsed")
            st.session_state.user_file_selections = selections
            if st.button("Confirm & Run Analysis", type="primary"): process_and_run_full_analysis()

    if not st.session_state.analysis_results:
        st.info('**Welcome!** Enter data in the sidebar to begin.')
        return
    results = st.session_state.analysis_results
    if "error" in results:
        st.error(f"Analysis Failed: {results['error']}")
        return
    summary_df = results.get('return_summary')
    if summary_df is None or summary_df.empty:
        st.warning("No data found for the target SKU.")
        return
    sku_summary = summary_df[summary_df['sku'] == st.session_state.target_sku]
    if sku_summary.empty:
        st.warning(f"No summary data for SKU: {st.session_state.target_sku}")
        return
    summary_data = sku_summary.iloc[0]
    
    with st.container(border=True):
        st.markdown(f"### Analysis for SKU: **{summary_data['sku']}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Return Rate", f"{summary_data['return_rate']:.2f}%")
        c2.metric("Total Returned", f"{int(summary_data['total_returned']):,}")
        c3.metric("Total Sold", f"{int(summary_data['total_sold']):,}")
        c4.metric("Quality Score", f"{results['quality_metrics'].get('quality_score', 'N/A')}/100", delta=results['quality_metrics'].get('risk_level', ''), delta_color="inverse")
        st.markdown(f"**🧠 AI Insights**: {results.get('insights', 'N/A')}")

    with st.container(border=True):
        st.subheader("💡 Cost-Benefit Analysis")
        with st.form("cost_benefit_form"):
            c1, c2 = st.columns(2)
            cost_change = c1.number_input("Cost increase per unit ($)", 0.0, format="%.2f")
            expected_rr_reduction = c2.number_input("Expected return rate reduction (%)", 0.0, 100.0, format="%.1f")
            if st.form_submit_button("Calculate Financial Impact", type="primary", use_container_width=True):
                st.session_state.capa_feasibility_analysis = calculate_cost_benefit(
                    results, st.session_state.unit_cost, cost_change, expected_rr_reduction,
                    (st.session_state.end_date - st.session_state.start_date).days, st.session_state.target_sku
                )
        if st.session_state.capa_feasibility_analysis:
            res = st.session_state.capa_feasibility_analysis
            st.success(f"**Summary:** {res['summary']}")
            with st.expander("Show calculation"): st.table(pd.DataFrame.from_dict(res['details'], orient='index', columns=["Value"]))

def display_risk_safety_tab():
    st.header("🛡️ Risk & Safety Analysis")
    if st.session_state.api_key_missing: st.error("AI features disabled."); return

    with st.container(border=True):
        st.subheader("Failure Mode and Effects Analysis (FMEA)")
        if st.button("🤖 Suggest FMEA Failure Modes with AI"):
            if st.session_state.analysis_results:
                with st.spinner("AI is suggesting failure modes..."):
                    suggestions = st.session_state.fmea_generator.suggest_failure_modes(
                        st.session_state.analysis_results.get('insights', ''), st.session_state.analysis_results
                    )
                    st.session_state.fmea_data = pd.DataFrame(suggestions)
            else: st.warning("Run an analysis on the dashboard first.")
        
        if 'fmea_data' not in st.session_state or st.session_state.fmea_data is None:
             st.session_state.fmea_data = pd.DataFrame(columns=["Potential Failure Mode", "Potential Effect(s)", "Severity", "Potential Cause(s)", "Occurrence", "Current Controls", "Detection", "RPN"])

        edited_df = st.data_editor(st.session_state.fmea_data, num_rows="dynamic", key="fmea_editor", column_config={
            "Severity": st.column_config.NumberColumn(min_value=1, max_value=10, required=True),
            "Occurrence": st.column_config.NumberColumn(min_value=1, max_value=10, required=True),
            "Detection": st.column_config.NumberColumn(min_value=1, max_value=10, required=True),
            "RPN": st.column_config.NumberColumn(disabled=True, help="S x O x D")
        })
        for col in ['Severity', 'Occurrence', 'Detection']: edited_df[col] = pd.to_numeric(edited_df[col], errors='coerce').fillna(1)
        edited_df['RPN'] = edited_df['Severity'] * edited_df['Occurrence'] * edited_df['Detection']
        st.session_state.fmea_data = edited_df

    with st.container(border=True):
        st.subheader("ISO 14971 Risk Assessment")
        with st.form("risk_assessment_form"):
            prod_desc = st.text_area("Product Description & Intended Use")
            if st.form_submit_button("Generate Assessment", type="primary"):
                with st.spinner("AI is generating risk assessment..."):
                    st.session_state.risk_assessment = st.session_state.risk_assessment_generator.generate_assessment(
                        st.session_state.target_sku, st.session_state.target_sku, prod_desc, "ISO 14971"
                    )
        if st.session_state.risk_assessment: st.markdown(st.session_state.risk_assessment)

def display_vendor_comm_tab():
    st.header("✉️ Vendor Communications")
    if st.session_state.api_key_missing: st.error("AI features disabled."); return

    with st.container(border=True):
        st.subheader("Draft a Vendor Email with AI")
        if not st.session_state.analysis_results: st.info("Run an analysis first."); return
        with st.form("vendor_email_form"):
            c1, c2 = st.columns(2)
            vendor_name = c1.text_input("Vendor Name")
            contact_name = c2.text_input("Contact Name")
            goal = st.text_area("Goal of Email", "Investigate the increase in return rate.")
            english_ability = st.slider("Recipient's English Proficiency", 1, 5, 3)
            if st.form_submit_button("Draft Email", type="primary"):
                with st.spinner("AI is drafting email..."):
                    st.session_state.vendor_email_draft = st.session_state.ai_capa_helper.draft_vendor_email(
                        goal, st.session_state.analysis_results, st.session_state.target_sku,
                        vendor_name, contact_name, english_ability
                    )
        if st.session_state.vendor_email_draft: st.text_area("Generated Draft", st.session_state.vendor_email_draft, height=300)

def display_compliance_tab():
    st.header("⚖️ Compliance Center")
    if st.session_state.api_key_missing: st.error("AI features disabled."); return

    with st.container(border=True):
        st.subheader("Medical Device Classification (U.S. FDA)")
        with st.form("classification_form"):
            device_desc = st.text_area("Describe your device")
            if st.form_submit_button("Classify Device", type="primary"):
                with st.spinner("AI is classifying..."):
                    st.session_state.medical_device_classification = st.session_state.medical_device_classifier.classify_device(device_desc)
        if st.session_state.medical_device_classification:
            res = st.session_state.medical_device_classification
            st.success(f"**Classification:** {res.get('classification', 'N/A')}")
            st.markdown(f"**Rationale:** {res.get('rationale', 'N/A')}")

    with st.container(border=True):
        st.subheader("Pre-Mortem Analysis")
        scenario = st.text_input("Define failure scenario:", "Our new product launch failed.")
        if st.button("Generate Pre-Mortem Questions"):
            with st.spinner("AI is generating questions..."):
                st.session_state.pre_mortem_questions = st.session_state.pre_mortem_generator.generate_questions(scenario)
        if st.session_state.pre_mortem_questions:
            answers = [{"question": q, "answer": st.text_area(f"**Q:** {q}", key=f"pm_q_{i}")} for i, q in enumerate(st.session_state.pre_mortem_questions)]
            if st.button("Summarize Session"):
                with st.spinner("AI is summarizing..."):
                    st.session_state.pre_mortem_summary = st.session_state.pre_mortem_generator.summarize_answers(answers)
        if st.session_state.pre_mortem_summary: st.markdown(st.session_state.pre_mortem_summary)

def display_exports_tab():
    st.header("📄 Exports")
    st.info("Compile all session data into a single Word document.")
    if st.button("Generate Combined Word Report", type="primary"):
        with st.spinner("Generating document..."):
            # Create a dictionary of only the data we want to export
            export_content = {
                'sku': st.session_state.target_sku,
                'analysis_results': st.session_state.analysis_results,
                'capa_data': st.session_state.capa_data,
                'fmea_data': st.session_state.fmea_data,
                'medical_device_classification': st.session_state.medical_device_classification,
                'risk_assessment': st.session_state.risk_assessment,
                'urra': st.session_state.urra,
                'pre_mortem_summary': st.session_state.pre_mortem_summary,
                'vendor_email_draft': st.session_state.vendor_email_draft
            }
            doc_buffer = st.session_state.doc_generator.export_all_to_docx(export_content)
            st.download_button("📥 Download Report", doc_buffer, f"Quality_Report_{st.session_state.target_sku}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        st.success("Report generated!")

def display_ai_chat_interface(tab_name: str):
    with st.container(border=True):
        st.subheader(f"🤖 AI Assistant for {tab_name}")
        if tab_name not in st.session_state.chat_history: st.session_state.chat_history[tab_name] = []
        for author, message in st.session_state.chat_history[tab_name]:
            with st.chat_message(author): st.markdown(message)
        prompt = st.chat_input(f"Ask about {tab_name}...")
        if prompt:
            st.session_state.chat_history[tab_name].append(("user", prompt))
            with st.chat_message("user"): st.markdown(prompt)
            with st.spinner("AI is thinking..."):
                response = st.session_state.ai_context_helper.generate_response(prompt)
                st.session_state.chat_history[tab_name].append(("assistant", response))
                with st.chat_message("assistant"): st.markdown(response)

# --- Process Functions ---
def reset_analysis_state():
    st.session_state.analysis_results, st.session_state.capa_feasibility_analysis = None, None
    st.session_state.ai_file_analyses, st.session_state.user_file_selections = [], {}
    st.session_state.sales_data, st.session_state.returns_data = pd.DataFrame(), pd.DataFrame()

def run_ai_file_analysis():
    reset_analysis_state()
    st.session_state.manual_sales_input, st.session_state.manual_returns_input = "", ""
    with st.spinner("AI is analyzing files..."):
        st.session_state.ai_file_analyses = [st.session_state.file_parser.analyze_file_structure(file, st.session_state.target_sku) for file in st.session_state.uploaded_files_list]
    st.success("AI analysis complete.")

def process_manual_data():
    reset_analysis_state()
    with st.spinner("Processing data..."):
        sales_df = parse_manual_input(st.session_state.manual_sales_input, st.session_state.target_sku)
        returns_df = parse_manual_input(st.session_state.manual_returns_input, st.session_state.target_sku)
        st.session_state.sales_data = st.session_state.data_processor.process_sales_data(sales_df)
        st.session_state.returns_data = st.session_state.data_processor.process_returns_data(returns_df)
        st.session_state.analysis_results = run_full_analysis(
            st.session_state.sales_data, st.session_state.returns_data,
            (st.session_state.end_date - st.session_state.start_date).days,
            st.session_state.unit_cost, st.session_state.sales_price
        )
        if "error" not in st.session_state.analysis_results: st.success("Manual data processed!")

def process_and_run_full_analysis():
    with st.spinner("Extracting and analyzing data..."):
        sales_dfs, returns_dfs = [], []
        for i, analysis in enumerate(st.session_state.ai_file_analyses):
            if st.session_state.user_file_selections.get(i, False):
                df = st.session_state.file_parser.extract_data(st.session_state.uploaded_files_list[i], analysis, st.session_state.target_sku)
                if df is not None:
                    if analysis.get('content_type') == 'sales': sales_dfs.append(df)
                    elif analysis.get('content_type') == 'returns': returns_dfs.append(df)
        
        st.session_state.sales_data = st.session_state.data_processor.process_sales_data(pd.concat(sales_dfs, ignore_index=True) if sales_dfs else pd.DataFrame())
        st.session_state.returns_data = st.session_state.data_processor.process_returns_data(pd.concat(returns_dfs, ignore_index=True) if returns_dfs else pd.DataFrame())
        st.session_state.analysis_results = run_full_analysis(
            st.session_state.sales_data, st.session_state.returns_data,
            (st.session_state.end_date - st.session_state.start_date).days,
            st.session_state.unit_cost, st.session_state.sales_price
        )
    st.success("Analysis complete!")
    st.session_state.ai_file_analyses, st.session_state.user_file_selections = [], {}

# --- Main App Flow ---
def main():
    load_css()
    initialize_session_state()
    initialize_components()
    display_header()
    display_sidebar()

    tab_titles = ["📊 Dashboard", "📝 CAPA", "🛡️ Risk & Safety", "✉️ Vendor Comms", "⚖️ Compliance", "📄 Exports"]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        display_dashboard()
        display_ai_chat_interface("Dashboard")
    with tabs[1]:
        display_capa_form()
        display_ai_chat_interface("CAPA")
    with tabs[2]:
        display_risk_safety_tab()
        display_ai_chat_interface("Risk & Safety")
    with tabs[3]:
        display_vendor_comm_tab()
        display_ai_chat_interface("Vendor Comms")
    with tabs[4]:
        display_compliance_tab()
        display_ai_chat_interface("Compliance")
    with tabs[5]:
        display_exports_tab()

if __name__ == "__main__":
    main()
