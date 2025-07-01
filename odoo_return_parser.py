"""
Specialized File Parsers for Medical Device CAPA Tool
Handles Odoo Inventory Forecast and Pivot Return Report formats
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime
import logging
import streamlit as st
from openpyxl import load_workbook

logger = logging.getLogger(__name__)

class OdooInventoryParser:
    """Parse Odoo - Inventory Forecast US Excel files"""
    
    @staticmethod
    def parse_inventory_forecast(file_path) -> pd.DataFrame:
        """
        Parse Odoo Inventory Forecast file
        Expected format: Product data with sales quantities by period
        """
        try:
            # Read all sheets to find the right data
            excel_file = pd.ExcelFile(file_path)
            
            # Common sheet names in Odoo exports
            possible_sheets = ['Sheet1', 'Inventory Forecast', 'Data', 'Export']
            
            df = None
            for sheet in excel_file.sheet_names:
                temp_df = pd.read_excel(file_path, sheet_name=sheet)
                
                # Check if this sheet has the expected columns
                expected_cols = ['product', 'sku', 'quantity', 'date', 'warehouse']
                if any(col in temp_df.columns.str.lower() for col in ['product', 'sku']):
                    df = temp_df
                    break
            
            if df is None:
                # Try first sheet as fallback
                df = pd.read_excel(file_path, sheet_name=0)
            
            # Standardize column names
            column_mapping = {
                'product': 'product_name',
                'product name': 'product_name',
                'product/product': 'product_name',
                'sku': 'sku',
                'product code': 'sku',
                'internal reference': 'sku',
                'quantity': 'quantity',
                'qty': 'quantity',
                'forecasted quantity': 'quantity',
                'date': 'date',
                'date from': 'date',
                'date to': 'date_to',
                'warehouse': 'warehouse',
                'location': 'warehouse',
                'sales channel': 'channel'
            }
            
            # Rename columns
            df.columns = df.columns.str.strip().str.lower()
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df.rename(columns={old_col: new_col}, inplace=True)
            
            # Process dates
            date_cols = ['date', 'date_to']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # If no explicit date column, try to extract from other columns
            if 'date' not in df.columns:
                # Look for date patterns in column names
                for col in df.columns:
                    if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', str(col)):
                        # This column name contains a date
                        date_str = re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', str(col)).group()
                        df['date'] = pd.to_datetime(date_str)
                        df['quantity'] = df[col]
                        break
            
            # Ensure quantity is numeric
            if 'quantity' in df.columns:
                df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
            
            # Add source identifier
            df['source'] = 'Odoo Inventory Forecast'
            
            # Filter out null quantities
            if 'quantity' in df.columns:
                df = df[df['quantity'].notna() & (df['quantity'] > 0)]
            
            logger.info(f"Successfully parsed Odoo file with {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error parsing Odoo Inventory Forecast: {e}")
            raise

class PivotReturnReportParser:
    """Parse Pivot Return Report (return.report) Excel files"""
    
    @staticmethod
    def parse_return_report(file_path) -> pd.DataFrame:
        """
        Parse Pivot Return Report file
        Expected format: Return data with reasons and quantities
        """
        try:
            # Read the Excel file
            excel_file = pd.ExcelFile(file_path)
            
            # Try to find the correct sheet
            df = None
            for sheet in excel_file.sheet_names:
                temp_df = pd.read_excel(file_path, sheet_name=sheet)
                
                # Check for return-related columns
                if any(col in temp_df.columns.str.lower() for col in ['return', 'reason', 'rma']):
                    df = temp_df
                    break
            
            if df is None:
                # Use first sheet as fallback
                df = pd.read_excel(file_path, sheet_name=0)
            
            # Standardize column names
            column_mapping = {
                'product': 'product_name',
                'product name': 'product_name',
                'item': 'product_name',
                'sku': 'sku',
                'product code': 'sku',
                'item code': 'sku',
                'part number': 'sku',
                'quantity': 'quantity',
                'qty': 'quantity',
                'return quantity': 'quantity',
                'returned qty': 'quantity',
                'date': 'return_date',
                'return date': 'return_date',
                'returned date': 'return_date',
                'rma date': 'return_date',
                'reason': 'reason',
                'return reason': 'reason',
                'reason code': 'reason_code',
                'comments': 'customer_comments',
                'notes': 'customer_comments',
                'customer comments': 'customer_comments',
                'order': 'order_id',
                'order id': 'order_id',
                'order number': 'order_id',
                'rma': 'rma_number',
                'rma number': 'rma_number',
                'channel': 'channel',
                'source': 'channel',
                'marketplace': 'channel'
            }
            
            # Rename columns
            df.columns = df.columns.str.strip().str.lower()
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df.rename(columns={old_col: new_col}, inplace=True)
            
            # Process dates
            if 'return_date' in df.columns:
                df['return_date'] = pd.to_datetime(df['return_date'], errors='coerce')
            
            # Ensure quantity is numeric
            if 'quantity' in df.columns:
                df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
                df['quantity'] = df['quantity'].fillna(1)  # Default to 1 if missing
            else:
                df['quantity'] = 1  # Default quantity
            
            # Add return ID if not present
            if 'return_id' not in df.columns:
                df['return_id'] = range(1, len(df) + 1)
            
            # Add source identifier
            df['source'] = 'Pivot Return Report'
            
            # Filter out invalid records
            if 'return_date' in df.columns:
                df = df[df['return_date'].notna()]
            
            logger.info(f"Successfully parsed Return Report with {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error parsing Pivot Return Report: {e}")
            raise

class AmazonVOCParser:
    """Parse Amazon Voice of Customer screenshots and data"""
    
    @staticmethod
    def parse_voc_data(image_text: str) -> Dict:
        """
        Parse text extracted from Amazon VOC screenshots
        Returns structured data about customer issues
        """
        try:
            voc_data = {
                'issues': [],
                'return_rate': None,
                'date_range': None,
                'total_complaints': 0
            }
            
            # Extract return rate if present
            return_rate_match = re.search(r'(\d+\.?\d*)%.*return rate', image_text, re.IGNORECASE)
            if return_rate_match:
                voc_data['return_rate'] = float(return_rate_match.group(1))
            
            # Extract complaint categories and counts
            issue_pattern = re.compile(r'([A-Za-z\s]+?)\s+(\d+\.?\d*)%\s+(\d+)\s+complaints?', re.IGNORECASE)
            
            for match in issue_pattern.finditer(image_text):
                issue = {
                    'category': match.group(1).strip(),
                    'percentage': float(match.group(2)),
                    'count': int(match.group(3))
                }
                voc_data['issues'].append(issue)
                voc_data['total_complaints'] += issue['count']
            
            # Try to identify specific issue types from the text
            quality_keywords = ['quality', 'defective', 'broken', 'damaged', 'malfunction']
            size_keywords = ['size', 'fit', 'large', 'small', 'tight', 'loose']
            wrong_item_keywords = ['wrong', 'incorrect', 'different', 'not as described']
            
            # Categorize issues based on keywords
            for issue in voc_data['issues']:
                category_lower = issue['category'].lower()
                
                if any(keyword in category_lower for keyword in quality_keywords):
                    issue['macro_category'] = 'QUALITY_DEFECTS'
                elif any(keyword in category_lower for keyword in size_keywords):
                    issue['macro_category'] = 'SIZE_FIT_ISSUES'
                elif any(keyword in category_lower for keyword in wrong_item_keywords):
                    issue['macro_category'] = 'WRONG_PRODUCT'
                else:
                    issue['macro_category'] = 'OTHER'
            
            # Look for date range information
            date_pattern = re.compile(r'last\s+(\d+)\s+days?', re.IGNORECASE)
            date_match = date_pattern.search(image_text)
            if date_match:
                voc_data['date_range'] = f"Last {date_match.group(1)} days"
            
            return voc_data
            
        except Exception as e:
            logger.error(f"Error parsing VOC data: {e}")
            return {'issues': [], 'return_rate': None, 'date_range': None, 'total_complaints': 0}

class DataIntegrator:
    """Integrate data from multiple sources for comprehensive analysis"""
    
    @staticmethod
    def integrate_multi_channel_data(
        odoo_sales: Optional[pd.DataFrame],
        return_reports: Optional[pd.DataFrame],
        amazon_voc: Optional[Dict],
        manual_entries: Optional[Dict]
    ) -> Dict:
        """
        Integrate data from all sources and calculate true metrics
        """
        integrated_data = {
            'total_sales': 0,
            'total_returns': 0,
            'overall_return_rate': 0,
            'channel_breakdown': {},
            'date_range': {'start': None, 'end': None},
            'data_sources': [],
            'warnings': []
        }
        
        # Process Odoo sales data
        if odoo_sales is not None and not odoo_sales.empty:
            integrated_data['total_sales'] += odoo_sales['quantity'].sum()
            integrated_data['data_sources'].append('Odoo Inventory Forecast')
            
            if 'date' in odoo_sales.columns:
                min_date = odoo_sales['date'].min()
                max_date = odoo_sales['date'].max()
                
                if integrated_data['date_range']['start'] is None or min_date < integrated_data['date_range']['start']:
                    integrated_data['date_range']['start'] = min_date
                if integrated_data['date_range']['end'] is None or max_date > integrated_data['date_range']['end']:
                    integrated_data['date_range']['end'] = max_date
        
        # Process return report data
        if return_reports is not None and not return_reports.empty:
            integrated_data['total_returns'] += return_reports['quantity'].sum()
            integrated_data['data_sources'].append('Pivot Return Report')
            
            # Channel breakdown
            if 'channel' in return_reports.columns:
                channel_returns = return_reports.groupby('channel')['quantity'].sum()
                for channel, returns in channel_returns.items():
                    if channel not in integrated_data['channel_breakdown']:
                        integrated_data['channel_breakdown'][channel] = {'returns': 0, 'sales': 0}
                    integrated_data['channel_breakdown'][channel]['returns'] += returns
        
        # Add Amazon VOC data as supplementary information only
        if amazon_voc:
            integrated_data['data_sources'].append('Amazon VOC (Reference Only)')
            
            # Add warning about VOC limitations
            if amazon_voc.get('return_rate'):
                integrated_data['warnings'].append(
                    f"Amazon VOC shows {amazon_voc['return_rate']}% return rate for {amazon_voc.get('date_range', 'unknown period')}. "
                    "This is Amazon channel only and should not be used as overall return rate."
                )
            
            integrated_data['voc_insights'] = amazon_voc
        
        # Calculate true overall return rate
        if integrated_data['total_sales'] > 0:
            integrated_data['overall_return_rate'] = (
                integrated_data['total_returns'] / integrated_data['total_sales'] * 100
            )
        
        # Add data quality warnings
        if integrated_data['total_sales'] == 0:
            integrated_data['warnings'].append("No sales data found. Cannot calculate return rate.")
        
        if integrated_data['total_returns'] == 0:
            integrated_data['warnings'].append("No return data found.")
        
        return integrated_data

class ISO13485ComplianceValidator:
    """Ensure CAPA documentation meets ISO 13485 requirements"""
    
    REQUIRED_SECTIONS = [
        'problem_identification',
        'risk_assessment',
        'root_cause_analysis',
        'corrective_action',
        'preventive_action',
        'effectiveness_verification',
        'documentation_control'
    ]
    
    @staticmethod
    def validate_capa_data(capa_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate CAPA data for ISO 13485 compliance
        Returns: (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        required_fields = {
            'capa_number': 'CAPA Number',
            'product': 'Product Name',
            'sku': 'Product SKU',
            'issue_description': 'Issue Description',
            'root_cause': 'Root Cause Analysis',
            'corrective_action': 'Corrective Action',
            'preventive_action': 'Preventive Action',
            'severity': 'Severity Assessment',
            'prepared_by': 'Prepared By',
            'date': 'Date'
        }
        
        for field, label in required_fields.items():
            if field not in capa_data or not capa_data[field]:
                issues.append(f"Missing required field: {label}")
        
        # Validate content quality
        if 'issue_description' in capa_data:
            if len(capa_data['issue_description']) < 50:
                issues.append("Issue description is too brief. Provide detailed problem statement.")
        
        if 'root_cause' in capa_data:
            if len(capa_data['root_cause']) < 50:
                issues.append("Root cause analysis is insufficient. Include investigation methodology.")
        
        if 'corrective_action' in capa_data:
            # Check for timeline
            if not any(word in capa_data['corrective_action'].lower() for word in ['immediate', 'within', 'by', 'date']):
                issues.append("Corrective action should include implementation timeline.")
        
        if 'preventive_action' in capa_data:
            # Check for monitoring plan
            if not any(word in capa_data['preventive_action'].lower() for word in ['monitor', 'review', 'verify', 'check']):
                issues.append("Preventive action should include monitoring/verification plan.")
        
        # Risk assessment validation
        if 'severity' in capa_data:
            if capa_data['severity'] not in ['Critical', 'Major', 'Minor']:
                issues.append("Severity must be classified as Critical, Major, or Minor per ISO 13485.")
        
        is_valid = len(issues) == 0
        return is_valid, issues

# Streamlit integration functions
def process_odoo_file(file) -> pd.DataFrame:
    """Process Odoo Inventory Forecast file in Streamlit"""
    try:
        df = OdooInventoryParser.parse_inventory_forecast(file)
        st.success(f"✅ Processed Odoo file: {len(df)} sales records found")
        return df
    except Exception as e:
        st.error(f"❌ Error processing Odoo file: {str(e)}")
        return pd.DataFrame()

def process_return_report(file) -> pd.DataFrame:
    """Process Pivot Return Report file in Streamlit"""
    try:
        df = PivotReturnReportParser.parse_return_report(file)
        st.success(f"✅ Processed Return Report: {len(df)} return records found")
        return df
    except Exception as e:
        st.error(f"❌ Error processing Return Report: {str(e)}")
        return pd.DataFrame()

def validate_capa_compliance(capa_data: Dict) -> bool:
    """Validate CAPA data for ISO 13485 compliance in Streamlit"""
    is_valid, issues = ISO13485ComplianceValidator.validate_capa_data(capa_data)
    
    if not is_valid:
        st.error("❌ ISO 13485 Compliance Issues Found:")
        for issue in issues:
            st.warning(f"• {issue}")
        return False
    else:
        st.success("✅ CAPA data meets ISO 13485 requirements")
        return True

def display_integrated_metrics(integrated_data: Dict):
    """Display integrated metrics with warnings in Streamlit"""
    
    # Show warnings first
    if integrated_data['warnings']:
        for warning in integrated_data['warnings']:
            st.warning(f"⚠️ {warning}")
    
    # Display true metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Sales (All Channels)",
            f"{integrated_data['total_sales']:,}",
            help="Combined sales from all sources"
        )
    
    with col2:
        st.metric(
            "Total Returns (All Channels)",
            f"{integrated_data['total_returns']:,}",
            help="Combined returns from all sources"
        )
    
    with col3:
        return_rate = integrated_data['overall_return_rate']
        color = "#dc2626" if return_rate > 10 else "#f59e0b" if return_rate > 5 else "#10b981"
        st.metric(
            "True Return Rate",
            f"{return_rate:.2f}%",
            help="Calculated from all channels, not just Amazon VOC"
        )
    
    with col4:
        sources = ", ".join(integrated_data['data_sources'])
        st.metric(
            "Data Sources",
            len(integrated_data['data_sources']),
            help=sources
        )
    
    # Show channel breakdown if available
    if integrated_data['channel_breakdown']:
        st.subheader("📊 Channel Breakdown")
        channel_df = pd.DataFrame(integrated_data['channel_breakdown']).T
        st.dataframe(channel_df, use_container_width=True)
    
    # Show VOC insights separately
    if 'voc_insights' in integrated_data and integrated_data['voc_insights']['issues']:
        st.subheader("📢 Amazon Voice of Customer Insights (Reference Only)")
        st.info("Note: VOC data represents Amazon channel only and should not be used as primary metrics")
        
        voc_df = pd.DataFrame(integrated_data['voc_insights']['issues'])
        st.dataframe(voc_df[['category', 'percentage', 'count']], use_container_width=True)
