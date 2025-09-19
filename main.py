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
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
def initialize_session_state():
    """Initializes all required session state variables."""
    defaults = {
        'analysis_results': None,
        'capa_data': {},
        'misc_data': [],
        'file_parser': None,
        'data_processor': None,
        'sales_data': {}, # Now a dict to hold data by channel
        'returns_data': {}, # Now a dict
        'ai_analysis': None,
        'unit_price': None,
        'generated_doc': None,
        'doc_filename': None,
        'ai_suggestions': {},
        'fmea_data': None,
        'pre_mortem_data': None,
        'vendor_email_draft': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- AI and Component Initialization ---
def initialize_components():
    """Initialize all AI-powered components and helpers."""
    if 'anthropic_api_key' not in st.session_state:
        st.session_state.anthropic_api_key = st.secrets.get("ANTHROPIC_API_KEY")

    api_key = st.session_state.anthropic_api_key
    if not api_key:
        st.info("Anthropic API key not configured. AI features will be limited.")
        st.session_state.file_parser = AIFileParser(None)
        st.session_state.data_processor = DataProcessor(None)
        return

    try:
        if st.session_state.file_parser is None:
            st.session_state.file_parser = AIFileParser(api_key)
        if st.session_state.data_processor is None:
            st.session_state.data_processor = DataProcessor(api_key)
    except Exception as e:
        st.warning(f"AI features unavailable: {str(e)}. Using standard parsing.")
        st.session_state.file_parser = AIFileParser(None)
        st.session_state.data_processor = DataProcessor(None)

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
            "Report Period (Days)",
            min_value=1,
            value=30,
            help="Time period for the analysis.",
            key='sidebar_period'
        )

        st.markdown("---")
        st.header("📁 File Upload")
        st.markdown(
            "Upload all relevant files for the target SKU. The AI will identify and process them."
        )

        uploaded_files = st.file_uploader(
            "Sales, Returns, Inspection Sheets, VOC Screenshots, etc.",
            accept_multiple_files=True,
            type=['csv', 'xlsx', 'xls', 'txt', 'pdf', 'png', 'jpg', 'jpeg'],
            help="Upload all relevant files. The system will categorize them automatically."
        )

        if st.button("🚀 Process All Files", type="primary", use_container_width=True):
            if not st.session_state.target_sku:
                st.warning("⚠️ Please enter a target SKU.")
            elif not uploaded_files:
                st.warning("⚠️ Please upload at least one file.")
            else:
                process_all_files(uploaded_files, st.session_state.target_sku, st.session_state.report_period_days)

def process_all_files(files, target_sku, report_period_days):
    """Process all uploaded files, categorize by channel, and run analysis."""
    progress_bar = st.progress(0, text="Initializing...")
    file_parser = st.session_state.file_parser

    # Reset data
    st.session_state.sales_data = {}
    st.session_state.returns_data = {}
    st.session_state.misc_data = []

    for i, file in enumerate(files):
        progress_bar.progress((i + 1) / len(files), text=f"Analyzing {file.name}...")
        try:
            analysis = file_parser.analyze_file_structure(file, target_sku)
            content_type = analysis.get('content_type', 'other')
            channel = analysis.get('channel', 'general') # e.g., fba, fbm, b2b

            data_df = file_parser.extract_data(file, analysis, target_sku)

            if data_df is not None:
                if 'sales' in content_type:
                    if channel not in st.session_state.sales_data:
                        st.session_state.sales_data[channel] = []
                    st.session_state.sales_data[channel].append(data_df)
                    st.success(f"Processed {channel.upper()} Sales Data: {file.name}")
                elif 'returns' in content_type:
                    if channel not in st.session_state.returns_data:
                        st.session_state.returns_data[channel] = []
                    st.session_state.returns_data[channel].append(data_df)
                    st.success(f"Processed {channel.upper()} Returns Data: {file.name}")
                else:
                    st.session_state.misc_data.append(analysis)
                    st.info(f"Processed supplementary file: {file.name}")
            else:
                 st.session_state.misc_data.append(analysis)
                 st.info(f"Processed supplementary file: {file.name} (Type: {analysis.get('content_type', 'Unknown')})")

        except Exception as e:
            st.error(f"Could not process {file.name}: {str(e)}")

    progress_bar.progress(1.0, text="Aggregating data...")

    # Consolidate data for each channel
    for channel, df_list in st.session_state.sales_data.items():
        st.session_state.sales_data[channel] = pd.concat(df_list, ignore_index=True)
    for channel, df_list in st.session_state.returns_data.items():
        st.session_state.returns_data[channel] = pd.concat(df_list, ignore_index=True)

    progress_bar.progress(1.0, text="Running final analysis...")
    if st.session_state.sales_data and st.session_state.returns_data:
        st.session_state.analysis_results = run_full_analysis(
            st.session_state.sales_data,
            st.session_state.returns_data,
            report_period_days,
            st.session_state.unit_price
        )
        st.markdown(
            f'<div class="success-box">✅ Successfully analyzed data for SKU: <strong>{target_sku}</strong></div>',
            unsafe_allow_html=True
        )
    else:
        st.error("Could not find both sales and returns data. Please check your files.")
    
    progress_bar.empty()


