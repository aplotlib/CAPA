# main.py

import streamlit as st
import pandas as pd
from datetime import datetime, date
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
from src.ai_capa_helper import AICAPAHelper, AIEmailDrafter, MedicalDeviceClassifier, RiskAssessmentGenerator
from src.fmea import FMEA
from src.pre_mortem import PreMortem
from src.fba_returns_processor import ReturnsProcessor
from src.ai_context_helper import AIContextHelper

# --- Page Configuration and Styling ---
st.set_page_config(page_title="Product Lifecycle Manager", page_icon="📈", layout="wide")

st.markdown("""
<style>
    body {
        font-family: 'Inter', sans-serif;
    }
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
    div, p, span, th, td {
        word-wrap: break-word;
        overflow-wrap: break-word;
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
        'ai_analysis': None, 'unit_cost': 0.0, 'sales_price': 0.0, 'target_sku': "",
        'start_date': datetime.now().date() - pd.Timedelta(days=30),
        'end_date': datetime.now().date(),
        'manual_sales': 0, 'manual_returns': 0,
        'generated_doc': None, 'doc_filename': None,
        'ai_suggestions': {}, 'fmea_data': None,
        'pre_mortem_data': [], 'pre_mortem_summary': None,
        'vendor_email_draft': None, 'pending_image_confirmations': [],
        'chat_history': {},
        'capa_feasibility_analysis': None,
        'medical_device_classification': None,
        'risk_assessment_report': None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- AI and Component Initialization ---
def initialize_components():
    """Initialize all AI-powered components and helpers."""
    if 'components_initialized' not in st.session_state:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
        st.session_state.anthropic_api_key = api_key

        if not api_key:
            st.info("Anthropic API key not configured. AI features will be limited.")

        st.session_state.file_parser = AIFileParser(api_key)
        st.session_state.data_processor = DataProcessor(api_key)
        st.session_state.ai_context_helper = AIContextHelper(api_key)
        st.session_state.medical_device_classifier = MedicalDeviceClassifier(api_key)
        st.session_state.risk_assessment_generator = RiskAssessmentGenerator(api_key)
        st.session_state.components_initialized = True


# --- UI Sections ---

def display_header():
    st.markdown(
        '<div class="main-header">'
        '<h1>📈 Product Lifecycle & Quality Manager</h1>'
        '<p>Your AI-powered hub for proactive quality assurance and vendor management.</p>'
        '</div>',
        unsafe_allow_html=True
    )

def get_serializable_state() -> str:
    """Creates a JSON-serializable representation of the session state."""
    # Create a deep copy to avoid modifying the live session state
    state_copy = copy.deepcopy(st.session_state)
    
    serializable_state = {}
    
    for k, v in state_copy.items():
        # Handle DataFrames
        if isinstance(v, pd.DataFrame):
            serializable_state[k] = v.to_json(orient='split')
        # Handle dictionaries that might contain DataFrames
        elif isinstance(v, dict):
            # Check for 'analysis_results' specifically
            if k == 'analysis_results' and v and 'return_summary' in v and isinstance(v.get('return_summary'), pd.DataFrame):
                v['return_summary'] = v['return_summary'].to_json(orient='split')
            
            # Check sales/returns data
            if k in ['sales_data', 'returns_data']:
                for source, df_list in v.items():
                    if isinstance(df_list, list):
                        v[source] = [df.to_json(orient='split') if isinstance(df, pd.DataFrame) else df for df in df_list]

            serializable_state[k] = v
        # Handle date/datetime objects
        elif isinstance(v, (datetime, date)):
            serializable_state[k] = v.isoformat()
        # Handle other JSON-serializable types
        elif isinstance(v, (list, str, int, float, bool, type(None))):
            serializable_state[k] = v
        # Skip non-serializable objects like modules or functions
        else:
            continue
            
    return json.dumps(serializable_state, indent=2)

def load_state_from_json(uploaded_file):
    """Loads session state from an uploaded JSON file."""
    try:
        loaded_state = json.load(uploaded_file)
        for key, value in loaded_state.items():
            if key == 'fmea_data' and isinstance(value, str):
                st.session_state[key] = pd.read_json(value, orient='split')
            elif key == 'analysis_results' and isinstance(value, dict) and 'return_summary' in value and isinstance(value.get('return_summary'), str):
                value['return_summary'] = pd.read_json(value['return_summary'], orient='split')
                st.session_state[key] = value
            elif key in ['sales_data', 'returns_data'] and isinstance(value, dict):
                st.session_state[key] = {
                    source: [pd.read_json(df_json, orient='split') for df_json in df_list]
                    for source, df_list in value.items()
                }
            elif key in ['start_date', 'end_date'] and isinstance(value, str):
                 st.session_state[key] = date.fromisoformat(value)
            else:
                 # Check if the key exists before assigning, to avoid adding new keys from old session files
                if key in st.session_state:
                    st.session_state[key] = value
        st.success("Session loaded successfully!")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Failed to load session: {e}")


def display_sidebar():
    with st.sidebar:
        st.header("💾 Session Management")
        
        st.download_button(
            label="📤 Export/Save Session",
            data=get_serializable_state(),
            file_name=f"capa_session_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
        
        uploaded_state = st.file_uploader("📥 Import Session", type="json")
        if uploaded_state is not None:
            load_state_from_json(uploaded_state)

        st.markdown("---")
        st.header("⚙️ Controls & Data Input")

        st.session_state.target_sku = st.text_input(
            "Enter Target SKU*",
            value=st.session_state.get('target_sku', ''),
            help="Enter the exact SKU to analyze across all uploaded documents."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.unit_cost = st.number_input(
                "Unit Cost ($)",
                min_value=0.0,
                value=st.session_state.get('unit_cost', 0.0),
                help="The cost you pay your vendor for one unit.",
                format="%.2f"
            )
        with col2:
             st.session_state.sales_price = st.number_input(
                "Sales Price ($)",
                min_value=0.0,
                value=st.session_state.get('sales_price', 0.0),
                help="The price the customer pays for one unit.",
                format="%.2f"
            )

        st.subheader("🗓️ Analysis Date Range")
        st.session_state.start_date = st.date_input("Start Date", value=st.session_state.start_date)
        st.session_state.end_date = st.date_input("End Date", value=st.session_state.end_date)
        
        st.subheader("✍️ Manual Data Entry")
        st.session_state.manual_sales = st.number_input("Total Units Sold", min_value=0, step=1, value=st.session_state.manual_sales)
        st.session_state.manual_returns = st.number_input("Total Units Returned", min_value=0, step=1, value=st.session_state.manual_returns)
        
        if st.button("📈 Process Manual Data", use_container_width=True, type="primary"):
            if not st.session_state.target_sku:
                st.warning("⚠️ Please enter a target SKU first.")
            elif st.session_state.manual_sales <= 0:
                st.warning("⚠️ 'Total Units Sold' must be greater than zero.")
            else:
                with st.spinner("Processing manual data..."):
                    process_manual_data(st.session_state.target_sku, st.session_state.manual_sales, st.session_state.manual_returns)

        st.markdown("---")
        with st.expander("📁 Upload Data Files (Optional)"):
            uploaded_files = st.file_uploader(
                "Upload Sales, Returns, Inspection Sheets, VOC Screenshots, etc.",
                accept_multiple_files=True,
                type=['csv', 'xlsx', 'xls', 'txt', 'png', 'jpg', 'jpeg']
            )

            if st.button("🚀 Process Uploaded Files", use_container_width=True):
                if not st.session_state.target_sku:
                    st.warning("⚠️ Please enter a target SKU.")
                elif not uploaded_files:
                    st.warning("⚠️ Please upload at least one file.")
                else:
                    process_all_files(uploaded_files, st.session_state.target_sku)


def trigger_final_analysis():
    """Consolidates all data and runs the final analysis."""
    with st.spinner("Aggregating data and running final analysis..."):
        all_sales_df = pd.DataFrame()
        if st.session_state.sales_data:
            all_sales_dfs = [df for df_list in st.session_state.sales_data.values() for df in df_list if df is not None and not df.empty]
            if all_sales_dfs:
                all_sales_df = pd.concat(all_sales_dfs, ignore_index=True)

        all_returns_df = pd.DataFrame()
        if st.session_state.returns_data:
            all_returns_dfs = [df for df_list in st.session_state.returns_data.values() for df in df_list if df is not None and not df.empty]
            if all_returns_dfs:
                all_returns_df = pd.concat(all_returns_dfs, ignore_index=True)

        st.session_state.analysis_results = None
        
        report_period_days = (st.session_state.end_date - st.session_state.start_date).days
        if report_period_days <= 0:
            st.error("Error: Start Date must be before End Date.")
            return

        if not all_sales_df.empty:
            st.session_state.analysis_results = run_full_analysis(
                sales_df=all_sales_df,
                returns_df=all_returns_df,
                report_period_days=report_period_days,
                unit_cost=st.session_state.unit_cost,
                sales_price=st.session_state.sales_price
            )
            st.success(f"Successfully analyzed all data for SKU: {st.session_state.target_sku}")
            st.balloons()
        else:
            st.error("Could not find sufficient sales data to run an analysis.")


def process_all_files(files, target_sku):
    """Process all uploaded files, queuing images for user confirmation."""
    st.session_state.misc_data = []
    st.session_state.pending_image_confirmations = []

    file_parser = st.session_state.file_parser

    with st.spinner("Analyzing and processing all uploaded files..."):
        for file in files:
            try:
                analysis = file_parser.analyze_file_structure(file, target_sku)
                
                if analysis.get('content_type') in ['sales', 'returns']:
                    if file.type.startswith('image/'):
                        analysis['file_id'], file.seek(0)
                        analysis['file_bytes'], analysis['filename'] = f"{file.name}-{os.urandom(4).hex()}", file.read(), file.name
                        st.session_state.pending_image_confirmations.append(analysis)
                    else:
                        data_df = file_parser.extract_data(file, analysis, target_sku)
                        if data_df is not None:
                            if 'sales' in analysis.get('content_type', ''):
                                st.session_state.sales_data.setdefault('file_uploads', []).append(data_df)
                            elif 'returns' in analysis.get('content_type', ''):
                                st.session_state.returns_data.setdefault('file_uploads', []).append(data_df)
                else: 
                    st.session_state.misc_data.append(analysis)
            except Exception as e: st.error(f"Error processing {file.name}: {e}")

    if not st.session_state.pending_image_confirmations and (st.session_state.sales_data or st.session_state.returns_data):
        trigger_final_analysis()
    elif st.session_state.pending_image_confirmations:
        st.info("Action required: Please review extracted image data on the Dashboard.")
    else:
        st.warning("No sales or return data could be extracted from the uploaded files.")


def process_manual_data(target_sku, total_sold, total_returned):
    """Processes manually entered data and runs analysis."""
    st.session_state.sales_data['manual'] = [pd.DataFrame([{'sku': target_sku, 'quantity': total_sold}])]
    if total_returned > 0:
        st.session_state.returns_data['manual'] = [pd.DataFrame([{'sku': target_sku, 'quantity': total_returned}])]
    else:
        st.session_state.returns_data['manual'] = []
        
    trigger_final_analysis()

def display_ai_chat_interface(tab_name: str):
    """Displays the contextual AI chat interface."""
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    st.subheader("🤖 AI Assistant")
    st.markdown("Ask a question about the data across any of the tabs.")

    if tab_name not in st.session_state.chat_history:
        st.session_state.chat_history[tab_name] = []

    for author, message in st.session_state.chat_history[tab_name]:
        with st.chat_message(author):
            st.markdown(message)

    prompt = st.chat_input(f"Ask AI about {tab_name}...")
    if prompt:
        st.session_state.chat_history[tab_name].append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("AI is thinking..."):
            response = st.session_state.ai_context_helper.generate_response(prompt)
        st.session_state.chat_history[tab_name].append(("assistant", response))
        with st.chat_message("assistant"):
            st.markdown(response)

    st.markdown("</div>", unsafe_allow_html=True)


def display_dashboard():
    st.info(
        "**Instructions:** Start here. Enter your product's SKU, cost/price, and date range in the sidebar. "
        "You can then enter sales/returns data manually or upload files for the AI to parse. "
        "Once processed, this dashboard will show the high-level quality metrics."
    )
    if st.session_state.get('pending_image_confirmations'):
        st.header("🖼️ Image Data Confirmation")
        st.info("Our AI has extracted data from your images. Please review, correct if needed, and confirm.")

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
        st.markdown('👆 **Enter data in the sidebar to view the dashboard.**')
        return

    results = st.session_state.analysis_results
    summary = results.get('return_summary')
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
    
    st.markdown(results.get('insights', ''))

    st.markdown("---")
    st.subheader("💡 Cost-Benefit Analysis for Potential Fix")
    st.info("Use this tool to project the financial impact of a proposed quality improvement.")

    with st.form("cost_benefit_form"):
        col1, col2 = st.columns(2)
        with col1:
            cost_change = st.number_input("Cost increase per unit ($)", min_value=0.0, step=0.01, format="%.2f", help="How much will the proposed fix add to the unit cost?")
        with col2:
            expected_rr_reduction = st.number_input("Expected return rate reduction (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", help="How much do you expect the return rate to drop by?")
        
        submitted = st.form_submit_button("Calculate Financial Impact", use_container_width=True, type="primary")

        if submitted:
            if st.session_state.unit_cost > 0:
                report_period_days = (st.session_state.end_date - st.session_state.start_date).days
                with st.spinner("Calculating cost-benefit..."):
                    cost_benefit_results = calculate_cost_benefit(
                        analysis_results=st.session_state.analysis_results,
                        current_unit_cost=st.session_state.unit_cost,
                        cost_change=cost_change,
                        expected_rr_reduction=expected_rr_reduction,
                        report_period_days=report_period_days
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

def display_fmea_tab():
    st.header("🔬 Failure Mode and Effects Analysis (FMEA)")
    st.info(
        "**Instructions:**\n"
        "1.  **Add Failure Modes**: Manually enter a failure mode or describe an issue for the AI to suggest modes.\n"
        "2.  **Enter S/O/D Ratings**: Click on the `Severity`, `Occurrence`, and `Detection` cells in the table to enter a rating from 1 (best) to 10 (worst).\n"
        "3.  **Review RPN**: The Risk Priority Number (RPN) is calculated automatically (`S x O x D`). The highest RPNs represent the highest risks."
    )

    fmea = FMEA(st.session_state.anthropic_api_key)

    if 'fmea_data' not in st.session_state or st.session_state.fmea_data is None:
        st.session_state.fmea_data = pd.DataFrame(columns=["Potential Failure Mode", "Potential Effect(s)", "Severity", "Potential Cause(s)", "Occurrence", "Current Controls", "Detection", "RPN"])

    with st.expander("✍️ Add Failure Mode"):
        with st.container():
            with st.form("manual_fmea_entry", clear_on_submit=True):
                mode = st.text_input("Potential Failure Mode")
                effect = st.text_input("Potential Effect(s)")
                cause = st.text_input("Potential Cause(s)")
                controls = st.text_input("Current Controls")
                if st.form_submit_button("Add Entry", type="primary"):
                    new_row = pd.DataFrame([{"Potential Failure Mode": mode, "Potential Effect(s)": effect, "Potential Cause(s)": cause, "Current Controls": controls}])
                    st.session_state.fmea_data = pd.concat([st.session_state.fmea_data, new_row], ignore_index=True)
                    st.success("Manual entry added.")

    with st.expander("🤖 Suggest Failure Modes with AI"):
        with st.container():
            issue_description = st.text_area("Describe an issue for AI to analyze:", height=100, key="fmea_issue_desc", help="Provide a general issue or use data from the dashboard for more specific suggestions.")
            if st.button("Suggest Failure Modes"):
                if issue_description:
                    with st.spinner("AI is analyzing potential failure modes..."):
                        # Pass analysis_results if available, otherwise None.
                        suggestions = fmea.suggest_failure_modes(issue_description, st.session_state.analysis_results)
                    st.session_state.fmea_data = pd.concat([st.session_state.fmea_data, pd.DataFrame(suggestions)], ignore_index=True)
                    st.success("AI suggestions added.")
                else:
                    st.warning("Please describe the issue first.")

    st.subheader("FMEA Table")
    if 'fmea_data' in st.session_state and st.session_state.fmea_data is not None:
        edited_df = st.data_editor(
            st.session_state.fmea_data, num_rows="dynamic", key="fmea_editor", height=400,
            column_config={
                "Severity": st.column_config.NumberColumn(min_value=1, max_value=10, step=1, required=True),
                "Occurrence": st.column_config.NumberColumn(min_value=1, max_value=10, step=1, required=True),
                "Detection": st.column_config.NumberColumn(min_value=1, max_value=10, step=1, required=True),
                "RPN": st.column_config.NumberColumn(disabled=True, help="Severity x Occurrence x Detection")
            }
        )
        
        for col in ['Severity', 'Occurrence', 'Detection']:
            edited_df[col] = pd.to_numeric(edited_df[col], errors='coerce')
        
        edited_df.fillna({'Severity': 1, 'Occurrence': 1, 'Detection': 1}, inplace=True)
        
        edited_df['RPN'] = edited_df['Severity'] * edited_df['Occurrence'] * edited_df['Detection']
        st.session_state.fmea_data = edited_df

        st.metric("Highest Risk Priority Number (RPN)", int(edited_df['RPN'].max()) if not edited_df.empty else 0)

    display_ai_chat_interface("FMEA")


def display_risk_assessment_tab():
    st.header("🛡️ Risk Assessment (ISO 14971 / IEC 62366)")
    st.info(
        "**Instructions:** Generate a formal risk assessment for your Design History File (DHF).\n"
        "1.  **Enter Product Details**: Provide a name and a detailed description of the product and its intended use.\n"
        "2.  **Select Assessment Type**: Choose the standard to assess against (ISO 14971 for general device risk, IEC 62366 for use-related risk, or both).\n"
        "3.  **Generate & Review**: The AI will generate a structured risk table. Review it for accuracy and completeness.\n"
        "4.  **Export**: Copy the content or download the file for your records."
    )

    with st.form("risk_assessment_form"):
        product_name = st.text_input("Product Name", placeholder="e.g., Smart Temperature Monitor")
        product_description = st.text_area(
            "Product Description (include intended use, user profile, and key features)",
            height=150,
            placeholder="e.g., A wireless, wearable patch that continuously monitors body temperature for infants. It connects via Bluetooth to a mobile app..."
        )
        assessment_type = st.radio(
            "Select Assessment Type",
            ["ISO 14971 (Standard Risk Assessment)", "IEC 62366 (Use-Related Risk Analysis)", "Both"],
            horizontal=True
        )
        submitted = st.form_submit_button("🤖 Generate Risk Assessment", type="primary", use_container_width=True)

        if submitted:
            if not product_name or not product_description or not st.session_state.target_sku:
                st.warning("Please enter a Target SKU (in the sidebar), Product Name, and Product Description.")
            else:
                with st.spinner("AI is conducting a comprehensive risk assessment..."):
                    st.session_state.risk_assessment_report = st.session_state.risk_assessment_generator.generate_assessment(
                        product_name,
                        st.session_state.target_sku,
                        product_description,
                        assessment_type
                    )

    if st.session_state.risk_assessment_report:
        st.markdown("---")
        st.subheader("Generated Risk Assessment Report")
        
        report_text = st.session_state.risk_assessment_report
        st.markdown(report_text, unsafe_allow_html=True) # Allow HTML for better table rendering if needed
        
        st.text_area("Copyable Report Text", report_text, height=200, key="risk_report_copy_text")
        
        doc_gen = CapaDocumentGenerator(st.session_state.anthropic_api_key)
        docx_bytes = doc_gen.export_text_to_docx(report_text, "Risk Assessment Report")
        st.download_button("Download as Word (.docx)", docx_bytes, f"Risk_Assessment_{st.session_state.target_sku}.docx")

    display_ai_chat_interface("Risk Assessment")


def display_pre_mortem_tab():
    st.header("🔮 Proactive Pre-Mortem Analysis")
    st.info(
        "**Instructions:** This tool helps you anticipate failures before they happen.\n"
        "1.  **Define Failure**: Imagine your project or product has failed. Write down what that failure looks like.\n"
        "2.  **Generate Questions**: Click the button to get AI-generated questions that will probe potential causes for this failure.\n"
        "3.  **Brainstorm Answers**: Answer the questions with your team.\n"
        "4.  **Summarize**: The AI will then summarize your answers into a risk report."
    )

    pre_mortem = PreMortem(st.session_state.anthropic_api_key)

    scenario = st.text_area(
        "Define the 'failure' scenario:",
        "e.g., A new version of our product is launched and receives overwhelmingly negative reviews, leading to a product recall.",
        key="pre_mortem_scenario"
    )

    if st.button("🧠 Generate AI Questions"):
        if not scenario:
            st.warning("Please define the failure scenario first.")
        else:
            with st.spinner("Generating thought-provoking questions..."):
                questions = pre_mortem.generate_questions(scenario)
                st.session_state.pre_mortem_data = [{"question": q, "answer": ""} for q in questions]

    if st.session_state.pre_mortem_data:
        st.subheader("Brainstorming Session")
        for i, item in enumerate(st.session_state.pre_mortem_data):
            st.markdown(f"**{i+1}. {item['question']}**")
            item['answer'] = st.text_area("Your Answer:", key=f"pm_answer_{i}", value=item.get('answer', ''), height=100)

    if st.session_state.pre_mortem_data and st.button("✅ Summarize Pre-Mortem Analysis", type="primary"):
        with st.spinner("AI is synthesizing the pre-mortem discussion..."):
            st.session_state.pre_mortem_summary = pre_mortem.summarize_answers(st.session_state.pre_mortem_data)
    
    if st.session_state.pre_mortem_summary:
        st.subheader("Pre-Mortem Summary")
        st.markdown(st.session_state.pre_mortem_summary)

    display_ai_chat_interface("Pre-Mortem Analysis")


def display_vendor_comm_tab():
    st.header("✉️ AI Vendor Communication")
    st.info(
        "**Instructions:** This tool drafts professional, collaborative emails to your vendors.\n"
        "1.  **Enter Details**: Provide the vendor and contact person's name.\n"
        "2.  **Set Context**: Describe the goal of the email and rate the recipient's English fluency.\n"
        "3.  **Draft**: The AI will generate an email draft. If you've processed data on the dashboard, it will be included for context."
    )

    drafter = AIEmailDrafter(st.session_state.anthropic_api_key)
    
    col1, col2 = st.columns(2)
    with col1:
        vendor_name = st.text_input("Vendor Company Name")
    with col2:
        contact_name = st.text_input("Point of Contact Name")
        
    english_ability = st.slider("Recipient's English Ability (1=Limited, 5=Fluent)", 1, 5, 2, help="The AI will adjust the language complexity. For limited English, it will use simple terms, ideal for translation.")

    goal = st.text_area(
        "What is the primary goal of this email?",
        "e.g., Inform the vendor of the high return rate and ask for their initial thoughts on potential causes from the manufacturing side.",
        height=100, key="email_goal"
    )

    if st.button("✍️ Draft Collaborative Email", type="primary"):
        if goal and vendor_name and contact_name:
            with st.spinner("AI is drafting a professional email..."):
                # Pass analysis_results if available, otherwise an empty dict
                analysis_context = st.session_state.analysis_results or {}
                st.session_state.vendor_email_draft = drafter.draft_vendor_email(
                    goal, analysis_context, st.session_state.target_sku,
                    vendor_name, contact_name, english_ability
                )
        else:
            st.warning("Please fill in all vendor and goal fields.")

    if st.session_state.vendor_email_draft:
        st.subheader("Draft Email to Vendor")
        st.text_area("Email Draft", st.session_state.vendor_email_draft, height=400)

    display_ai_chat_interface("Vendor Communications")

def display_compliance_tab():
    st.header("⚖️ Compliance & Device Classification")
    st.info(
        "**Instructions:** Get an AI-powered preliminary classification for your medical device based on FDA guidelines.\n"
        "1.  **Describe Your Device**: Enter a detailed description of the device, including its intended use and mechanism of action.\n"
        "2.  **Classify**: The AI will analyze the description and provide a suggested FDA classification (Class I, II, or III) with a detailed rationale."
    )
    
    st.subheader("Medical Device Classification (U.S. FDA)")
    
    device_description = st.text_area(
        "Enter a detailed description of the medical device:",
        height=200,
        placeholder="Example: A non-sterile, handheld electronic device intended to measure an adult's body temperature by detecting infrared energy from the forehead..."
    )
    
    if st.button("Classify Device", type="primary"):
        if device_description:
            with st.spinner("AI is analyzing FDA regulations..."):
                st.session_state.medical_device_classification = st.session_state.medical_device_classifier.classify_device(device_description)
        else:
            st.warning("Please provide a device description.")
            
    if st.session_state.medical_device_classification:
        st.subheader("AI Classification Analysis")
        result = st.session_state.medical_device_classification
        if "error" in result:
            st.error(result["error"])
        else:
            st.success(f"**Suggested Classification:** {result.get('classification', 'N/A')}")
            
            with st.expander("Rationale", expanded=True):
                st.markdown(result.get('rationale', 'No rationale provided.'))
            
            with st.expander("Primary Risks"):
                st.markdown(result.get('risks', 'No risks identified.'))
                
            with st.expander("General Regulatory Requirements"):
                st.markdown(result.get('regulatory_requirements', 'No requirements provided.'))


def display_exports_tab():
    st.header("📄 Documents & Exports")
    st.info(
        "**Instructions:** Generate formal documents from your analysis.\n"
        "1.  **Select Content**: Choose which sections of your analysis you want to include.\n"
        "2.  **Choose Format**: Select whether to combine them into one file or download them separately.\n"
        "3.  **Generate**: Download your formatted documents."
    )

    doc_gen = CapaDocumentGenerator(st.session_state.anthropic_api_key)

    available_docs = []
    if st.session_state.analysis_results: available_docs.append("Dashboard & CAPA Insights")
    if st.session_state.fmea_data is not None and not st.session_state.fmea_data.empty: available_docs.append("FMEA Data")
    if st.session_state.risk_assessment_report: available_docs.append("Risk Assessment Report")
    if st.session_state.pre_mortem_summary: available_docs.append("Pre-Mortem Summary")
    if st.session_state.vendor_email_draft: available_docs.append("Vendor Email Draft")
    
    if not available_docs:
        st.warning("No data available to export. Complete some analysis on other tabs first.")
        return

    doc_types = st.multiselect(
        "Select document sections to generate:",
        available_docs,
        default=available_docs
    )

    export_format = st.radio("Export Format", ("Separate Files", "All in One Document"), horizontal=True)

    if st.button(f"📄 Generate Documents", type="primary"):
        with st.spinner("Generating documents..."):
            if export_format == "Separate Files":
                if "Dashboard & CAPA Insights" in doc_types and st.session_state.analysis_results:
                    docx_bytes = doc_gen.export_text_to_docx(st.session_state.analysis_results['insights'], "CAPA Insights Report")
                    st.download_button("Download CAPA Insights (.docx)", docx_bytes, f"CAPA_Insights_{st.session_state.target_sku}.docx", key="dl_capa")
                if "FMEA Data" in doc_types and st.session_state.fmea_data is not None:
                    excel_bytes = doc_gen.export_fmea_to_excel(st.session_state.fmea_data, st.session_state.target_sku)
                    st.download_button("Download FMEA (.xlsx)", excel_bytes, f"FMEA_{st.session_state.target_sku}.xlsx", key="dl_fmea")
                if "Risk Assessment Report" in doc_types and st.session_state.risk_assessment_report:
                    docx_bytes = doc_gen.export_text_to_docx(st.session_state.risk_assessment_report, "Risk Assessment Report")
                    st.download_button("Download Risk Assessment (.docx)", docx_bytes, f"Risk_Assessment_{st.session_state.target_sku}.docx", key="dl_risk")
                if "Pre-Mortem Summary" in doc_types and st.session_state.pre_mortem_summary:
                    docx_bytes = doc_gen.export_text_to_docx(st.session_state.pre_mortem_summary, "Pre-Mortem Summary")
                    st.download_button("Download Pre-Mortem (.docx)", docx_bytes, f"PreMortem_{st.session_state.target_sku}.docx", key="dl_pm")
                if "Vendor Email Draft" in doc_types and st.session_state.vendor_email_draft:
                    docx_bytes = doc_gen.export_text_to_docx(st.session_state.vendor_email_draft, "Vendor Email Draft")
                    st.download_button("Download Vendor Email (.docx)", docx_bytes, f"VendorEmail_{st.session_state.target_sku}.docx", key="dl_email")
            
            else: # All in One Document
                all_content = {
                    "sku": st.session_state.target_sku,
                    "dashboard": st.session_state.analysis_results if "Dashboard & CAPA Insights" in doc_types else None,
                    "fmea": st.session_state.fmea_data if "FMEA Data" in doc_types else None,
                    "risk_assessment": st.session_state.risk_assessment_report if "Risk Assessment Report" in doc_types else None,
                    "pre_mortem": st.session_state.pre_mortem_summary if "Pre-Mortem Summary" in doc_types else None,
                    "vendor_email": st.session_state.vendor_email_draft if "Vendor Email Draft" in doc_types else None,
                }
                docx_bytes = doc_gen.export_all_to_docx(all_content)
                st.download_button("Download Combined Report (.docx)", docx_bytes, f"Combined_Report_{st.session_state.target_sku}.docx", key="dl_combined")
        st.success("Your documents are ready to download below!")


# --- Main Application Flow ---
def main():
    initialize_session_state()
    display_header()
    initialize_components()
    display_sidebar()

    tabs = st.tabs(["📊 Dashboard", "🔬 FMEA", "🛡️ Risk Assessment", "🔮 Pre-Mortem", "✉️ Vendor Comms", "⚖️ Compliance", "📄 Exports"])

    with tabs[0]: display_dashboard()
    with tabs[1]: display_fmea_tab()
    with tabs[2]: display_risk_assessment_tab()
    with tabs[3]: display_pre_mortem_tab()
    with tabs[4]: display_vendor_comm_tab()
    with tabs[5]: display_compliance_tab()
    with tabs[6]: display_exports_tab()

if __name__ == "__main__":
    main()
