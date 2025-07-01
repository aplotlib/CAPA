"""
Medical Device CAPA Tool
A comprehensive quality management system for analyzing returns, sales data, 
and generating AI-powered CAPA documentation
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from typing import Dict, List, Optional, Tuple
import base64
from io import BytesIO, StringIO
import openai
import anthropic
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import re
from PIL import Image
import pytesseract
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Medical Device CAPA Tool",
    page_icon="🏥",
    layout="wide"
)

# Professional medical device styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Professional medical theme */
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background-color: #f8f9fa;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-left: 4px solid;
        height: 100%;
    }
    
    .metric-card.critical {
        border-left-color: #dc2626;
    }
    
    .metric-card.warning {
        border-left-color: #f59e0b;
    }
    
    .metric-card.good {
        border-left-color: #10b981;
    }
    
    .metric-card.info {
        border-left-color: #3b82f6;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #6b7280;
        margin: 0;
    }
    
    .metric-change {
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    /* Status indicators */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .status-critical {
        background-color: #fee2e2;
        color: #dc2626;
    }
    
    .status-warning {
        background-color: #fef3c7;
        color: #d97706;
    }
    
    .status-good {
        background-color: #d1fae5;
        color: #059669;
    }
    
    /* Section headers */
    .section-header {
        background: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 2rem 0 1rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-left: 4px solid #3b82f6;
    }
    
    .section-header h2 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 600;
        color: #1f2937;
    }
    
    /* Forms */
    .capa-form {
        background: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .form-section {
        margin-bottom: 2rem;
        padding-bottom: 2rem;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .form-section:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
    }
    
    .form-label {
        font-weight: 600;
        color: #374151;
        margin-bottom: 0.5rem;
        display: block;
    }
    
    /* Alert boxes */
    .alert-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid;
    }
    
    .alert-critical {
        background-color: #fee2e2;
        border-color: #fecaca;
        color: #7f1d1d;
    }
    
    .alert-warning {
        background-color: #fef3c7;
        border-color: #fde68a;
        color: #78350f;
    }
    
    .alert-info {
        background-color: #dbeafe;
        border-color: #bfdbfe;
        color: #1e3a8a;
    }
    
    /* Buttons */
    .stButton > button {
        font-weight: 500;
        border-radius: 6px;
        padding: 0.5rem 1rem;
    }
    
    /* File uploader */
    .uploadedFile {
        border: 2px dashed #d1d5db;
        border-radius: 8px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'sales_data' not in st.session_state:
    st.session_state.sales_data = None
if 'returns_data' not in st.session_state:
    st.session_state.returns_data = None
if 'metrics' not in st.session_state:
    st.session_state.metrics = {}
if 'capa_data' not in st.session_state:
    st.session_state.capa_data = {}
if 'screenshots' not in st.session_state:
    st.session_state.screenshots = []
if 'ai_client' not in st.session_state:
    st.session_state.ai_client = None

# --- Helper Functions ---
class MetricsCalculator:
    """Calculate key quality metrics from sales and returns data"""
    
    @staticmethod
    def calculate_return_rate(sales_df, returns_df, group_by='sku'):
        """Calculate return rates by product"""
        try:
            # Aggregate sales by product
            sales_summary = sales_df.groupby(group_by).agg({
                'quantity': 'sum',
                'order_date': ['min', 'max', 'count']
            }).reset_index()
            sales_summary.columns = [group_by, 'total_sold', 'first_sale', 'last_sale', 'order_count']
            
            # Aggregate returns by product
            returns_summary = returns_df.groupby(group_by).agg({
                'quantity': 'sum',
                'return_date': 'count'
            }).reset_index()
            returns_summary.columns = [group_by, 'total_returned', 'return_count']
            
            # Merge and calculate rates
            summary = pd.merge(sales_summary, returns_summary, on=group_by, how='left')
            summary['total_returned'] = summary['total_returned'].fillna(0)
            summary['return_count'] = summary['return_count'].fillna(0)
            summary['return_rate'] = (summary['total_returned'] / summary['total_sold'] * 100).round(2)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error calculating return rate: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def calculate_sales_velocity(sales_df, periods=[30, 60, 90]):
        """Calculate sales velocity for different time periods"""
        try:
            velocities = {}
            current_date = pd.Timestamp.now()
            
            for period in periods:
                start_date = current_date - pd.Timedelta(days=period)
                period_sales = sales_df[sales_df['order_date'] >= start_date]
                
                velocity = period_sales.groupby('sku').agg({
                    'quantity': 'sum',
                    'order_id': 'count'
                }).reset_index()
                velocity.columns = ['sku', f'units_{period}d', f'orders_{period}d']
                velocity[f'daily_avg_{period}d'] = (velocity[f'units_{period}d'] / period).round(2)
                
                velocities[period] = velocity
            
            # Merge all periods
            result = velocities[periods[0]]
            for period in periods[1:]:
                result = pd.merge(result, velocities[period], on='sku', how='outer')
            
            return result.fillna(0)
            
        except Exception as e:
            logger.error(f"Error calculating sales velocity: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def identify_quality_issues(returns_df, threshold=5):
        """Identify products with quality issues based on return patterns"""
        try:
            # Analyze return reasons
            reason_analysis = returns_df.groupby(['sku', 'reason']).agg({
                'quantity': 'sum',
                'return_id': 'count'
            }).reset_index()
            reason_analysis.columns = ['sku', 'reason', 'qty_returned', 'incident_count']
            
            # Identify top issues
            quality_indicators = ['defective', 'damaged', 'not_as_described', 'quality', 
                                'broken', 'malfunction', 'not_compatible']
            
            quality_issues = reason_analysis[
                reason_analysis['reason'].str.lower().str.contains('|'.join(quality_indicators), na=False)
            ]
            
            # Flag products exceeding threshold
            flagged_products = quality_issues[quality_issues['incident_count'] >= threshold]
            
            return flagged_products.sort_values('incident_count', ascending=False)
            
        except Exception as e:
            logger.error(f"Error identifying quality issues: {e}")
            return pd.DataFrame()

class DataProcessor:
    """Process various data formats from different channels"""
    
    @staticmethod
    def process_amazon_fba_returns(file_content):
        """Process Amazon FBA returns report"""
        try:
            # Read the tab-delimited file
            df = pd.read_csv(StringIO(file_content), sep='\t', parse_dates=['return-date'])
            
            # Standardize column names
            df = df.rename(columns={
                'return-date': 'return_date',
                'order-id': 'order_id',
                'sku': 'sku',
                'asin': 'asin',
                'product-name': 'product_name',
                'quantity': 'quantity',
                'reason': 'reason',
                'customer-comments': 'customer_comments',
                'detailed-disposition': 'disposition'
            })
            
            # Add return ID for tracking
            df['return_id'] = df.index + 1
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing Amazon FBA returns: {e}")
            return None
    
    @staticmethod
    def process_sales_data(df):
        """Process sales data from various formats"""
        try:
            # Attempt to identify and standardize columns
            column_mapping = {
                'date': 'order_date',
                'order_date': 'order_date',
                'purchase_date': 'order_date',
                'sku': 'sku',
                'product_sku': 'sku',
                'item_sku': 'sku',
                'quantity': 'quantity',
                'qty': 'quantity',
                'units': 'quantity',
                'order_id': 'order_id',
                'order_number': 'order_id',
                'channel': 'channel',
                'marketplace': 'channel'
            }
            
            # Rename columns based on mapping
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # Ensure required columns exist
            required_cols = ['order_date', 'sku', 'quantity']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"Missing required columns: {missing_cols}")
                return None
            
            # Convert date column
            df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
            
            # Remove invalid rows
            df = df.dropna(subset=['order_date', 'sku', 'quantity'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing sales data: {e}")
            return None

class AIDocumentGenerator:
    """Generate CAPA documents using AI"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AI clients from Streamlit secrets"""
        try:
            if 'OPENAI_API_KEY' in st.secrets:
                openai.api_key = st.secrets['OPENAI_API_KEY']
                self.openai_client = openai
            
            if 'ANTHROPIC_API_KEY' in st.secrets:
                self.anthropic_client = anthropic.Anthropic(api_key=st.secrets['ANTHROPIC_API_KEY'])
                
        except Exception as e:
            logger.error(f"Error initializing AI clients: {e}")
    
    def generate_capa_document(self, capa_data, metrics, quality_issues, use_anthropic=True):
        """Generate CAPA document using AI"""
        
        prompt = self._build_capa_prompt(capa_data, metrics, quality_issues)
        
        try:
            if use_anthropic and self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4000,
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                return response.content[0].text
                
            elif self.openai_client:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{
                        "role": "system",
                        "content": "You are a medical device quality management expert creating formal CAPA documentation."
                    }, {
                        "role": "user",
                        "content": prompt
                    }],
                    temperature=0,
                    max_tokens=4000
                )
                return response.choices[0].message.content
                
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error generating CAPA document: {e}")
            return None
    
    def _build_capa_prompt(self, capa_data, metrics, quality_issues):
        """Build prompt for CAPA generation"""
        
        prompt = f"""Generate a formal CAPA (Corrective and Preventive Action) report for a medical device quality issue.

CAPA DATA:
- CAPA Number: {capa_data.get('capa_number', 'TBD')}
- Date: {datetime.now().strftime('%Y-%m-%d')}
- Product: {capa_data.get('product', 'TBD')}
- SKU: {capa_data.get('sku', 'TBD')}

ISSUE DESCRIPTION:
{capa_data.get('issue_description', 'TBD')}

METRICS SUMMARY:
- Overall Return Rate: {metrics.get('overall_return_rate', 0):.2f}%
- Units Returned: {metrics.get('total_returns', 0)}
- Units Sold: {metrics.get('total_sales', 0)}
- Time Period: {metrics.get('period', 'Last 90 days')}

TOP QUALITY ISSUES:
{quality_issues.to_string() if not quality_issues.empty else 'No specific quality issues identified'}

PROPOSED CORRECTIVE ACTION:
{capa_data.get('corrective_action', 'TBD')}

Please generate a comprehensive CAPA report following medical device quality standards that includes:

1. ISSUE IDENTIFICATION
   - Clear problem statement
   - Impact assessment
   - Risk classification

2. ROOT CAUSE ANALYSIS
   - Investigation methodology
   - Root cause findings
   - Contributing factors

3. CORRECTIVE ACTIONS
   - Immediate actions taken
   - Long-term corrective measures
   - Implementation timeline
   - Responsible parties

4. PREVENTIVE ACTIONS
   - Systemic improvements
   - Process changes
   - Training requirements
   - Monitoring plans

5. EFFECTIVENESS VERIFICATION
   - Success criteria
   - Verification methods
   - Timeline for effectiveness checks
   - Key performance indicators

6. RISK ASSESSMENT
   - Patient safety impact
   - Regulatory considerations
   - Business impact

Format the response as a professional CAPA document suitable for regulatory submission."""
        
        return prompt
    
    def export_to_docx(self, content, capa_data):
        """Export CAPA content to Word document"""
        try:
            doc = Document()
            
            # Add header
            header = doc.sections[0].header
            header_para = header.paragraphs[0]
            header_para.text = "CORRECTIVE AND PREVENTIVE ACTION (CAPA) REPORT"
            header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add title
            title = doc.add_heading('CAPA Report', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add CAPA details
            doc.add_paragraph(f"CAPA Number: {capa_data.get('capa_number', 'TBD')}")
            doc.add_paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
            doc.add_paragraph(f"Product: {capa_data.get('product', 'TBD')}")
            doc.add_paragraph(f"Prepared By: {capa_data.get('prepared_by', 'Quality Team')}")
            
            doc.add_paragraph()
            
            # Add content sections
            sections = content.split('\n\n')
            for section in sections:
                if section.strip():
                    if section.strip().isupper() or section.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.')):
                        # Section header
                        doc.add_heading(section.strip(), level=1)
                    else:
                        # Regular paragraph
                        doc.add_paragraph(section.strip())
            
            # Add signature section
            doc.add_page_break()
            doc.add_heading('Approvals', level=1)
            
            table = doc.add_table(rows=4, cols=3)
            table.style = 'Light Grid Accent 1'
            
            # Header row
            cells = table.rows[0].cells
            cells[0].text = 'Role'
            cells[1].text = 'Name / Signature'
            cells[2].text = 'Date'
            
            # Signature rows
            roles = ['Prepared By', 'Reviewed By', 'Approved By']
            for i, role in enumerate(roles, 1):
                cells = table.rows[i].cells
                cells[0].text = role
                cells[1].text = '_' * 30
                cells[2].text = '_' * 15
            
            # Save to BytesIO
            bio = BytesIO()
            doc.save(bio)
            bio.seek(0)
            
            return bio
            
        except Exception as e:
            logger.error(f"Error exporting to DOCX: {e}")
            return None

# --- UI Components ---
def display_header():
    """Display application header"""
    st.markdown("""
    <div class="main-header">
        <h1>🏥 Medical Device CAPA Tool</h1>
        <p>Quality Management System for Returns Analysis and CAPA Generation</p>
    </div>
    """, unsafe_allow_html=True)

def display_metrics_dashboard(metrics):
    """Display key metrics dashboard"""
    col1, col2, col3, col4 = st.columns(4)
    
    # Return Rate
    with col1:
        return_rate = metrics.get('overall_return_rate', 0)
        if return_rate > 10:
            status_class = "critical"
            status_color = "#dc2626"
        elif return_rate > 5:
            status_class = "warning"
            status_color = "#f59e0b"
        else:
            status_class = "good"
            status_color = "#10b981"
        
        st.markdown(f"""
        <div class="metric-card {status_class}">
            <p class="metric-label">Overall Return Rate</p>
            <p class="metric-value" style="color: {status_color}">{return_rate:.1f}%</p>
            <p class="metric-change">Target: <5%</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Total Returns
    with col2:
        total_returns = metrics.get('total_returns', 0)
        st.markdown(f"""
        <div class="metric-card info">
            <p class="metric-label">Total Returns</p>
            <p class="metric-value" style="color: #3b82f6">{total_returns:,}</p>
            <p class="metric-change">{metrics.get('period', 'All Time')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Products Affected
    with col3:
        products_affected = metrics.get('products_affected', 0)
        st.markdown(f"""
        <div class="metric-card info">
            <p class="metric-label">Products Affected</p>
            <p class="metric-value" style="color: #3b82f6">{products_affected}</p>
            <p class="metric-change">Unique SKUs</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Quality Issues
    with col4:
        quality_issues = metrics.get('quality_issues', 0)
        if quality_issues > 0:
            status_class = "warning"
            status_color = "#f59e0b"
        else:
            status_class = "good"
            status_color = "#10b981"
        
        st.markdown(f"""
        <div class="metric-card {status_class}">
            <p class="metric-label">Quality Issues</p>
            <p class="metric-value" style="color: {status_color}">{quality_issues}</p>
            <p class="metric-change">Flagged Products</p>
        </div>
        """, unsafe_allow_html=True)

def display_quality_alerts(quality_issues):
    """Display quality alerts for products with issues"""
    if quality_issues.empty:
        return
    
    st.markdown('<div class="section-header"><h2>⚠️ Quality Alerts</h2></div>', unsafe_allow_html=True)
    
    for _, issue in quality_issues.iterrows():
        severity = "critical" if issue['incident_count'] >= 10 else "warning"
        st.markdown(f"""
        <div class="alert-box alert-{severity}">
            <strong>SKU: {issue['sku']}</strong><br>
            Reason: {issue['reason']}<br>
            Incidents: {issue['incident_count']} | Units: {issue['qty_returned']}
        </div>
        """, unsafe_allow_html=True)

# --- Main Application ---
def main():
    display_header()
    
    # Sidebar for data upload
    with st.sidebar:
        st.header("📁 Data Upload")
        
        st.subheader("Sales Data")
        sales_file = st.file_uploader(
            "Upload sales data (CSV/Excel)",
            type=['csv', 'xlsx', 'xls'],
            help="Should contain: order_date, sku, quantity"
        )
        
        st.subheader("Returns Data")
        returns_file = st.file_uploader(
            "Upload returns data (CSV/TXT)",
            type=['csv', 'txt', 'xlsx'],
            help="Amazon FBA returns report or similar format"
        )
        
        st.subheader("Supporting Evidence")
        screenshots = st.file_uploader(
            "Upload screenshots",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="Upload relevant screenshots or images"
        )
        
        if st.button("🔄 Process Data", type="primary"):
            process_uploaded_data(sales_file, returns_file, screenshots)
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Analysis", "📝 CAPA Form", "📄 Documents"])
    
    with tab1:
        if st.session_state.metrics:
            display_metrics_dashboard(st.session_state.metrics)
            
            # Return rate trend
            if st.session_state.returns_data is not None:
                st.markdown('<div class="section-header"><h2>📈 Return Rate Trend</h2></div>', unsafe_allow_html=True)
                display_return_trend(st.session_state.returns_data)
            
            # Quality alerts
            if 'quality_issues' in st.session_state and not st.session_state.quality_issues.empty:
                display_quality_alerts(st.session_state.quality_issues)
        else:
            st.info("📤 Please upload sales and returns data to view metrics")
    
    with tab2:
        if st.session_state.sales_data is not None and st.session_state.returns_data is not None:
            display_detailed_analysis()
        else:
            st.info("📤 Please upload data to view analysis")
    
    with tab3:
        display_capa_form()
    
    with tab4:
        display_document_generation()

def process_uploaded_data(sales_file, returns_file, screenshots):
    """Process uploaded files and calculate metrics"""
    
    with st.spinner("Processing data..."):
        # Process sales data
        if sales_file:
            try:
                if sales_file.name.endswith('.csv'):
                    sales_df = pd.read_csv(sales_file)
                else:
                    sales_df = pd.read_excel(sales_file)
                
                sales_df = DataProcessor.process_sales_data(sales_df)
                if sales_df is not None:
                    st.session_state.sales_data = sales_df
                    st.success(f"✅ Loaded {len(sales_df)} sales records")
            except Exception as e:
                st.error(f"Error processing sales file: {e}")
        
        # Process returns data
        if returns_file:
            try:
                if returns_file.name.endswith('.txt'):
                    # Amazon FBA format
                    content = returns_file.read().decode('utf-8')
                    returns_df = DataProcessor.process_amazon_fba_returns(content)
                elif returns_file.name.endswith('.csv'):
                    returns_df = pd.read_csv(returns_file)
                    returns_df = DataProcessor.process_sales_data(returns_df)  # Use same processor
                else:
                    returns_df = pd.read_excel(returns_file)
                    returns_df = DataProcessor.process_sales_data(returns_df)
                
                if returns_df is not None:
                    st.session_state.returns_data = returns_df
                    st.success(f"✅ Loaded {len(returns_df)} return records")
            except Exception as e:
                st.error(f"Error processing returns file: {e}")
        
        # Process screenshots
        if screenshots:
            st.session_state.screenshots = screenshots
            st.success(f"✅ Loaded {len(screenshots)} screenshots")
        
        # Calculate metrics if both datasets available
        if st.session_state.sales_data is not None and st.session_state.returns_data is not None:
            calculate_metrics()

def calculate_metrics():
    """Calculate all metrics from loaded data"""
    
    calc = MetricsCalculator()
    
    # Calculate return rates
    return_summary = calc.calculate_return_rate(
        st.session_state.sales_data, 
        st.session_state.returns_data
    )
    
    # Calculate sales velocity
    velocity = calc.calculate_sales_velocity(st.session_state.sales_data)
    
    # Identify quality issues
    quality_issues = calc.identify_quality_issues(st.session_state.returns_data)
    st.session_state.quality_issues = quality_issues
    
    # Calculate overall metrics
    total_sales = st.session_state.sales_data['quantity'].sum()
    total_returns = st.session_state.returns_data['quantity'].sum()
    overall_return_rate = (total_returns / total_sales * 100) if total_sales > 0 else 0
    
    st.session_state.metrics = {
        'overall_return_rate': overall_return_rate,
        'total_sales': total_sales,
        'total_returns': total_returns,
        'products_affected': return_summary['sku'].nunique(),
        'quality_issues': len(quality_issues),
        'period': 'All Time',
        'return_summary': return_summary,
        'velocity': velocity
    }

def display_return_trend(returns_df):
    """Display return rate trend chart"""
    
    # Group by month
    returns_df['month'] = pd.to_datetime(returns_df['return_date']).dt.to_period('M')
    monthly_returns = returns_df.groupby('month')['quantity'].sum().reset_index()
    monthly_returns['month'] = monthly_returns['month'].astype(str)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_returns['month'],
        y=monthly_returns['quantity'],
        mode='lines+markers',
        name='Returns',
        line=dict(color='#dc2626', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="Monthly Return Volume",
        xaxis_title="Month",
        yaxis_title="Units Returned",
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_detailed_analysis():
    """Display detailed analysis tab"""
    
    st.markdown('<div class="section-header"><h2>📊 Return Rate by Product</h2></div>', unsafe_allow_html=True)
    
    if 'return_summary' in st.session_state.metrics:
        summary = st.session_state.metrics['return_summary']
        
        # Sort by return rate
        summary = summary.sort_values('return_rate', ascending=False)
        
        # Create bar chart
        fig = px.bar(
            summary.head(20),
            x='sku',
            y='return_rate',
            title='Top 20 Products by Return Rate',
            labels={'return_rate': 'Return Rate (%)', 'sku': 'SKU'},
            color='return_rate',
            color_continuous_scale=['green', 'yellow', 'red']
        )
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Display detailed table
        st.subheader("Detailed Product Metrics")
        
        # Add velocity data if available
        if 'velocity' in st.session_state.metrics:
            summary = pd.merge(summary, st.session_state.metrics['velocity'], on='sku', how='left')
        
        # Format for display
        display_cols = ['sku', 'total_sold', 'total_returned', 'return_rate', 'daily_avg_30d', 'daily_avg_90d']
        available_cols = [col for col in display_cols if col in summary.columns]
        
        st.dataframe(
            summary[available_cols].style.format({
                'return_rate': '{:.1f}%',
                'daily_avg_30d': '{:.1f}',
                'daily_avg_90d': '{:.1f}'
            }).background_gradient(subset=['return_rate'], cmap='RdYlGn_r'),
            use_container_width=True
        )

def display_capa_form():
    """Display CAPA form"""
    
    st.markdown('<div class="section-header"><h2>📝 CAPA Information</h2></div>', unsafe_allow_html=True)
    
    with st.form("capa_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            capa_number = st.text_input("CAPA Number", value=f"CAPA-{datetime.now().strftime('%Y%m%d')}-001")
            product = st.text_input("Product Name", placeholder="e.g., Wheelchair Bag Advanced")
            sku = st.text_input("Primary SKU", placeholder="e.g., LVA3100BLK")
            prepared_by = st.text_input("Prepared By", value="Quality Team")
        
        with col2:
            date = st.date_input("Date", value=datetime.now())
            department = st.selectbox("Department", ["Quality", "Engineering", "Production", "Supply Chain"])
            severity = st.selectbox("Severity", ["Critical", "Major", "Minor"])
            priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        
        st.markdown("### Issue Description")
        issue_description = st.text_area(
            "Describe the issue",
            height=150,
            placeholder="Provide detailed description of the quality issue, including impact on customers and products"
        )
        
        st.markdown("### Root Cause Analysis")
        root_cause = st.text_area(
            "Root Cause Analysis",
            height=150,
            placeholder="Describe investigation findings and identified root causes"
        )
        
        st.markdown("### Corrective Actions")
        corrective_action = st.text_area(
            "Proposed Corrective Actions",
            height=150,
            placeholder="Detail immediate and long-term corrective actions"
        )
        
        st.markdown("### Preventive Actions")
        preventive_action = st.text_area(
            "Proposed Preventive Actions",
            height=150,
            placeholder="Describe actions to prevent recurrence"
        )
        
        submitted = st.form_submit_button("💾 Save CAPA Data", type="primary")
        
        if submitted:
            st.session_state.capa_data = {
                'capa_number': capa_number,
                'date': date.strftime('%Y-%m-%d'),
                'product': product,
                'sku': sku,
                'prepared_by': prepared_by,
                'department': department,
                'severity': severity,
                'priority': priority,
                'issue_description': issue_description,
                'root_cause': root_cause,
                'corrective_action': corrective_action,
                'preventive_action': preventive_action
            }
            st.success("✅ CAPA data saved successfully!")

def display_document_generation():
    """Display document generation tab"""
    
    st.markdown('<div class="section-header"><h2>📄 Generate CAPA Document</h2></div>', unsafe_allow_html=True)
    
    if not st.session_state.capa_data:
        st.warning("⚠️ Please fill out the CAPA form first")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Document Options")
        
        use_ai = st.checkbox("Use AI to enhance document", value=True)
        if use_ai:
            ai_provider = st.radio("AI Provider", ["Anthropic (Claude)", "OpenAI (GPT-4)"])
        
        include_metrics = st.checkbox("Include metrics summary", value=True)
        include_charts = st.checkbox("Include charts", value=True)
        include_screenshots = st.checkbox("Include uploaded screenshots", value=True)
    
    with col2:
        st.subheader("Export Format")
        export_format = st.radio("Format", ["Word Document (.docx)", "PDF (coming soon)"])
    
    if st.button("🚀 Generate Document", type="primary"):
        generate_capa_document(use_ai, ai_provider if use_ai else None, include_metrics, include_charts, include_screenshots)

def generate_capa_document(use_ai, ai_provider, include_metrics, include_charts, include_screenshots):
    """Generate the CAPA document"""
    
    with st.spinner("Generating document..."):
        generator = AIDocumentGenerator()
        
        # Generate content
        if use_ai:
            quality_issues = st.session_state.quality_issues if 'quality_issues' in st.session_state else pd.DataFrame()
            content = generator.generate_capa_document(
                st.session_state.capa_data,
                st.session_state.metrics,
                quality_issues,
                use_anthropic=(ai_provider == "Anthropic (Claude)")
            )
            
            if content:
                st.success("✅ AI content generated successfully!")
            else:
                st.warning("⚠️ AI generation failed, using template format")
                content = generate_template_content()
        else:
            content = generate_template_content()
        
        # Export to Word
        doc_buffer = generator.export_to_docx(content, st.session_state.capa_data)
        
        if doc_buffer:
            st.download_button(
                label="📥 Download CAPA Document",
                data=doc_buffer,
                file_name=f"CAPA_{st.session_state.capa_data['capa_number']}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            # Display preview
            st.markdown("### Document Preview")
            st.text_area("Content", content, height=500)

def generate_template_content():
    """Generate basic template content without AI"""
    
    capa = st.session_state.capa_data
    metrics = st.session_state.metrics
    
    content = f"""CORRECTIVE AND PREVENTIVE ACTION (CAPA) REPORT

1. ISSUE IDENTIFICATION

CAPA Number: {capa['capa_number']}
Date: {capa['date']}
Product: {capa['product']}
SKU: {capa['sku']}
Severity: {capa['severity']}
Priority: {capa['priority']}

Issue Description:
{capa['issue_description']}

2. METRICS SUMMARY

Overall Return Rate: {metrics.get('overall_return_rate', 0):.2f}%
Total Units Returned: {metrics.get('total_returns', 0):,}
Total Units Sold: {metrics.get('total_sales', 0):,}
Products Affected: {metrics.get('products_affected', 0)}

3. ROOT CAUSE ANALYSIS

{capa['root_cause']}

4. CORRECTIVE ACTIONS

{capa['corrective_action']}

5. PREVENTIVE ACTIONS

{capa['preventive_action']}

6. IMPLEMENTATION PLAN

[To be developed]

7. EFFECTIVENESS VERIFICATION

[To be determined]

Prepared by: {capa['prepared_by']}
Department: {capa['department']}
"""
    
    return content

if __name__ == "__main__":
    main()