def display_dashboard():
    st.header("📊 Quality Dashboard")
    if not st.session_state.analysis_results:
        st.markdown(
            '<div class="info-box">👆 Upload and process files using the sidebar to view the dashboard.</div>',
            unsafe_allow_html=True
        )
        return

    results = st.session_state.analysis_results
    summary = results.get('overall_summary')

    if summary is None or summary.empty:
        st.warning("Analysis did not produce a valid summary.")
        return

    summary_data = summary.iloc[0]
    st.markdown(f"### Overall Analysis for SKU: **{summary_data['sku']}**")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Return Rate", f"{summary_data['return_rate']:.2f}%")
    col2.metric("Total Units Sold", f"{int(summary_data['total_sold']):,}")
    col3.metric("Total Units Returned", f"{int(summary_data['total_returned']):,}")
    
    quality_metrics = results.get('quality_metrics', {})
    col4.metric("Quality Score", f"{quality_metrics.get('quality_score', 'N/A')}/100", delta=quality_metrics.get('risk_level', ''))
    
    # Per-channel breakdown
    st.markdown("---")
    st.subheader("📈 Channel Performance Breakdown")
    channel_summary = results.get('channel_summary')
    if channel_summary:
        num_channels = len(channel_summary)
        cols = st.columns(num_channels)
        for i, (channel, data) in enumerate(channel_summary.items()):
            with cols[i]:
                st.markdown(f"#### {channel.upper()}")
                st.metric("Return Rate", f"{data.get('return_rate', 0):.2f}%")
                st.metric("Units Sold", f"{int(data.get('total_sold', 0)):,}")
                st.metric("Units Returned", f"{int(data.get('total_returned', 0)):,}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔍 AI-Generated Insights")
        st.markdown(results.get('insights', 'No insights generated.'))

    with col2:
        st.subheader("📄 Supplementary Data")
        if st.session_state.misc_data:
            for item in st.session_state.misc_data:
                with st.expander(f"{item.get('filename', 'Unknown File')} - (Type: {item.get('content_type', 'Misc')})"):
                    st.json(item)
        else:
            st.info("No supplementary files were processed.")


