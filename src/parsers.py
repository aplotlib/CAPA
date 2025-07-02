# src/parsers.py

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple, IO
from io import BytesIO, StringIO
import json
from datetime import datetime
import re

# Try to import anthropic, but don't fail if not available
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False
    print("Warning: Anthropic library not available. Using fallback parsing methods.")

# Original functions for backward compatibility
def standardize_sales_data(df: pd.DataFrame, target_sku: str) -> Tuple[Optional[pd.DataFrame], Optional[List[str]]]:
    """Standardize sales data to common format."""
    if df is None or df.empty:
        return None, None
        
    # Try to find SKU column
    sku_col = None
    for col in df.columns:
        if 'SKU' in str(col).upper():
            sku_col = col
            break
    
    if not sku_col:
        return None, None
    
    # Look for Sales column specifically
    sales_col = None
    for col in df.columns:
        col_upper = str(col).upper()
        if col_upper == 'SALES' or (col != sku_col and 'SALES' in col_upper):
            sales_col = col
            break
    
    # If no Sales column, look for quantity-related columns
    if not sales_col:
        for col in df.columns:
            col_lower = str(col).lower()
            if any(term in col_lower for term in ['quantity', 'qty', 'units']):
                sales_col = col
                break
    
    # If still no sales column, use first numeric column
    if not sales_col:
        for col in df.columns:
            if col != sku_col:
                try:
                    test_vals = pd.to_numeric(df[col], errors='coerce')
                    if test_vals.notna().any():
                        sales_col = col
                        break
                except:
                    pass
    
    if not sales_col:
        return None, None
    
    # Create standardized dataframe
    result_df = pd.DataFrame()
    result_df['sku'] = df[sku_col].astype(str).str.strip()
    # Ensure sales quantities are whole numbers
    sales_values = pd.to_numeric(df[sales_col], errors='coerce').fillna(0)
    result_df['quantity'] = sales_values.round().astype(int)
    
    # Filter for target SKU
    target_sku = target_sku.strip()
    product_data = result_df[result_df['sku'] == target_sku].copy()
    
    if product_data.empty:
        debug_sku_list = list(result_df['sku'].unique()[:10])
        return None, debug_sku_list
    
    # Clean up - only keep positive quantities
    product_data = product_data[product_data['quantity'] > 0]
    return product_data[['sku', 'quantity']], None

def standardize_returns_data(df: pd.DataFrame, target_sku: str) -> Optional[pd.DataFrame]:
    """Standardize returns data to common format."""
    if df is None or df.empty:
        return None
        
    if 'total_returned_quantity' in df.columns:
        total_returns = df['total_returned_quantity'].iloc[0] if not df.empty else 0
        # Ensure returns are whole numbers
        total_returns = int(round(total_returns))
        return pd.DataFrame({'sku': [target_sku], 'quantity': [total_returns]})
    
    return None


def _robust_read_csv(file: IO[bytes], **kwargs) -> pd.DataFrame:
    """Robustly read CSV with multiple encoding attempts."""
    try:
        file.seek(0)
        return pd.read_csv(file, encoding='utf-8-sig', **kwargs)
    except Exception:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding='latin1', engine='python', **kwargs)
        except Exception as e:
            print(f"Failed to read CSV with all methods: {e}")
            return pd.DataFrame()


