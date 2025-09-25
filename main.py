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
from src.capa_form import display_capa_form

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
        'logged_in': False, 'workflow_mode': None
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

def display_dashboard():
    st.header("Quality Dashboard")
    if not st.session_state.analysis_results:
        st.info('Welcome! Configure your product and add data in the sidebar to begin.')
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
    
    st.subheader("AI Insights")
    st.markdown(f"{results.get('insights', 'N/A')}")

def display_risk_safety_tab():
    st.header("Risk & Safety Analysis Hub")
    if st.session_state.api_key_missing:
        st.error("AI features are disabled. Please configure your API key.")
        return

    # --- Tool 1: FMEA ---
    with st.container(border=True):
        st.subheader("Failure Mode and Effects Analysis (FMEA)")
        with st.expander("What is an FMEA?"):
            st.markdown("""
            An FMEA is a proactive method to evaluate a process for potential failures and their impacts. Use this tool to identify and prioritize risks based on Severity, Occurrence, and Detection.
            - **Severity (S):** Impact of the failure (1=Low, 5=High).
            - **Occurrence (O):** Likelihood of the failure (1=Low, 5=High).
            - **Detection (D):** How likely you are to detect the failure (1=High, 5=Low).
            **RPN = S × O × D**. Higher RPNs are higher priorities.
            """)

        c1, c2 = st.columns(2)
        if c1.button("Suggest Failure Modes with AI", width='stretch', key="fmea_ai"):
            if st.session_state.analysis_results:
                with st.spinner("AI is suggesting failure modes..."):
                    insights = st.session_state.analysis_results.get('insights', 'High return rate observed.')
                    suggestions = st.session_state.fmea_generator.suggest_failure_modes(insights, st.session_state.analysis_results)
                    df = pd.DataFrame(suggestions)
                    # Ensure score columns exist with default values
                    for col in ['Severity', 'Occurrence', 'Detection']:
                        if col not in df.columns:
                            df[col] = 1
                    st.session_state.fmea_data = df
            else:
                st.warning("Run an analysis on the dashboard first.")
        
        if c2.button("Add Manual FMEA Row", width='stretch', key="fmea_add"):
            new_row = pd.DataFrame([{"Potential Failure Mode": "", "Potential Effect(s)": "", "Severity": 1, "Potential Cause(s)": "", "Occurrence": 1, "Current Controls": "", "Detection": 1, "RPN": 1}])
            st.session_state.fmea_data = pd.concat([st.session_state.fmea_data, new_row], ignore_index=True)

        if not st.session_state.fmea_data.empty:
            edited_df = st.data_editor(st.session_state.fmea_data, column_config={
                    "Severity": st.column_config.SelectboxColumn("S", options=list(range(1, 6)), required=True),
                    "Occurrence": st.column_config.SelectboxColumn("O", options=list(range(1, 6)), required=True),
                    "Detection": st.column_config.SelectboxColumn("D", options=list(range(1, 6)), required=True),
                }, num_rows="dynamic", key="fmea_editor")
            
            edited_df['RPN'] = (
                pd.to_numeric(edited_df['Severity'], errors='coerce').fillna(1) *
                pd.to_numeric(edited_df['Occurrence'], errors='coerce').fillna(1) *
                pd.to_numeric(edited_df['Detection'], errors='coerce').fillna(1)
            ).astype(int)
            st.session_state.fmea_data = edited_df
    
    st.write("") 
    
    # --- Tool 2: ISO 14971 Risk Assessment ---
    with st.container(border=True):
        st.subheader("ISO 14971 Risk Assessment Generator")
        with st.form("risk_assessment_form"):
            st.info("Generates a formal risk assessment for a medical device according to ISO 14971.")
            ra_product_name = st.text_input("Product Name", st.session_state.target_sku)
            ra_product_desc = st.text_area("Product Description & Intended Use", height=100)
            if st.form_submit_button("Generate Risk Assessment", type="primary", width='stretch'):
                if ra_product_name and ra_product_desc:
                    with st.spinner("AI is generating the ISO 14971 assessment..."):
                        st.session_state.risk_assessment = st.session_state.risk_assessment_generator.generate_assessment(ra_product_name, st.session_state.target_sku, ra_product_desc)
                else:
                    st.warning("Please provide a product name and description.")
        
        if st.session_state.get('risk_assessment'):
            st.markdown(st.session_state.risk_assessment)

    st.write("") 

    # --- Tool 3: Use-Related Risk Analysis (URRA) ---
    with st.container(border=True):
        st.subheader("Use-Related Risk Analysis (URRA) Generator")
        with st.form("urra_form"):
            st.info("Generates a URRA based on IEC 62366 to identify risks associated with product usability.")
            urra_product_name = st.text_input("Product Name", st.session_state.target_sku, key="urra_name")
            urra_product_desc = st.text_area("Product Description & Intended Use", height=100, key="urra_desc")
            urra_user = st.text_input("Intended User Profile", placeholder="e.g., Elderly individuals with limited dexterity")
            urra_env = st.text_input("Intended Use Environment", placeholder="e.g., Home healthcare setting")
            if st.form_submit_button("Generate URRA", type="primary", width='stretch'):
                if urra_product_name and urra_product_desc and urra_user and urra_env:
                    with st.spinner("AI is generating the URRA..."):
                        st.session_state.urra = st.session_state.urra_generator.generate_urra(urra_product_name, urra_product_desc, urra_user, urra_env)
                else:
                    st.warning("Please fill in all fields to generate the URRA.")

        if st.session_state.get('urra'):
            st.markdown(st.session_state.urra)

