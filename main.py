# main.py

import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import json
import os
from typing import Dict, Optional, Any

# Import custom modules
from src.parsers import AIFileParser, parse_file
from src.data_processing import DataProcessor, standardize_sales_data, standardize_returns_data
from src.analysis import run_full_analysis
from src.compliance import validate_capa_data, generate_compliance_checklist, get_regulatory_guidelines
from src.document_generator import CapaDocumentGenerator

# Try to import AI helper, fall back if not available
try:
    from src.ai_capa_helper import AICAPAHelper
except ImportError:
    # If the module doesn't exist yet, create a dummy class
    class AICAPAHelper:
        def __init__(self, api_key=None):
            self.client = None
        def generate_capa_suggestions(self, issue_summary, analysis_results, product_info=None):
            return {}

# --- Page Configuration and Styling ---
st.set_page_config(page_title="Medical Device CAPA Tool", page_icon="🏥", layout="wide")

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
        border-left: 4px solid #1976D2;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }
    .success-box {
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }
    .error-box {
        background-color: #FFEBEE;
        border-left: 4px solid #F44336;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
def initialize_session_state():
    """Initializes all required session state variables."""
    defaults = {
        'analysis_results': None,
        'capa_data': {},
        'misc_df': pd.DataFrame(columns=['filename', 'type', 'size', 'content_type']),
        'file_parser': None,
        'data_processor': None,
        'sales_data': None,
        'returns_data': None,
        'ai_analysis': None,
        'debug_info': {},
        'unit_price': None,
        'manual_entry': False,
        'override_manual': False,
        'generated_doc': None,
        'doc_filename': None,
        'ai_suggestions': {}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- Initialize AI Components ---
def initialize_ai_components():
    """Initialize AI-powered file parser and data processor."""
    if st.session_state.file_parser is None:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if api_key:
            try:
                st.session_state.file_parser = AIFileParser(api_key)
                st.session_state.data_processor = DataProcessor(api_key)
                return True
            except Exception as e:
                st.warning(f"AI features unavailable: {str(e)}. Using standard parsing.")
                st.session_state.file_parser = None
                st.session_state.data_processor = DataProcessor(None)
                return True  # Continue with fallback methods
        else:
            st.info("Anthropic API key not configured. Using standard parsing methods.")
            st.session_state.file_parser = None
            st.session_state.data_processor = DataProcessor(None)
            return True  # Continue with fallback methods
    return True

# --- UI Components ---
def display_header():
    st.markdown(
        '<div class="main-header">'
        '<h1>🏥 Medical Device CAPA Tool</h1>'
        '<p>AI-Powered Quality Management System for Returns Analysis and CAPA Generation</p>'
        '</div>', 
        unsafe_allow_html=True
    )

def display_file_analysis_results():
    """Display the AI's analysis of uploaded files."""
    if st.session_state.ai_analysis:
        with st.expander("📊 AI File Analysis Results", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Sales File Analysis")
                if 'sales' in st.session_state.ai_analysis:
                    analysis = st.session_state.ai_analysis['sales']
                    st.markdown(f"**File Type:** {analysis.get('file_type', 'Unknown')}")
                    st.markdown(f"**Structure:** {analysis.get('structure', 'Unknown')}")
                    if 'columns_found' in analysis:
                        st.markdown("**Columns Found:**")
                        for col in analysis['columns_found']:
                            st.markdown(f"- {col}")
            
            with col2:
                st.markdown("### Returns File Analysis")
                if 'returns' in st.session_state.ai_analysis:
                    analysis = st.session_state.ai_analysis['returns']
                    st.markdown(f"**File Type:** {analysis.get('file_type', 'Unknown')}")
                    st.markdown(f"**Structure:** {analysis.get('structure', 'Unknown')}")
                    st.markdown(f"**Pre-filtered:** {'Yes' if analysis.get('pre_filtered', False) else 'No'}")

def process_files_with_ai(sales_file, returns_file, misc_files, target_sku, report_period_days):
    """Process files using AI to understand their structure first."""
    
    # Initialize progress tracking
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Check if AI is available
        if st.session_state.file_parser is None:
            # Use fallback parsing
            status_text.text("Processing files using standard parsing...")
            progress_bar.progress(50)
            
            # Parse files using original methods
            sales_df = parse_file(sales_file, sales_file.name)
            returns_df = parse_file(returns_file, returns_file.name)
            
            if sales_df is None or sales_df.empty:
                st.error("Could not read the Sales Forecast file.")
                return
                
            # Process with original functions
            sales_data, debug_skus = standardize_sales_data(sales_df, target_sku)
            if sales_data is None:
                st.error(f"SKU '{target_sku}' not found in the Sales file.")
                if debug_skus:
                    st.info("Available SKUs found:")
                    for sku in debug_skus[:10]:
                        st.write(f"- {sku}")
                return
            
            returns_data = standardize_returns_data(returns_df, target_sku)
            if returns_data is None:
                st.error("Could not extract returns data.")
                return
            
            # Store processed data
            st.session_state.sales_data = sales_data
            st.session_state.returns_data = returns_data
            
            # Run analysis
            st.session_state.analysis_results = run_full_analysis(sales_data, returns_data, report_period_days, st.session_state.unit_price)
            progress_bar.progress(100)
            status_text.text("✅ Analysis complete!")
            
            # Process miscellaneous files
            if misc_files:
                misc_data = []
                for file in misc_files:
                    try:
                        misc_info = {
                            'filename': file.name,
                            'type': file.type if hasattr(file, 'type') else 'unknown',
                            'size': file.size if hasattr(file, 'size') else 0,
                            'content_type': 'misc'
                        }
                        misc_data.append(misc_info)
                    except Exception as e:
                        st.warning(f"Could not process {file.name}: {str(e)}")
                
                if misc_data:
                    st.session_state.misc_df = pd.DataFrame(misc_data)
                else:
                    st.session_state.misc_df = pd.DataFrame()
                    
            st.success(f"✅ Analysis complete for SKU: {target_sku}")
            return
        
        # Step 1: Analyze file structures with AI
        status_text.text("🤖 Analyzing file structures with AI...")
        progress_bar.progress(20)
        
        # Analyze sales file
        sales_analysis = st.session_state.file_parser.analyze_file_structure(
            sales_file, 
            "sales_forecast",
            target_sku
        )
        
        # Analyze returns file
        returns_analysis = st.session_state.file_parser.analyze_file_structure(
            returns_file, 
            "returns_pivot",
            target_sku
        )
        
        # Store analysis results
        st.session_state.ai_analysis = {
            'sales': sales_analysis,
            'returns': returns_analysis
        }
        
        # Step 2: Extract data based on AI analysis
        status_text.text("📊 Extracting data based on AI insights...")
        progress_bar.progress(40)
        
        # Extract sales data
        sales_data = st.session_state.file_parser.extract_data_with_ai(
            sales_file,
            sales_analysis,
            target_sku
        )
        
        if sales_data is None or sales_data.empty:
            st.error(f"❌ Could not extract sales data for SKU '{target_sku}'")
            if 'available_skus' in sales_analysis:
                st.info("Available SKUs found in the file:")
                for sku in sales_analysis['available_skus'][:10]:
                    st.write(f"- {sku}")
            return
        
        st.session_state.sales_data = sales_data
        
        # Extract returns data (pre-filtered for the SKU)
        returns_data = st.session_state.file_parser.extract_returns_with_ai(
            returns_file,
            returns_analysis,
            target_sku
        )
        
        if returns_data is None:
            st.error("❌ Could not extract returns data from the pivot report")
            return
            
        st.session_state.returns_data = returns_data
        
        # Step 3: Process and standardize data
        status_text.text("🔧 Processing and standardizing data...")
        progress_bar.progress(60)
        
        processed_sales = st.session_state.data_processor.process_sales_data(
            sales_data, target_sku
        )
        processed_returns = st.session_state.data_processor.process_returns_data(
            returns_data, target_sku
        )
        
        # Step 4: Run analysis
        status_text.text("📈 Running quality analysis...")
        progress_bar.progress(80)
        
        st.session_state.analysis_results = run_full_analysis(
            processed_sales, 
            processed_returns, 
            report_period_days,
            st.session_state.unit_price
        )
        
        # Step 5: Process miscellaneous files if provided
        if misc_files:
            status_text.text("📎 Processing additional files...")
            progress_bar.progress(90)
            
            misc_data = []
            for file in misc_files:
                try:
                    if st.session_state.file_parser:
                        # Use AI file parser if available
                        misc_analysis = st.session_state.file_parser.analyze_misc_file(file)
                    else:
                        # Fallback analysis
                        misc_analysis = {
                            'filename': file.name,
                            'type': file.type,
                            'size': file.size,
                            'content_type': 'misc'
                        }
                    if misc_analysis:
                        misc_data.append(misc_analysis)
                except Exception as e:
                    st.warning(f"Could not process {file.name}: {str(e)}")
            
            if misc_data:
                # Create DataFrame with explicit index
                st.session_state.misc_df = pd.DataFrame(misc_data)
            else:
                st.session_state.misc_df = pd.DataFrame()
        
        # Complete
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        
        # Show success message
        st.markdown(
            f'<div class="success-box">'
            f'✅ Successfully analyzed data for SKU: <strong>{target_sku}</strong>'
            f'</div>',
            unsafe_allow_html=True
        )

def display_manual_entry_form(report_period_days):
    """Display form for manual data entry."""
    st.markdown("#### Manually Enter Data")
    with st.form("manual_data_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            target_sku = st.text_input("Enter SKU for Analysis*", 
                                      help="Enter the exact SKU code")
            sales_units = st.number_input("Enter Total Sales Units for SKU", 
                                         min_value=0,
                                         help="Total units sold in the period")
            return_units = st.number_input("Enter Total Return Units for SKU", 
                                          min_value=0,
                                          help="Total units returned in the period")
        
        with col2:
            unit_price = st.number_input("Product Unit Price (Optional)", 
                                        min_value=0.0,
                                        value=0.0,
                                        help="Enter price for financial impact calculation. Leave as 0 to skip cost estimates.",
                                        format="%.2f")
            
            st.markdown("##### Data Period")
            st.info(f"📅 Analysis period: Last {report_period_days} days")
            
        submitted = st.form_submit_button("Process Manual Data", type="primary")

        if submitted:
            if not target_sku or sales_units <= 0:
                st.warning("⚠️ Please provide an SKU and sales quantity.")
            else:
                # Create simple dataframes
                sales_df = pd.DataFrame([{
                    'sku': target_sku, 
                    'quantity': sales_units,
                    'date': datetime.now()
                }])
                returns_df = pd.DataFrame([{
                    'sku': target_sku, 
                    'quantity': return_units,
                    'date': datetime.now()
                }])
                
                # Store manual entry flag and price
                st.session_state.manual_entry = True
                st.session_state.unit_price = unit_price if unit_price > 0 else None
                
                st.session_state.analysis_results = run_full_analysis(
                    sales_df, returns_df, report_period_days, st.session_state.unit_price
                )
                st.success(f"✅ Manual analysis complete for SKU: {target_sku}")

def calculate_quality_score(return_rate):
    """Calculate quality score appropriate for medical devices."""
    # Medical device industry standards:
    # < 5% return rate: Excellent (90-100 score)
    # 5-10% return rate: Good (70-90 score) - Industry standard
    # 10-15% return rate: Acceptable (50-70 score)
    # 15-20% return rate: Needs Improvement (30-50 score)
    # > 20% return rate: Poor (0-30 score)
    
    if return_rate < 5:
        # Excellent: Linear scale from 90-100
        quality_score = 90 + (5 - return_rate) * 2
    elif return_rate < 10:
        # Good: Linear scale from 70-90
        quality_score = 70 + (10 - return_rate) * 4
    elif return_rate < 15:
        # Acceptable: Linear scale from 50-70
        quality_score = 50 + (15 - return_rate) * 4
    elif return_rate < 20:
        # Needs Improvement: Linear scale from 30-50
        quality_score = 30 + (20 - return_rate) * 4
    else:
        # Poor: Scale from 0-30
        quality_score = max(0, 30 - (return_rate - 20) * 3)
    
    return round(quality_score)

def display_metrics_dashboard(results):
    """Display analysis metrics dashboard."""
    if not results or 'return_summary' not in results or results['return_summary'].empty:
        return
    
    summary = results['return_summary'].iloc[0]
    
    # Main metrics
    st.markdown(f"### Analysis for SKU: **{summary['sku']}**")
    
    # Check for date range warnings
    if st.session_state.returns_data and isinstance(st.session_state.returns_data, dict):
        if 'date_warning' in st.session_state.returns_data and st.session_state.returns_data['date_warning']:
            st.warning(st.session_state.returns_data['date_warning'])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Return Rate", 
            f"{summary['return_rate']:.2f}%"
        )
    
    with col2:
        st.metric(
            "Total Units Sold", 
            f"{int(summary['total_sold']):,}"
        )
    
    with col3:
        st.metric(
            "Total Units Returned", 
            f"{int(summary['total_returned']):,}"
        )
    
    with col4:
        # Updated quality score calculation
        quality_score = calculate_quality_score(summary['return_rate'])
        
        # Determine quality status based on medical device standards
        if quality_score >= 90:
            quality_status = "Excellent"
        elif quality_score >= 70:
            quality_status = "Good"
        elif quality_score >= 50:
            quality_status = "Acceptable"
        else:
            quality_status = "Needs Improvement"
            
        st.metric(
            "Quality Score",
            f"{quality_score}/100",
            delta=quality_status
        )
    
    # Additional context for medical devices
    st.markdown("---")
    st.markdown("#### 📊 Medical Device Industry Context")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"""
        **Return Rate Analysis:**
        - Industry standard: 5-10%
        - Your rate: {summary['return_rate']:.2f}%
        - Status: {quality_status}
        """)
        
        # Show financial impact only if price is provided
        if hasattr(st.session_state, 'unit_price') and st.session_state.unit_price:
            return_cost = summary['total_returned'] * st.session_state.unit_price
            st.info(f"""
            **Financial Impact:**
            - Unit Price: ${st.session_state.unit_price:,.2f}
            - Return Cost: ${return_cost:,.2f}
            """)
    
    with col2:
        # Severity recommendation based on medical device standards
        if summary['return_rate'] > 15:
            severity_rec = "Critical - Immediate action required"
            color = "🔴"
        elif summary['return_rate'] > 10:
            severity_rec = "Major - Investigation recommended"
            color = "🟡"
        else:
            severity_rec = "Minor - Monitor trends"
            color = "🟢"
            
        st.info(f"""
        **Recommended CAPA Severity:**
        {color} {severity_rec}
        """)
    
    # Additional insights
    if results.get('insights'):
        st.markdown("### 🔍 AI-Generated Insights")
        # Remove cost estimates if no price provided
        insights_text = results['insights']
        if not (hasattr(st.session_state, 'unit_price') and st.session_state.unit_price):
            # Remove financial impact section from insights
            lines = insights_text.split('\n')
            filtered_lines = [line for line in lines if '💰' not in line and 'cost' not in line.lower()]
            insights_text = '\n'.join(filtered_lines)
        st.markdown(insights_text)

def generate_ai_capa_suggestions(issue_summary: str, analysis_results: Dict, api_key: str) -> Dict[str, str]:
    """Generate AI suggestions for CAPA form fields based on issue summary and analysis data."""
    
    if not api_key:
        return {}
    
    try:
        # Use the AI helper
        helper = AICAPAHelper(api_key)
        suggestions = helper.generate_capa_suggestions(issue_summary, analysis_results)
        return suggestions
        
    except Exception as e:
        st.error(f"Could not generate AI suggestions: {str(e)}")
        return {}


def display_capa_form():
    """Displays the full CAPA form for data input."""
    st.markdown("## CAPA Information - ISO 13485 Compliant")
    
    # Pre-fill with analysis data if available
    prefill_sku = ""
    prefill_severity = "Minor"
    
    if st.session_state.analysis_results and not st.session_state.analysis_results.get('return_summary', pd.DataFrame()).empty:
        summary = st.session_state.analysis_results['return_summary'].iloc[0]
        prefill_sku = summary['sku']
        
        # Auto-determine severity based on medical device standards
        if summary['return_rate'] > 15:
            prefill_severity = "Critical"
        elif summary['return_rate'] > 10:
            prefill_severity = "Major"
    
    # AI Suggestions Section
    st.markdown("### 🤖 AI-Assisted Form Completion (Optional)")
    
    with st.expander("Get AI Suggestions", expanded=False):
        st.info("Describe the issue briefly, and AI will suggest content for all form fields.")
        
        issue_summary = st.text_area(
            "Issue Summary",
            placeholder="Example: High return rate due to comfort issues with the pressure mattress pad. Customers reporting discomfort and instability.",
            height=100,
            key="issue_summary_for_ai"
        )
        
        if st.button("✨ Generate AI Suggestions", type="secondary"):
            if not issue_summary:
                st.warning("Please provide an issue summary first.")
            elif not st.session_state.analysis_results:
                st.warning("Please analyze your data first to get context-aware suggestions.")
            else:
                with st.spinner("Generating suggestions..."):
                    suggestions = generate_ai_capa_suggestions(
                        issue_summary,
                        st.session_state.analysis_results,
                        st.secrets.get("ANTHROPIC_API_KEY")
                    )
                    
                    if suggestions:
                        st.session_state.ai_suggestions = suggestions
                        st.success("✅ AI suggestions generated! They have been added to the form below. Feel free to edit them.")
                    else:
                        st.error("Could not generate suggestions. Please fill the form manually.")
    
    st.markdown("---")
    
    # Main CAPA Form
    with st.form("capa_form"):
        st.markdown(
            '<div class="info-box">'
            'Fill out the required fields below to generate a compliant CAPA report. '
            'Fields marked with * are required. AI suggestions (if generated) are editable.'
            '</div>',
            unsafe_allow_html=True
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            capa_number = st.text_input(
                "CAPA Number*", 
                value=f"CAPA-{datetime.now().strftime('%Y%m%d')}-001",
                help="Unique identifier for this CAPA"
            )
            product_name = st.text_input(
                "Product Name*", 
                value=prefill_sku,
                help="Full product name or description"
            )
            sku = st.text_input(
                "Primary SKU*", 
                value=prefill_sku,
                help="The SKU being investigated"
            )
            
        with col2:
            prepared_by = st.text_input(
                "Prepared By*",
                help="Your name and title"
            )
            date = st.date_input(
                "Date*", 
                value=datetime.now()
            )
            severity = st.selectbox(
                "Severity Assessment", 
                ["Critical", "Major", "Minor"],
                index=["Critical", "Major", "Minor"].index(prefill_severity),
                help="Based on impact and frequency"
            )
        
        st.markdown("### Issue Details")
        
        # Get AI suggestions if available
        ai_issue = ""
        ai_root_cause = ""
        ai_corrective = ""
        ai_preventive = ""
        
        if hasattr(st.session_state, 'ai_suggestions') and st.session_state.ai_suggestions:
            ai_issue = st.session_state.ai_suggestions.get('issue_description', '')
            ai_root_cause = st.session_state.ai_suggestions.get('root_cause', '')
            ai_corrective = st.session_state.ai_suggestions.get('corrective_action', '')
            ai_preventive = st.session_state.ai_suggestions.get('preventive_action', '')
            
            st.info("📝 AI suggestions have been added to the fields below. You can edit them as needed.")
        
        issue_description = st.text_area(
            "Issue Description*", 
            value=ai_issue,
            height=150,
            placeholder="Provide a detailed problem statement including the nature of returns, frequency, and impact on customers...",
            help="Be specific about the quality issue identified"
        )
        
        root_cause = st.text_area(
            "Root Cause Analysis*", 
            value=ai_root_cause,
            height=150,
            placeholder="Describe the investigation methodology and findings. What is the underlying cause of the returns?",
            help="Use tools like 5 Whys or Fishbone diagram"
        )
        
        corrective_action = st.text_area(
            "Corrective Actions*", 
            value=ai_corrective,
            height=150,
            placeholder="Describe immediate actions to address existing issues and prevent further occurrences...",
            help="What will you do to fix the current problem?"
        )
        
        preventive_action = st.text_area(
            "Preventive Actions*", 
            value=ai_preventive,
            height=150,
            placeholder="Describe long-term actions to prevent recurrence across all products...",
            help="How will you prevent this from happening again?"
        )
        
        # Clear AI suggestions button
        if hasattr(st.session_state, 'ai_suggestions') and st.session_state.ai_suggestions:
            if st.form_submit_button("🗑️ Clear AI Suggestions", type="secondary"):
                st.session_state.ai_suggestions = {}
                st.rerun()
        
        submitted = st.form_submit_button("💾 Save CAPA Data", type="primary")

        if submitted:
            # Validate required fields
            required_fields = {
                'capa_number': capa_number,
                'product': product_name,
                'sku': sku,
                'prepared_by': prepared_by,
                'issue_description': issue_description,
                'root_cause': root_cause,
                'corrective_action': corrective_action,
                'preventive_action': preventive_action
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            
            if missing_fields:
                st.error(f"❌ Please fill in all required fields: {', '.join(missing_fields)}")
            else:
                capa_data = {
                    'capa_number': capa_number,
                    'product': product_name,
                    'sku': sku,
                    'prepared_by': prepared_by,
                    'date': date.strftime('%Y-%m-%d'),
                    'severity': severity,
                    'issue_description': issue_description,
                    'root_cause': root_cause,
                    'corrective_action': corrective_action,
                    'preventive_action': preventive_action
                }
                
                is_valid, errors, warnings = validate_capa_data(capa_data)
                
                if is_valid:
                    st.session_state.capa_data = capa_data
                    # Clear AI suggestions after saving
                    if hasattr(st.session_state, 'ai_suggestions'):
                        st.session_state.ai_suggestions = {}
                    st.success("✅ CAPA data saved successfully!")
                    for warning in warnings:
                        st.warning(f"⚠️ {warning}")
                else:
                    for error in errors:
                        st.error(f"❌ {error}")

def display_doc_gen():
    """Display document generation section."""
    st.markdown("## Generate CAPA Document")
    
    if not st.session_state.capa_data:
        st.markdown(
            '<div class="info-box">'
            '📋 Please complete and save the CAPA form before generating a document.'
            '</div>',
            unsafe_allow_html=True
        )
        return

    # Display saved CAPA data summary
    with st.expander("📄 CAPA Data Summary", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**CAPA Number:** {st.session_state.capa_data['capa_number']}")
            st.markdown(f"**Product:** {st.session_state.capa_data['product']}")
            st.markdown(f"**SKU:** {st.session_state.capa_data['sku']}")
        with col2:
            st.markdown(f"**Severity:** {st.session_state.capa_data['severity']}")
            st.markdown(f"**Prepared By:** {st.session_state.capa_data['prepared_by']}")
            st.markdown(f"**Date:** {st.session_state.capa_data['date']}")

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Generate Document with AI", type="primary", use_container_width=True):
            if not st.session_state.analysis_results:
                st.error("❌ Please process your sales and return data first.")
                return

            with st.spinner("🤖 Generating comprehensive CAPA document..."):
                try:
                    generator = CapaDocumentGenerator(
                        anthropic_api_key=st.secrets.get("ANTHROPIC_API_KEY")
                    )
                    
                    # Generate AI content
                    ai_content = generator.generate_ai_structured_content(
                        st.session_state.capa_data, 
                        st.session_state.analysis_results
                    )
                    
                    if ai_content:
                        # Generate document
                        doc_buffer = generator.export_to_docx(
                            st.session_state.capa_data, 
                            ai_content
                        )
                        
                        # Store in session state for persistent download
                        st.session_state.generated_doc = doc_buffer
                        st.session_state.doc_filename = f"CAPA_{st.session_state.capa_data['capa_number']}.docx"
                        
                        st.success("✅ CAPA document generated successfully!")
                    else:
                        st.error("❌ Failed to generate content from AI. Please check your API key.")
                        
                except Exception as e:
                    st.error(f"❌ Error generating document: {str(e)}")
                    st.info("💡 Make sure your Anthropic API key is configured in Streamlit secrets.")
    
    with col2:
        if st.button("📊 Export Analysis Data", use_container_width=True):
            if st.session_state.analysis_results:
                # Create Excel file with analysis data
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    # Write return summary
                    st.session_state.analysis_results['return_summary'].to_excel(
                        writer, sheet_name='Return Summary', index=False
                    )
                    
                    # Write raw data if available
                    if st.session_state.sales_data is not None:
                        # Ensure it's a DataFrame
                        if isinstance(st.session_state.sales_data, pd.DataFrame):
                            st.session_state.sales_data.to_excel(
                                writer, sheet_name='Sales Data', index=False
                            )
                        else:
                            pd.DataFrame(st.session_state.sales_data).to_excel(
                                writer, sheet_name='Sales Data', index=False
                            )
                    
                    if st.session_state.returns_data is not None:
                        # Ensure it's a DataFrame
                        if isinstance(st.session_state.returns_data, pd.DataFrame):
                            st.session_state.returns_data.to_excel(
                                writer, sheet_name='Returns Data', index=False
                            )
                        elif isinstance(st.session_state.returns_data, dict):
                            pd.DataFrame([st.session_state.returns_data]).to_excel(
                                writer, sheet_name='Returns Data', index=False
                            )
                        else:
                            pd.DataFrame(st.session_state.returns_data).to_excel(
                                writer, sheet_name='Returns Data', index=False
                            )
                
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Download Analysis Data",
                    data=buffer,
                    file_name=f"CAPA_Analysis_{st.session_state.capa_data.get('sku', 'data')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadshingml.sheet"
                )
    
    # Show download button if document was generated
    if hasattr(st.session_state, 'generated_doc') and st.session_state.generated_doc:
        st.markdown("---")
        st.markdown("### 📥 Download Generated Document")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label="📄 Download CAPA Document (.docx)",
                data=st.session_state.generated_doc,
                file_name=st.session_state.doc_filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

# --- Main Application Flow ---
def main():
    initialize_session_state()
    display_header()
    
    # Initialize AI components
    if not initialize_ai_components():
        st.stop()
    
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Input method selection
        input_method = st.radio(
            "Choose Input Method", 
            ('File Upload', 'Manual Entry'),
            help="Upload files for AI analysis or enter data manually"
        )
        
        # Report period
        report_period_days = st.number_input(
            "Report Period (Days)", 
            min_value=1, 
            value=30,
            help="Time period for the analysis"
        )

        st.markdown("---")
        st.header("📁 Data Input")

        if input_method == 'File Upload':
            # SKU input
            target_sku = st.text_input(
                "Enter Target SKU*",
                help="Enter the exact SKU to analyze. The return report should be pre-filtered for this SKU.",
                placeholder="e.g., ABC123-001"
            )
            
            # Product price input
            unit_price = st.number_input(
                "Product Unit Price (Optional)",
                min_value=0.0,
                value=0.0,
                help="Enter price for financial impact calculation. Leave as 0 to skip cost estimates.",
                format="%.2f"
            )
            
            # Date range reminder
            st.info(f"""
            📅 **Important**: Analysis period is set to {report_period_days} days.
            
            Please ensure your return report is filtered for the same period, or adjust the period above.
            The tool will analyze whatever data you provide - it won't force date filtering.
            """)
            
            # File uploads
            st.markdown("### Required Files")
            
            sales_file = st.file_uploader(
                "1. Upload Sales Forecast (Odoo Export)",
                type=['csv', 'xlsx', 'xls'],
                help="Export from Odoo Inventory Forecast"
            )
            
            returns_file = st.file_uploader(
                "2. Upload Pivot Return Report",
                type=['csv', 'xlsx', 'xls'],
                help="Pre-filtered pivot table for the target SKU"
            )
            
            st.markdown("### Optional Files")
            
            misc_files = st.file_uploader(
                "3. Additional Files (FBA Returns, Images, PDFs, etc.)",
                accept_multiple_files=True,
                type=['txt', 'csv', 'xlsx', 'xls', 'pdf', 'png', 'jpg'],
                help="FBA return reports (.txt), supporting documentation, or images"
            )
            
            # Override option
            override_with_manual = st.checkbox(
                "Override with manual data if entered",
                help="If checked, manual data entry will override uploaded file data"
            )
            
            # Process button
            if st.button("🚀 Process Files with AI", type="primary", use_container_width=True):
                if not target_sku:
                    st.warning("⚠️ Please enter the target SKU.")
                elif not sales_file or not returns_file:
                    st.warning("⚠️ Please upload both required files.")
                else:
                    # Store unit price
                    st.session_state.unit_price = unit_price if unit_price > 0 else None
                    st.session_state.override_manual = override_with_manual
                    
                    process_files_with_ai(
                        sales_file, returns_file, misc_files, 
                        target_sku, report_period_days
                    )
        
        elif input_method == 'Manual Entry':
            display_manual_entry_form(report_period_days)
        
        # Debug information
        if st.checkbox("🐛 Show Debug Info"):
            st.markdown("### Debug Information")
            if st.session_state.ai_analysis:
                st.json(st.session_state.ai_analysis)
            if st.session_state.debug_info:
                st.json(st.session_state.debug_info)

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📋 CAPA Form", "📄 Document Generation"])
    
    with tab1:
        if st.session_state.analysis_results:
            # Display AI analysis results
            display_file_analysis_results()
            
            # Display metrics
            display_metrics_dashboard(st.session_state.analysis_results)
            
            # Show raw data tables
            with st.expander("📈 View Raw Data", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.session_state.sales_data is not None:
                        st.markdown("### Sales Data")
                        if isinstance(st.session_state.sales_data, pd.DataFrame):
                            st.dataframe(st.session_state.sales_data)
                        else:
                            st.dataframe(pd.DataFrame(st.session_state.sales_data))
                
                with col2:
                    if st.session_state.returns_data is not None:
                        st.markdown("### Returns Data")
                        if isinstance(st.session_state.returns_data, pd.DataFrame):
                            st.dataframe(st.session_state.returns_data)
                        elif isinstance(st.session_state.returns_data, dict):
                            st.dataframe(pd.DataFrame([st.session_state.returns_data]))
                        else:
                            st.dataframe(pd.DataFrame(st.session_state.returns_data))
        else:
            st.markdown(
                '<div class="info-box">'
                '👆 Enter data using the sidebar and click "Process" to see the analysis.'
                '</div>',
                unsafe_allow_html=True
            )

        # Display miscellaneous files
        if hasattr(st.session_state, 'misc_df') and isinstance(st.session_state.misc_df, pd.DataFrame) and not st.session_state.misc_df.empty:
            st.markdown("---")
            st.markdown("### 📎 Additional Files Processed")
            
            # Check for FBA return reports
            fba_reports = st.session_state.misc_df[st.session_state.misc_df['content_type'] == 'fba_returns']
            if not fba_reports.empty:
                st.info("**FBA Return Report Detected**: Consider analyzing return reasons for additional insights")
            
            try:
                st.dataframe(st.session_state.misc_df)
            except Exception as e:
                st.warning(f"Could not display additional files: {str(e)}")
                # Try to display as JSON instead
                for idx, row in st.session_state.misc_df.iterrows():
                    st.json(row.to_dict())
    
    with tab2:
        display_capa_form()
    
    with tab3:
        display_doc_gen()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.info("Please check your data files and try again.")
        if st.checkbox("Show error details"):
            st.exception(e)