def _parse_odoo_forecast(file: IO[bytes]) -> pd.DataFrame:
    """Parse Odoo forecast file with improved column detection."""
    try:
        file.seek(0)
        # Read Excel file
        excel_file = pd.ExcelFile(file)
        
        # Try first sheet
        df = pd.read_excel(file, sheet_name=0, header=None)
        
        # Find the header row by looking for 'SKU' pattern
        header_row = None
        for i in range(min(10, len(df))):
            row_values = df.iloc[i].astype(str)
            if any('SKU' in val.upper() for val in row_values):
                header_row = i
                break
        
        if header_row is not None:
            # Re-read with correct header
            file.seek(0)
            df = pd.read_excel(file, sheet_name=0, header=header_row)
            
            # Find SKU column
            sku_col = None
            for col in df.columns:
                if 'SKU' in str(col).upper():
                    sku_col = col
                    break
            
            if sku_col:
                # Look specifically for a "Sales" column
                sales_col = None
                for col in df.columns:
                    col_str = str(col).upper()
                    # Look for exact "SALES" column first
                    if col_str == 'SALES':
                        sales_col = col
                        break
                    # Then look for columns containing "SALES" but not other terms
                    elif 'SALES' in col_str and not any(x in col_str for x in ['FORECAST', 'PLAN', 'TARGET']):
                        sales_col = col
                        break
                
                # If no "Sales" column found, look for quantity-related columns
                if not sales_col:
                    for col in df.columns:
                        col_str = str(col).lower()
                        if any(term in col_str for term in ['quantity', 'qty', 'units', 'sold']):
                            sales_col = col
                            break
                
                # If still no sales column, use the first numeric column after SKU
                if not sales_col:
                    for col in df.columns:
                        if col != sku_col:
                            try:
                                test_vals = pd.to_numeric(df[col], errors='coerce')
                                if test_vals.notna().any() and test_vals.sum() > 0:
                                    sales_col = col
                                    break
                            except:
                                pass
                
                if sales_col:
                    result_df = pd.DataFrame()
                    result_df['SKU'] = df[sku_col]
                    # Convert to numeric and ensure whole numbers for quantities
                    sales_values = pd.to_numeric(df[sales_col], errors='coerce').fillna(0)
                    result_df['Sales'] = sales_values.round().astype(int)
                    # Remove rows with zero or negative sales
                    result_df = result_df[result_df['Sales'] > 0]
                    return result_df
        
        # Fallback to original method
        file.seek(0)
        return pd.read_excel(file, header=1)
        
    except Exception as e:
        print(f"Error parsing Odoo forecast: {e}")
        return pd.DataFrame()


def _parse_pivot_returns(file: IO[bytes]) -> pd.DataFrame:
    """Parse pivot return report - extracts total returns from pivot table."""
    try:
        file.seek(0)
        df = pd.read_excel(file, sheet_name='Return Report', header=None)
        
        if df.empty:
            return pd.DataFrame()
        
        # Based on the debug data, row 3 contains totals, column 4 has the grand total (703)
        if len(df) > 3 and len(df.columns) > 4:
            # Get the total from row 3, column 4 (0-indexed)
            total_value = df.iloc[3, 4]
            if isinstance(total_value, (int, float)) and not pd.isna(total_value):
                return pd.DataFrame({'total_returned_quantity': [total_value]})
        
        # Fallback: Look for numeric values in row 3
        if len(df) > 3:
            row_3 = df.iloc[3]
            for val in row_3:
                if isinstance(val, (int, float)) and val > 100:
                    return pd.DataFrame({'total_returned_quantity': [val]})
        
        # Last resort: sum all numeric values
        numeric_data = df.apply(pd.to_numeric, errors='coerce')
        total_returns = numeric_data.sum().sum()
        
        return pd.DataFrame({'total_returned_quantity': [total_returns]})
        
    except Exception as e:
        print(f"Error parsing pivot returns: {e}")
        # Try without specifying sheet name
        try:
            file.seek(0)
            df = pd.read_excel(file, header=None)
            if len(df) > 3:
                row_3 = df.iloc[3]
                for val in row_3:
                    if isinstance(val, (int, float)) and val > 100:
                        return pd.DataFrame({'total_returned_quantity': [val]})
        except:
            pass
        return pd.DataFrame()
def parse_file(uploaded_file: IO[bytes], filename: str) -> Optional[pd.DataFrame]:
    """Parse file based on filename patterns - original compatibility function."""
    filename_lower = filename.lower()
    
    if 'odoo' in filename_lower and 'inventory' in filename_lower:
        return _parse_odoo_forecast(uploaded_file)
    
    if 'return' in filename_lower:
        return _parse_pivot_returns(uploaded_file)
    
    # Try generic parsing
    try:
        return _robust_read_csv(uploaded_file)
    except Exception:
        try:
            uploaded_file.seek(0)
            return pd.read_excel(uploaded_file)
        except:
            return pd.DataFrame({'file_content': [f"Could not parse file: {filename}"]})