def display_fmea_tab():
    st.header("🔬 Failure Mode and Effects Analysis (FMEA)")
    if not st.session_state.analysis_results:
        st.markdown(
            '<div class="info-box">👆 Process data first to enable FMEA analysis.</div>',
            unsafe_allow_html=True
        )
        return
        
    fmea = FMEA(st.session_state.anthropic_api_key)
    
    if 'fmea_data' not in st.session_state or st.session_state.fmea_data is None:
        st.session_state.fmea_data = pd.DataFrame(columns=["Potential Failure Mode", "Potential Effect(s)", "Severity", "Potential Cause(s)", "Occurrence", "Current Controls", "Detection", "RPN"])

    issue_description = st.text_area("Describe the issue or potential failure to analyze:", height=100, key="fmea_issue_desc")

    if st.button("🤖 Suggest Failure Modes with AI"):
        if issue_description:
            with st.spinner("AI is thinking..."):
                suggestions = fmea.suggest_failure_modes(issue_description, st.session_state.analysis_results)
                new_rows = pd.DataFrame(suggestions)
                # Ensure all columns exist before concatenating
                for col in st.session_state.fmea_data.columns:
                    if col not in new_rows.columns:
                        new_rows[col] = '' # or some default value
                st.session_state.fmea_data = pd.concat([st.session_state.fmea_data, new_rows], ignore_index=True)
                st.success("AI suggestions added to the table below.")
        else:
            st.warning("Please describe the issue first.")
            
    st.subheader("FMEA Table")
    edited_df = st.data_editor(
        st.session_state.fmea_data,
        num_rows="dynamic",
        column_config={
            "Severity": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "Occurrence": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "Detection": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "RPN": st.column_config.NumberColumn(disabled=True)
        },
        key="fmea_editor"
    )
    
    # Calculate RPN
    edited_df['RPN'] = pd.to_numeric(edited_df['Severity'], errors='coerce').fillna(1) * \
                      pd.to_numeric(edited_df['Occurrence'], errors='coerce').fillna(1) * \
                      pd.to_numeric(edited_df['Detection'], errors='coerce').fillna(1)

    st.session_state.fmea_data = edited_df
    
    st.metric("Highest Risk Priority Number (RPN)", edited_df['RPN'].max())
    st.dataframe(edited_df.sort_values(by="RPN", ascending=False))


def display_pre_mortem_tab():
    st.header("🔮 Proactive Pre-Mortem Analysis")
    st.markdown(
        "Identify potential problems *before* they occur. Imagine the product has failed and work backward to figure out why."
    )
    
    pre_mortem = PreMortem(st.session_state.anthropic_api_key)
    
    if 'pre_mortem_data' not in st.session_state:
        st.session_state.pre_mortem_data = []

    scenario = st.text_input(
        "Define the 'failure' scenario:",
        "e.g., A new version of our product is launched and receives overwhelmingly negative reviews.",
        key="pre_mortem_scenario"
    )

    if st.button("🧠 Generate AI Questions"):
        with st.spinner("Generating guiding questions..."):
            questions = pre_mortem.generate_questions(scenario)
            for q in questions:
                st.session_state.pre_mortem_data.append({"question": q, "answer": ""})
            st.success("Questions generated below. Please provide your team's answers.")

    if st.session_state.pre_mortem_data:
        for i, item in enumerate(st.session_state.pre_mortem_data):
            st.markdown(f"**{i+1}. {item['question']}**")
            st.session_state.pre_mortem_data[i]['answer'] = st.text_area("Your Answer:", key=f"pm_answer_{i}", value=item['answer'], height=100)
    
    if st.session_state.pre_mortem_data and st.button("✅ Finalize Pre-Mortem Analysis"):
        with st.spinner("AI is summarizing the results..."):
            summary = pre_mortem.summarize_answers(st.session_state.pre_mortem_data)
            st.subheader("Pre-Mortem Summary")
            st.markdown(summary)
            st.session_state.pre_mortem_summary = summary


def display_vendor_comm_tab():
    st.header("✉️ AI Vendor Communication")
    if not st.session_state.analysis_results:
        st.markdown(
            '<div class="info-box">👆 Process data first to draft vendor communications.</div>',
            unsafe_allow_html=True
        )
        return
    
    drafter = AIEmailDrafter(st.session_state.anthropic_api_key)

    goal = st.text_area(
        "What is the primary goal of this email?",
        "e.g., Inform the vendor of the high return rate and ask for their initial thoughts on potential causes from the manufacturing side.",
        height=100,
        key="email_goal"
    )
    
    if st.button("✍️ Draft Conservative Email", type="primary"):
        if goal:
            with st.spinner("Drafting email..."):
                st.session_state.vendor_email_draft = drafter.draft_vendor_email(
                    goal,
                    st.session_state.analysis_results,
                    st.session_state.target_sku
                )
        else:
            st.warning("Please specify the goal of the email.")

    if st.session_state.vendor_email_draft:
        st.subheader("Draft Email to Vendor")
        st.markdown(st.session_state.vendor_email_draft)
        st.code(st.session_state.vendor_email_draft, language=None)
        st.info("You can now copy the text above and edit it before sending.")