def display_vendor_comm_tab():
    st.header("Vendor Communications Center")
    if st.session_state.api_key_missing: st.error("AI features are disabled."); return
    if not st.session_state.analysis_results: st.info("Run an analysis on the Dashboard tab first to activate this feature."); return
    
    with st.form("vendor_email_form"):
        st.subheader("Draft a Vendor Email with AI")
        c1, c2 = st.columns(2)
        vendor_name = c1.text_input("Vendor Name")
        contact_name = c2.text_input("Contact Name")
        english_ability = st.slider("Recipient's English Proficiency", 1, 5, 3, help="1: Low, 5: High")
        
        if st.form_submit_button("Draft Email", type="primary", width='stretch'):
            with st.spinner("AI is drafting email..."):
                goal = f"Start a collaborative investigation into the recent return rate for SKU {st.session_state.target_sku}."
                st.session_state.vendor_email_draft = st.session_state.ai_email_drafter.draft_vendor_email(
                    goal, st.session_state.analysis_results, st.session_state.target_sku,
                    vendor_name, contact_name, english_ability)
    
    if st.session_state.vendor_email_draft:
        st.text_area("Generated Draft", st.session_state.vendor_email_draft, height=300)
        if st.button("Generate Formal SCAR Document"):
            with st.spinner("Generating SCAR document..."):
                st.download_button("Download SCAR (.docx)", 
                    st.session_state.doc_generator.generate_scar_docx(st.session_state.capa_data, vendor_name),
                    f"SCAR_{st.session_state.target_sku}_{date.today()}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

def display_compliance_tab():
    st.header("Compliance Center")
    if st.session_state.api_key_missing: st.error("AI features are disabled."); return

    col1, col2 = st.columns(2)
    with col1, st.container(border=True):
        st.subheader("Medical Device Classification")
        with st.form("classification_form"):
            device_desc = st.text_area("Device's intended use:", height=150, placeholder="e.g., A foam cushion for comfort in a wheelchair.")
            if st.form_submit_button("Classify Device", type="primary", width='stretch'):
                if device_desc:
                    with st.spinner("AI is classifying..."):
                        st.session_state.medical_device_classification = st.session_state.medical_device_classifier.classify_device(device_desc)
                else:
                    st.warning("Please describe the device.")
        if st.session_state.get('medical_device_classification'):
            res = st.session_state.medical_device_classification
            if "error" in res: st.error(res['error'])
            else:
                st.success(f"**Classification:** {res.get('classification', 'N/A')}")
                st.markdown(f"**Rationale:** {res.get('rationale', 'N/A')}")
    
    with col2, st.container(border=True):
        st.subheader("Pre-Mortem Analysis")
        scenario = st.text_input("Define failure scenario:", "Our new product launch failed.")
        if st.button("Generate Pre-Mortem Questions", width='stretch'):
            with st.spinner("AI is generating questions..."):
                st.session_state.pre_mortem_questions = st.session_state.pre_mortem_generator.generate_questions(scenario)
        
        if st.session_state.get('pre_mortem_questions'):
            answers = {q: st.text_area(q, key=q, label_visibility="collapsed") for q in st.session_state.pre_mortem_questions}
            if st.button("Summarize Pre-Mortem Analysis", width='stretch'):
                qa_list = [{"question": q, "answer": a} for q, a in answers.items() if a]
                if qa_list:
                    with st.spinner("AI is summarizing..."):
                        st.session_state.pre_mortem_summary = st.session_state.pre_mortem_generator.summarize_answers(qa_list)
                else:
                    st.warning("Please answer at least one question.")
        
        if st.session_state.get('pre_mortem_summary'):
            st.markdown(st.session_state.pre_mortem_summary)

def display_cost_of_quality_tab():
    st.header("Cost of Quality (CoQ) Calculator")
    st.info("Estimate the total cost of quality, broken down into prevention, appraisal, and failure costs.")

    with st.form("coq_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Prevention Costs")
            quality_planning = st.number_input("Quality Planning ($)", 0.0, step=100.0)
            training = st.number_input("Quality Training ($)", 0.0, step=100.0)
            st.subheader("Failure Costs")
            scrap_rework = st.number_input("Internal Failures ($)", 0.0, step=100.0)
            returns_warranty = st.number_input("External Failures ($)", 0.0, step=100.0)
        with c2:
            st.subheader("Appraisal Costs")
            inspection = st.number_input("Inspection & Testing ($)", 0.0, step=100.0)
            audits = st.number_input("Quality Audits ($)", 0.0, step=100.0)

        if st.form_submit_button("Calculate Cost of Quality", type="primary", width='stretch'):
            total_prevention = quality_planning + training
            total_appraisal = inspection + audits
            total_failure = scrap_rework + returns_warranty
            st.session_state.coq_results = {
                "Prevention Costs": total_prevention, "Appraisal Costs": total_appraisal,
                "Failure Costs": total_failure, "Total Cost of Quality": total_prevention + total_appraisal + total_failure
            }

    if st.session_state.get('coq_results'):
        results = st.session_state.coq_results
        st.subheader("Cost of Quality Results")
        st.metric("Total Cost of Quality", f"${results['Total Cost of Quality']:,.2f}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Prevention Costs", f"${results['Prevention Costs']:,.2f}")
        c2.metric("Appraisal Costs", f"${results['Appraisal Costs']:,.2f}")
        c3.metric("Failure Costs", f"${results['Failure Costs']:,.2f}")
        if results['Total Cost of Quality'] > 0:
            st.progress(results['Failure Costs'] / results['Total Cost of Quality'], text=f"{(results['Failure Costs']/results['Total Cost of Quality']):.1%} Failure Costs")
        if st.button("Get AI Insights on CoQ", width='stretch'):
            with st.spinner("AI is analyzing..."):
                st.markdown(st.session_state.ai_context_helper.generate_response(f"Analyze this CoQ data: {results}. Give advice on shifting spending from failure to prevention."))

def display_exports_tab():
    st.header("Document Exports")
    st.info("Generate a single, comprehensive project summary document.")
    
    export_options = st.multiselect(
        "Select sections to include in the final report:",
        ["CAPA Form", "FMEA", "ISO 14971 Assessment", "URRA", "Vendor Email Draft"],
        default=["CAPA Form", "FMEA"]
    )

    if st.button("Generate Project Summary Report (.docx)", type="primary", width='stretch'):
        if not st.session_state.capa_data.get('issue_description') and "CAPA Form" in export_options:
            st.warning("Please fill out the CAPA form before generating a report that includes it.")
        else:
            with st.spinner("Generating comprehensive report..."):
                doc_buffer = st.session_state.doc_generator.generate_summary_docx(st.session_state, export_options)
                st.download_button(
                    "Download Project Summary", doc_buffer,
                    f"Project_Summary_{st.session_state.target_sku}_{date.today()}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

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

    tabs = st.tabs(["Dashboard", "CAPA", "Risk & Safety", "Vendor Comms", "Compliance", "Cost of Quality", "Exports"])
    with tabs[0]: display_dashboard()
    with tabs[1]: display_capa_form()
    with tabs[2]: display_risk_safety_tab()
    with tabs[3]: display_vendor_comm_tab()
    with tabs[4]: display_compliance_tab()
    with tabs[5]: display_cost_of_quality_tab()
    with tabs[6]: display_exports_tab()
    
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