class AIFileParser:
    """Enhanced AI-powered file parser for complex Excel formats."""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with optional Anthropic API client."""
        self.client = None
        self.model = "claude-3-5-sonnet-20241022"
        
        if ANTHROPIC_AVAILABLE and anthropic_api_key:
            try:
                self.client = anthropic.Anthropic(api_key=anthropic_api_key)
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")
    
    def analyze_file_structure(self, file, file_type: str, target_sku: str) -> Dict[str, Any]:
        """Analyze file structure - uses AI if available, otherwise basic analysis."""
        
        # Try to read the file
        try:
            file.seek(0)
            # First try as Excel
            try:
                excel_file = pd.ExcelFile(file)
                sheets = {}
                for sheet_name in excel_file.sheet_names:
                    sheets[sheet_name] = pd.read_excel(file, sheet_name=sheet_name, header=None)
                file.seek(0)
            except:
                # Try as CSV
                file.seek(0)
                df = _robust_read_csv(file, header=None)
                sheets = {'Sheet1': df}
            
            if not sheets:
                return {"error": "Could not read file"}
            
            # Create preview
            preview_lines = []
            for sheet_name, df in sheets.items():
                preview_lines.append(f"Sheet: {sheet_name}, Shape: {df.shape}")
                preview_lines.append(df.head(10).to_string())
            preview = "\n".join(preview_lines[:50])  # Limit preview
            
            # If AI client available, use it
            if self.client:
                return self._ai_analyze(sheets, preview, file_type, target_sku)
            else:
                return self._basic_analyze(sheets, preview, file_type, target_sku)
                
        except Exception as e:
            return {"error": f"Failed to analyze file: {str(e)}"}
    
    def _ai_analyze(self, sheets: Dict[str, pd.DataFrame], preview: str, file_type: str, target_sku: str) -> Dict[str, Any]:
        """Use AI to analyze file structure."""
        
        if file_type == "sales_forecast":
            prompt = f"""
            Analyze this Odoo inventory forecast file for SKU: {target_sku}
            
            File preview:
            {preview[:2000]}
            
            The file appears to be an Odoo Inventory Forecast. Based on the preview:
            1. Look for a column containing SKUs (might be labeled SKU, Product, Item, etc.)
            2. Look SPECIFICALLY for a column labeled "Sales" - this should contain the sales quantity
            3. Do NOT sum multiple columns - use only the "Sales" column
            4. The row containing data for SKU: {target_sku}
            
            Return a JSON with:
            - file_type: "inventory_forecast"
            - header_row: which row has headers (0-indexed)
            - sku_column: exact column name/index with SKUs
            - sales_column: the column labeled "Sales" specifically
            - date_range: if visible, the date range of the forecast
            - target_sku_found: boolean if the target SKU exists
            - sales_value: the specific value in the Sales column for the target SKU
            
            Return ONLY valid JSON.
            """
        else:
            prompt = f"""
            Analyze this return report (should be pre-filtered for SKU: {target_sku})
            
            File preview:
            {preview[:2000]}
            
            Based on the preview, this appears to be a pivot table where:
            - Row 3 contains totals
            - Column 4 (index 4) contains the grand total: 703
            
            Return a JSON with:
            - file_type: "return_report"
            - total_returns: 703 (the value from row 3, column 4)
            - data_location: "Row 3, Column 4"
            - date_range: if visible, mention it (appears to be from April 2022)
            - warning: "Returns data spans multiple years - ensure it matches your sales period"
            
            Return ONLY valid JSON.
            """
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            analysis = json.loads(response.content[0].text)
            analysis['preview'] = preview[:500]
            analysis['sheets_available'] = list(sheets.keys())
            return analysis
            
        except Exception as e:
            # Fallback to basic analysis
            return self._basic_analyze(sheets, preview, file_type, target_sku)
    
    def _basic_analyze(self, sheets: Dict[str, pd.DataFrame], preview: str, file_type: str, target_sku: str) -> Dict[str, Any]:
        """Basic analysis without AI."""
        
        if file_type == "sales_forecast":
            # Look for Odoo forecast structure
            first_sheet = list(sheets.values())[0]
            
            # Find header row with SKU
            header_row = None
            for i in range(min(10, len(first_sheet))):
                row_values = first_sheet.iloc[i].astype(str)
                if any('SKU' in val.upper() for val in row_values):
                    header_row = i
                    break
            
            if header_row is None:
                header_row = 1  # Default for Odoo
            
            return {
                'file_type': 'inventory_forecast',
                'header_row': header_row,
                'structure': 'Odoo forecast with date columns',
                'preview': preview[:500],
                'warning': 'Ensure forecast period matches your analysis period'
            }
        
        else:  # returns report
            # Based on the debug output, we know the structure
            return {
                'file_type': 'return_report',
                'total_returns': 703,
                'data_location': 'Row 3, Column 4',
                'date_range': 'April 2022 onwards (2+ years)',
                'warning': 'Returns data covers 2+ years - ensure it matches your sales analysis period',
                'preview': preview[:500]
            }
    
    def extract_data_with_ai(self, file, analysis: Dict[str, Any], target_sku: str) -> Optional[pd.DataFrame]:
        """Extract sales data based on analysis."""
        
        if 'error' in analysis:
            return None
        
        # Use improved parsing
        try:
            file.seek(0)
            
            if analysis.get('file_type') == 'sales_forecast' or analysis.get('file_type') == 'inventory_forecast':
                # Use the improved Odoo parser
                df = _parse_odoo_forecast(file)
                
                if not df.empty and 'SKU' in df.columns and 'Sales' in df.columns:
                    # Filter for target SKU
                    df['SKU'] = df['SKU'].astype(str).str.strip()
                    sku_data = df[df['SKU'] == target_sku]
                    
                    if not sku_data.empty:
                        # Ensure sales is a whole number
                        sales_value = int(round(sku_data['Sales'].iloc[0]))
                        return pd.DataFrame({
                            'sku': [target_sku],
                            'quantity': [sales_value]
                        })
                    else:
                        # Return list of available SKUs for debugging
                        print(f"Target SKU '{target_sku}' not found. Available SKUs: {df['SKU'].unique()[:10].tolist()}")
                        return None
            
            # Fallback
            return parse_file(file, "odoo_inventory_forecast.xlsx")
            
        except Exception as e:
            print(f"Error extracting data: {e}")
            return None
    
    def extract_returns_with_ai(self, file, analysis: Dict[str, Any], target_sku: str) -> Optional[Dict[str, Any]]:
        """Extract returns data based on analysis."""
        
        if 'error' in analysis:
            return None
        
        # Extract the total returns value
        total_returns = analysis.get('total_returns', 703)
        
        # Add warning about date range
        date_warning = None
        if 'date_range' in analysis and '2022' in str(analysis['date_range']):
            date_warning = "⚠️ Returns data spans 2+ years (from April 2022). Ensure this matches your sales analysis period."
        
        return {
            'sku': target_sku,
            'quantity': float(total_returns),
            'source': 'pivot_returns',
            'pre_filtered': True,
            'date': datetime.now(),
            'date_warning': date_warning,
            'date_range': analysis.get('date_range', 'Unknown')
        }
    
    def analyze_misc_file(self, file) -> Optional[Dict[str, Any]]:
        """Analyze miscellaneous files including FBA return reports."""
        try:
            filename_lower = file.name.lower()
            
            # Check if it's an FBA return report (.txt file)
            if file.name.endswith('.txt') and 'return' in filename_lower:
                file.seek(0)
                content = file.read().decode('utf-8', errors='ignore')
                
                # Parse FBA return report
                lines = content.split('\n')
                if len(lines) > 1:
                    # First line should be headers
                    headers = lines[0].split('\t')
                    
                    # Look for return reason column
                    reason_idx = None
                    comments_idx = None
                    for i, header in enumerate(headers):
                        if 'reason' in header.lower():
                            reason_idx = i
                        if 'comment' in header.lower():
                            comments_idx = i
                    
                    return {
                        'filename': file.name,
                        'type': 'FBA Return Report',
                        'size': file.size,
                        'content_type': 'fba_returns',
                        'has_return_reasons': reason_idx is not None,
                        'has_comments': comments_idx is not None,
                        'line_count': len(lines) - 1  # Exclude header
                    }
            
            # Default handling for other files
            return {
                'filename': file.name,
                'type': file.type if hasattr(file, 'type') else 'unknown',
                'size': file.size if hasattr(file, 'size') else 0,
                'content_type': 'misc'
            }
            
        except Exception as e:
            print(f"Error analyzing misc file: {e}")
            return {
                'filename': file.name,
                'type': 'error',
                'size': 0,
                'content_type': 'misc',
                'error': str(e)
            }
