# main.py

import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import json
import os
from typing import Dict, Optional, Any

# Import custom modules
from src.parsers import AIFileParser
from src.data_processing import DataProcessor
from src.analysis import run_full_analysis
from src.compliance import validate_capa_data
from src.document_generator import CapaDocumentGenerator
from src.ai_capa_helper import AICAPAHelper, AIEmailDrafter
from src.fmea import FMEA
from src.pre_mortem import PreMortem
from src.fba_returns_processor import ReturnsProcessor
from src.ai_context_helper import AIContextHelper

# --- Page Configuration and Styling ---
st.set_page_config(page_title="Product Lifecycle Manager", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .main-header {
        background-color: #00466B;
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 30px;
    }
    .stMetric {
        background-color: #F0F2F6;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #E0E0E0;
    }
    .stButton>button {
        width: 100%;
    }
    .info-box {
        background-color: #E3F2FD;
        border-left: 5px solid #1E88E5;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .success-box {
        background-color: #E8F5E9;
        border-left: 5px solid #43A047;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .error-box {
        background-color: #FFEBEE;
        border-left: 5px solid #E53935;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .chat-container {
        margin-top: 2rem;
        border-top: 2px solid #F0F2F6;
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
def initialize_session_state():
    """Initializes all required session state variables."""
    defaults = {
        'analysis_results': None, 'capa_data': {}, 'misc_data': [],
        'file_parser': None, 'data_processor': None,
        'sales_data': {}, 'returns_data': {},
        'ai_analysis': None, 'unit_price': None,
        'generated_doc': None, 'doc_filename': None,
        'ai_suggestions': {}, 'fmea_data': None,
        'pre_mortem_data': None, 'pre_mortem_summary': None,
        'vendor_email_draft': None, 'pending_image_confirmations': [],
        'chat_history': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- AI and Component Initialization ---
def initialize_components():
    """Initialize all AI-powered components and helpers."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    st.session_state.anthropic_api_key = api_key

    if not api_key:
        st.info("Anthropic API key not configured. AI features will be limited.")
    
    st.session_state.file_parser = AIFileParser(api_key)
    st.session_state.data_processor = DataProcessor(api_key)
    st.session_state.ai_context_helper = AIContextHelper(api_key)


# --- UI Sections ---

def display_header():
    st.markdown(
        '<div class="main-header">'
        '<h1>📈 Product Lifecycle & Quality Manager</h1>'
        '<p>Your AI-powered hub for proactive quality assurance and vendor management.</p>'
        '</div>',
        unsafe_allow_html=True
    )

def display_sidebar():
    with st.sidebar:
        st.header("⚙️ Controls & Data Input")

        st.session_state.target_sku = st.text_input(
            "Enter Target SKU*",
            help="Enter the exact SKU to analyze across all uploaded documents.",
            placeholder="e.g., ABC123-001",
            key='sidebar_sku'
        )

        st.session_state.unit_price = st.number_input(
            "Product Unit Price ($)",
            min_value=0.0,
            value=st.session_state.get('unit_price', 0.0),
            help="Used for financial impact calculations.",
            format="%.2f",
            key='sidebar_price'
        )

        st.session_state.report_period_days = st.number_input(
            "Report Period (Days)", min_value=1, value=30,
            help="Time period for the analysis.", key='sidebar_period'
        )

        st.markdown("---")
        st.header("📁 File Upload")
        uploaded_files = st.file_uploader(
            "Sales, Returns, Inspection Sheets, VOC Screenshots, etc.",
            accept_multiple_files=True,
            type=['csv', 'xlsx', 'xls', 'txt', 'pdf', 'png', 'jpg', 'jpeg']
        )

        if st.button("🚀 Process All Files", type="primary", use_container_width=True):
            if not st.session_state.target_sku:
                st.warning("⚠️ Please enter a target SKU.")
            elif not uploaded_files:
                st.warning("⚠️ Please upload at least one file.")
            else:
                process_all_files(uploaded_files, st.session_state.target_sku)

        st.markdown("---")
        with st.expander("✍️ Or Enter Data Manually"):
            manual_sales = st.number_input("Total Units Sold", min_value=0, step=1, key="manual_sales")
            manual_returns = st.number_input("Total Units Returned", min_value=0, step=1, key="manual_returns")
            
            if st.button("📈 Process Manual Data", use_container_width=True, key="process_manual"):
                if not st.session_state.target_sku:
                    st.warning("⚠️ Please enter a target SKU first.")
                elif manual_sales <= 0:
                    st.warning("⚠️ 'Total Units Sold' must be greater than zero.")
                else:
                    process_manual_data(st.session_state.target_sku, manual_sales, manual_returns)


def trigger_final_analysis():
    """Consolidates all data and runs the final analysis."""
    with st.spinner("Aggregating data and running final analysis..."):
        # Consolidate data for each channel
        for channel, df_list in st.session_state.sales_data.items():
            if df_list:
                st.session_state.sales_data[channel] = pd.concat(df_list, ignore_index=True)
        for channel, df_list in st.session_state.returns_data.items():
            if df_list:
                st.session_state.returns_data[channel] = pd.concat(df_list, ignore_index=True)
        
        st.session_state.analysis_results = None 
        if st.session_state.sales_data:
            st.session_state.analysis_results = run_full_analysis(
                st.session_state.sales_data,
                st.session_state.returns_data,
                st.session_state.report_period_days,
                st.session_state.unit_price
            )
            st.success(f"Successfully analyzed all data for SKU: {st.session_state.target_sku}")
            st.balloons()
        else:
            st.error("Could not find sufficient sales data to run an analysis.")


def process_all_files(files, target_sku):
    """Process all uploaded files, queuing images for user confirmation."""
    st.session_state.sales_data, st.session_state.returns_data, st.session_state.misc_data = {}, {}, []
    st.session_state.pending_image_confirmations, st.session_state.analysis_results = [], None
    
    file_parser = st.session_state.file_parser
    image_files = [f for f in files if f.type.startswith('image/')]
    other_files = [f for f in files if not f.type.startswith('image/')]

    with st.spinner("Processing files..."):
        for file in other_files:
            try:
                analysis = file_parser.analyze_file_structure(file, target_sku)
                data_df = file_parser.extract_data(file, analysis, target_sku)
                if data_df is not None:
                    if 'sales' in analysis.get('content_type', ''):
                        st.session_state.sales_data.setdefault('general', []).append(data_df)
                    elif 'returns' in analysis.get('content_type', ''):
                        st.session_state.returns_data.setdefault('general', []).append(data_df)
                else: st.session_state.misc_data.append(analysis)
            except Exception as e: st.error(f"Error processing {file.name}: {e}")

        for file in image_files:
            try:
                analysis = file_parser.analyze_file_structure(file, target_sku)
                if analysis.get('content_type') in ['sales', 'returns']:
                    analysis['file_id'], file.seek(0)
                    analysis['file_bytes'], analysis['filename'] = f"{file.name}-{os.urandom(4).hex()}", file.read(), file.name
                    st.session_state.pending_image_confirmations.append(analysis)
                else: st.session_state.misc_data.append(analysis)
            except Exception as e: st.error(f"Error analyzing image {file.name}: {e}")

    if not st.session_state.pending_image_confirmations and (st.session_state.sales_data or st.session_state.returns_data):
        trigger_final_analysis()
    elif st.session_state.pending_image_confirmations:
        st.info("Action required: Please review extracted image data on the Dashboard.")


def process_manual_data(target_sku, total_sold, total_returned):
    """Processes manually entered data and runs analysis."""
    st.session_state.sales_data, st.session_state.returns_data, st.session_state.misc_data = {}, {}, []
    st.session_state.pending_image_confirmations, st.session_state.analysis_results = [], None

    st.session_state.sales_data['manual'] = [pd.DataFrame([{'sku': target_sku, 'quantity': total_sold}])]
    st.session_state.returns_data['manual'] = [pd.DataFrame([{'sku': target_sku, 'quantity': total_returned}])] if total_returned > 0 else []
    
    trigger_final_analysis()

def display_ai_chat_interface(tab_name: str):
    """Displays the contextual AI chat interface."""
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    st.subheader("🤖 AI Assistant")
    st.markdown("Ask a question about the data across any of the tabs.")

    for author, message in st.session_state.chat_history:
        with st.chat_message(author):
            st.markdown(message)
    
    prompt = st.chat_input(f"Ask AI about {tab_name}...")
    if prompt:
        st.session_state.chat_history.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)
        
        response = st.session_state.ai_context_helper.generate_response(prompt)
        st.session_state.chat_history.append(("assistant", response))
        with st.chat_message("assistant"):
            st.markdown(response)
    
    st.markdown("</div>", unsafe_allow_html=True)


def display_dashboard():
    if st.session_state.get('pending_image_confirmations'):
        st.header("🖼️ Image Data Confirmation")
        st.info("Our AI has extracted data from your images. Please review, correct if needed, and confirm.")
        
        for analysis in st.session_state.pending_image_confirmations[:]:
            with st.form(key=f"image_confirm_{analysis['file_id']}"):
                st.image(analysis['file_bytes'], width=300, caption=analysis['filename'])
                key_data = analysis.get('key_data', {})
                
                content_type = st.selectbox("Detected Content Type", ['sales', 'returns', 'other'], index=['sales', 'returns', 'other'].index(analysis.get('content_type', 'other')), key=f"type_{analysis['file_id']}")
                quantity = st.number_input("Detected Quantity", min_value=0, value=int(key_data.get('total_quantity', 0)), step=1, key=f"qty_{analysis['file_id']}")
                
                if st.form_submit_button("✅ Confirm and Add Data"):
                    if content_type in ['sales', 'returns']:
                        df = pd.DataFrame([{'sku': st.session_state.target_sku, 'quantity': quantity}])
                        (st.session_state.sales_data if content_type == 'sales' else st.session_state.returns_data).setdefault('image_uploads', []).append(df)
                    st.session_state.pending_image_confirmations.remove(analysis)
                    st.rerun()
        st.markdown("---")

    if not st.session_state.pending_image_confirmations and (st.session_state.sales_data or st.session_state.returns_data) and not st.session_state.analysis_results:
         if st.button("🚀 Run Final Analysis on All Data", type="primary", use_container_width=True):
             trigger_final_analysis()

    st.header("📊 Quality Dashboard")
    if not st.session_state.analysis_results:
        st.info('👆 Upload files or enter data manually to view the dashboard.')
        return

    results = st.session_state.analysis_results
    summary = results.get('overall_summary')
    if summary is None or summary.empty:
        st.warning("Analysis did not produce a valid summary.")
        return

    summary_data = summary.iloc[0]
    st.markdown(f"### Overall Analysis for SKU: **{summary_data['sku']}**")
    cols = st.columns(4)
    cols[0].metric("Return Rate", f"{summary_data['return_rate']:.2f}%")
    cols[1].metric("Total Sold", f"{int(summary_data['total_sold']):,}")
    cols[2].metric("Total Returned", f"{int(summary_data['total_returned']):,}")
    cols[3].metric("Quality Score", f"{results['quality_metrics'].get('quality_score', 'N/A')}/100", delta=results['quality_metrics'].get('risk_level', ''))
    
    display_ai_chat_interface("the Dashboard")

def display_fmea_tab():
    st.header("🔬 Failure Mode and Effects Analysis (FMEA)")
    if not st.session_state.analysis_results:
        st.info('👆 Process data first to enable FMEA analysis.')
        return
        
    fmea = FMEA(st.session_state.anthropic_api_key)
    
    if 'fmea_data' not in st.session_state or st.session_state.fmea_data is None:
        st.session_state.fmea_data = pd.DataFrame(columns=["Potential Failure Mode", "Potential Effect(s)", "Severity", "Potential Cause(s)", "Occurrence", "Current Controls", "Detection", "RPN"])

    with st.expander("✍️ Manually Add Failure Mode"):
        with st.form("manual_fmea_entry", clear_on_submit=True):
            mode = st.text_input("Potential Failure Mode")
            effect = st.text_input("Potential Effect(s)")
            cause = st.text_input("Potential Cause(s)")
            if st.form_submit_button("Add Entry"):
                new_row = pd.DataFrame([{"Potential Failure Mode": mode, "Potential Effect(s)": effect, "Potential Cause(s)": cause}])
                st.session_state.fmea_data = pd.concat([st.session_state.fmea_data, new_row], ignore_index=True)
                st.success("Manual entry added.")

    issue_description = st.text_area("Or, describe an issue for AI to analyze:", height=100, key="fmea_issue_desc")
    if st.button("🤖 Suggest Failure Modes with AI"):
        if issue_description:
            suggestions = fmea.suggest_failure_modes(issue_description, st.session_state.analysis_results)
            st.session_state.fmea_data = pd.concat([st.session_state.fmea_data, pd.DataFrame(suggestions)], ignore_index=True)
            st.success("AI suggestions added.")
        else: st.warning("Please describe the issue first.")
            
    st.subheader("FMEA Table")
    edited_df = st.data_editor(
        st.session_state.fmea_data, num_rows="dynamic", key="fmea_editor",
        column_config={
            "Severity": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "Occurrence": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "Detection": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "RPN": st.column_config.NumberColumn(disabled=True)
        }
    )
    
    edited_df['RPN'] = pd.to_numeric(edited_df['Severity'], 'coerce').fillna(1) * pd.to_numeric(edited_df['Occurrence'], 'coerce').fillna(1) * pd.to_numeric(edited_df['Detection'], 'coerce').fillna(1)
    st.session_state.fmea_data = edited_df
    
    st.metric("Highest Risk Priority Number (RPN)", edited_df['RPN'].max() if not edited_df.empty else 0)
    
    display_ai_chat_interface("FMEA")


def display_pre_mortem_tab():
    st.header("🔮 Proactive Pre-Mortem Analysis")
    pre_mortem = PreMortem(st.session_state.anthropic_api_key)
    
    if 'pre_mortem_data' not in st.session_state:
        st.session_state.pre_mortem_data = []

    scenario = st.text_input(
        "Define the 'failure' scenario:",
        "e.g., A new version of our product is launched and receives overwhelmingly negative reviews.",
        key="pre_mortem_scenario"
    )

    if st.button("🧠 Generate AI Questions"):
        questions = pre_mortem.generate_questions(scenario)
        st.session_state.pre_mortem_data = [{"question": q, "answer": ""} for q in questions]

    if st.session_state.pre_mortem_data:
        for i, item in enumerate(st.session_state.pre_mortem_data):
            st.markdown(f"**{i+1}. {item['question']}**")
            item['answer'] = st.text_area("Your Answer:", key=f"pm_answer_{i}", value=item['answer'], height=100)
    
    if st.session_state.pre_mortem_data and st.button("✅ Summarize Pre-Mortem Analysis"):
        st.session_state.pre_mortem_summary = pre_mortem.summarize_answers(st.session_state.pre_mortem_data)
        st.subheader("Pre-Mortem Summary")
        st.markdown(st.session_state.pre_mortem_summary)

    display_ai_chat_interface("Pre-Mortem Analysis")


def display_vendor_comm_tab():
    st.header("✉️ AI Vendor Communication")
    if not st.session_state.analysis_results:
        st.info('👆 Process data first to draft vendor communications.')
        return
    
    drafter = AIEmailDrafter(st.session_state.anthropic_api_key)
    goal = st.text_area(
        "What is the primary goal of this email?",
        "e.g., Inform the vendor of the high return rate and ask for their initial thoughts on potential causes from the manufacturing side.",
        height=100, key="email_goal"
    )
    
    if st.button("✍️ Draft Conservative Email", type="primary"):
        if goal:
            st.session_state.vendor_email_draft = drafter.draft_vendor_email(
                goal, st.session_state.analysis_results, st.session_state.target_sku
            )
        else: st.warning("Please specify the goal of the email.")

    if st.session_state.vendor_email_draft:
        st.subheader("Draft Email to Vendor")
        st.code(st.session_state.vendor_email_draft, language=None)
    
    display_ai_chat_interface("Vendor Communications")


def display_exports_tab():
    st.header("📄 Documents & Exports")
    st.markdown("Generate formal documents or export data for logging and further analysis.")
    
    doc_gen = CapaDocumentGenerator(st.session_state.anthropic_api_key)
    
    doc_type = st.selectbox("Select document type to generate:", ["CAPA Report", "FMEA Report", "Pre-Mortem Summary"])

    if st.button(f"📄 Generate {doc_type}", type="primary"):
        buffer, filename = None, ""
        with st.spinner(f"Generating {doc_type}..."):
            if doc_type == "CAPA Report" and st.session_state.analysis_results:
                capa_data = {'capa_number': f"CAPA-{datetime.now().strftime('%Y%m%d')}-001", 'product': st.session_state.target_sku}
                content = doc_gen.generate_ai_structured_content(capa_data, st.session_state.analysis_results)
                buffer = doc_gen.export_to_docx(capa_data, content)
                filename = f"CAPA_{st.session_state.target_sku}.docx"
            elif doc_type == "FMEA Report" and st.session_state.fmea_data is not None:
                buffer = doc_gen.export_fmea_to_excel(st.session_state.fmea_data, st.session_state.target_sku)
                filename = f"FMEA_{st.session_state.target_sku}.xlsx"
            elif doc_type == "Pre-Mortem Summary" and st.session_state.pre_mortem_summary:
                buffer = doc_gen.export_text_to_docx(st.session_state.pre_mortem_summary, f"Pre-Mortem Summary for {st.session_state.target_sku}")
                filename = f"PreMortem_{st.session_state.target_sku}.docx"
            else: st.warning(f"No data available to generate {doc_type}.")

        if buffer:
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if filename.endswith('.xlsx') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            st.download_button(label=f"📥 Download {doc_type}", data=buffer, file_name=filename, mime=mime)


# --- Main Application Flow ---
def main():
    initialize_session_state()
    display_header()
    initialize_components()
    display_sidebar()

    tabs = st.tabs(["📊 Dashboard", "🔬 FMEA", "🔮 Pre-Mortem", "✉️ Vendor Comms", "📄 Exports"])

    with tabs[0]: display_dashboard()
    with tabs[1]: display_fmea_tab()
    with tabs[2]: display_pre_mortem_tab()
    with tabs[3]: display_vendor_comm_tab()
    with tabs[4]: display_exports_tab()

if __name__ == "__main__":
    main()