def display_exports_tab():
    st.header("📄 Documents & Exports")
    st.markdown("Generate formal documents or export data for logging and further analysis.")
    
    if not st.session_state.analysis_results:
        st.markdown('<div class="info-box">👆 Process data first to enable exports.</div>', unsafe_allow_html=True)
        return

    doc_gen = CapaDocumentGenerator(st.session_state.anthropic_api_key)

    st.subheader("Export for Manual Logging")
    st.markdown(
        "Click the button below to download a single-row Excel file with the key metrics from this analysis. "
        "You can then copy and paste this row into your master tracking spreadsheet to maintain data continuity."
    )
    
    if st.button("📦 Export Analysis Row for Logging"):
        summary_df = st.session_state.analysis_results['overall_summary']
        if not summary_df.empty:
            log_data = summary_df.iloc[[0]].copy() # Select first row as a DataFrame
            log_data['analysis_date'] = datetime.now().strftime('%Y-%m-%d')
            
            # Reorder columns for clarity
            log_data = log_data[['analysis_date', 'sku', 'total_sold', 'total_returned', 'return_rate', 'quality_status']]

            buffer = BytesIO()
            log_data.to_excel(buffer, index=False, engine='openpyxl')
            buffer.seek(0)
            
            st.download_button(
                label="📥 Download Log Row (.xlsx)",
                data=buffer,
                file_name=f"LogRow_{st.session_state.target_sku}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.markdown("---")
    st.subheader("Generate Formal Documents")
    
    doc_type = st.selectbox("Select document type to generate:", ["CAPA Report", "FMEA Report", "Pre-Mortem Summary"])

    if st.button(f"📄 Generate {doc_type}", type="primary"):
        buffer = None
        filename = ""
        with st.spinner(f"Generating {doc_type}..."):
            if doc_type == "CAPA Report":
                # A simplified CAPA data dict for this example
                capa_data = {
                    'capa_number': f"CAPA-{datetime.now().strftime('%Y%m%d')}-001",
                    'product': st.session_state.target_sku,
                    'sku': st.session_state.target_sku,
                    'prepared_by': "Quality Team",
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'severity': st.session_state.analysis_results['quality_metrics'].get('risk_level', 'Medium')
                }
                content = doc_gen.generate_ai_structured_content(capa_data, st.session_state.analysis_results)
                buffer = doc_gen.export_to_docx(capa_data, content)
                filename = f"CAPA_{st.session_state.target_sku}.docx"

            elif doc_type == "FMEA Report":
                if st.session_state.fmea_data is not None and not st.session_state.fmea_data.empty:
                    buffer = doc_gen.export_fmea_to_excel(st.session_state.fmea_data, st.session_state.target_sku)
                    filename = f"FMEA_{st.session_state.target_sku}.xlsx"
                else:
                    st.warning("No FMEA data available to export.")

            elif doc_type == "Pre-Mortem Summary":
                if 'pre_mortem_summary' in st.session_state:
                    summary = st.session_state.pre_mortem_summary
                    buffer = doc_gen.export_text_to_docx(summary, f"Pre-Mortem Summary for {st.session_state.target_sku}")
                    filename = f"PreMortem_{st.session_state.target_sku}.docx"
                else:
                    st.warning("No Pre-Mortem summary available to export.")

        if buffer:
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if filename.endswith('.xlsx') else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            st.download_button(
                label=f"📥 Download {doc_type}",
                data=buffer,
                file_name=filename,
                mime=mime_type
            )


# --- Main Application Flow ---
def main():
    initialize_session_state()
    display_header()
    initialize_components()
    display_sidebar()

    tabs = st.tabs([
        "📊 Dashboard",
        "🔬 FMEA",
        "🔮 Pre-Mortem",
        "✉️ Vendor Comms",
        "📄 Exports"
    ])

    with tabs[0]:
        display_dashboard()

    with tabs[1]:
        display_fmea_tab()

    with tabs[2]:
        display_pre_mortem_tab()

    with tabs[3]:
        display_vendor_comm_tab()

    with tabs[4]:
        display_exports_tab()

if __name__ == "__main__":
    main()
