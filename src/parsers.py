# src/parsers.py

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from io import BytesIO, StringIO
import json
import anthropic
import base64
from datetime import datetime

class AIFileParser:
    """AI-powered file parser that can understand various Excel formats."""
    
    def __init__(self, anthropic_api_key: str):
        """Initialize with Anthropic API client."""
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model = "claude-3-5-sonnet-20241022"  # Use latest Sonnet model
        
    def _read_excel_safely(self, file) -> Tuple[Dict[str, pd.DataFrame], str]:
        """Read Excel file and return all sheets with preview."""
        try:
            file.seek(0)
            # Read all sheets
            excel_file = pd.ExcelFile(file)
            sheets = {}
            preview_text = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet_name, header=None)
                sheets[sheet_name] = df
                
                # Create text preview of first 20 rows
                preview_text.append(f"\n=== Sheet: {sheet_name} ===")
                preview_text.append(f"Shape: {df.shape}")
                preview_text.append("First 20 rows:")
                preview_text.append(df.head(20).to_string())
                
            file.seek(0)
            return sheets, "\n".join(preview_text)
            
        except Exception as e:
            print(f"Error reading Excel file: {e}")
            return {}, f"Error: {str(e)}"
    
    def analyze_file_structure(self, file, file_type: str, target_sku: str) -> Dict[str, Any]:
        """Use AI to analyze the file structure and identify data locations."""
        
        # Read the file
        sheets, preview = self._read_excel_safely(file)
        
        if not sheets:
            return {"error": "Could not read file", "preview": preview}
        
        # Prepare prompt for AI
        if file_type == "sales_forecast":
            prompt = f"""
            Analyze this Odoo Inventory Forecast Excel file structure. I need to extract sales data for SKU: {target_sku}
            
            File preview:
            {preview}
            
            Please analyze and return a JSON response with:
            1. "file_type": Confirm this is an Odoo sales forecast
            2. "structure": Describe the file structure (pivot table, regular table, etc.)
            3. "data_location": Which sheet and rows contain the actual data
            4. "header_row": Which row contains column headers (0-indexed)
            5. "sku_column": Which column contains SKU codes
            6. "sales_column": Which column contains sales quantities
            7. "columns_found": List all column names you can identify
            8. "available_skus": List up to 10 SKUs you can see in the data
            9. "extraction_strategy": How to best extract data for the target SKU
            
            Return ONLY a valid JSON object.
            """
        else:  # returns_pivot
            prompt = f"""
            Analyze this Pivot Return Report Excel file structure. This file is pre-filtered for SKU: {target_sku}
            
            File preview:
            {preview}
            
            Please analyze and return a JSON response with:
            1. "file_type": Confirm this is a returns pivot report
            2. "structure": Describe the file structure
            3. "pre_filtered": Is this file pre-filtered for a single SKU? (true/false)
            4. "total_returns_location": Where is the total returns value? (sheet, row, column)
            5. "data_start_row": Where does actual return data start?
            6. "has_sku_column": Does it have a SKU column? (true/false)
            7. "return_quantity": What is the total return quantity you can identify?
            8. "extraction_strategy": How to extract the total returns for this SKU
            
            Return ONLY a valid JSON object.
            """
        
        try:
            # Call AI to analyze structure
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Parse AI response
            ai_analysis = json.loads(response.content[0].text)
            ai_analysis['sheets_available'] = list(sheets.keys())
            ai_analysis['preview'] = preview[:500]  # Store partial preview
            
            return ai_analysis
            
        except json.JSONDecodeError as e:
            return {
                "error": "AI response was not valid JSON",
                "raw_response": response.content[0].text if 'response' in locals() else None,
                "preview": preview[:500]
            }
        except Exception as e:
            return {
                "error": f"AI analysis failed: {str(e)}",
                "preview": preview[:500]
            }
    
    def extract_data_with_ai(self, file, analysis: Dict[str, Any], target_sku: str) -> Optional[pd.DataFrame]:
        """Extract sales data based on AI analysis."""
        
        if 'error' in analysis:
            print(f"Cannot extract data due to analysis error: {analysis['error']}")
            return None
        
        try:
            # Read the file again
            file.seek(0)
            
            # Determine which sheet to read
            sheet_name = 0  # Default to first sheet
            if 'data_location' in analysis and isinstance(analysis['data_location'], dict):
                sheet_name = analysis['data_location'].get('sheet', 0)
            
            # Determine header row
            header_row = analysis.get('header_row', 1)  # Odoo usually has header at row 1
            
            # Read with identified header
            df = pd.read_excel(file, sheet_name=sheet_name, header=header_row)
            
            # Clean column names
            df.columns = df.columns.astype(str).str.strip()
            
            # Find SKU and sales columns using AI suggestions or common patterns
            sku_col = None
            sales_col = None
            
            # Try AI-suggested columns first
            if 'sku_column' in analysis:
                for col in df.columns:
                    if analysis['sku_column'].lower() in col.lower():
                        sku_col = col
                        break
            
            if 'sales_column' in analysis:
                for col in df.columns:
                    if analysis['sales_column'].lower() in col.lower():
                        sales_col = col
                        break
            
            # Fallback to pattern matching
            if not sku_col:
                for col in df.columns:
                    if 'sku' in col.lower() or 'product' in col.lower() or 'item' in col.lower():
                        sku_col = col
                        break
            
            if not sales_col:
                for col in df.columns:
                    if 'sales' in col.lower() or 'quantity' in col.lower() or 'qty' in col.lower():
                        sales_col = col
                        break
            
            if not sku_col or not sales_col:
                # Try asking AI to identify columns from actual data
                sample_data = df.head(10).to_string()
                identify_prompt = f"""
                Looking at this data sample, identify the SKU and Sales quantity columns:
                
                {sample_data}
                
                Target SKU: {target_sku}
                
                Return a JSON with:
                {{"sku_column": "exact column name", "sales_column": "exact column name"}}
                """
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": identify_prompt}]
                )
                
                try:
                    col_mapping = json.loads(response.content[0].text)
                    sku_col = col_mapping.get('sku_column')
                    sales_col = col_mapping.get('sales_column')
                except:
                    pass
            
            if sku_col and sales_col and sku_col in df.columns and sales_col in df.columns:
                # Filter for target SKU
                df[sku_col] = df[sku_col].astype(str).str.strip()
                sku_data = df[df[sku_col] == target_sku].copy()
                
                if sku_data.empty:
                    # Try case-insensitive match
                    sku_data = df[df[sku_col].str.upper() == target_sku.upper()].copy()
                
                if not sku_data.empty:
                    # Prepare return data
                    result = pd.DataFrame({
                        'sku': sku_data[sku_col],
                        'quantity': pd.to_numeric(sku_data[sales_col], errors='coerce'),
                        'source': 'sales_forecast'
                    })
                    
                    # Add date if available
                    date_col = None
                    for col in df.columns:
                        if 'date' in col.lower():
                            date_col = col
                            break
                    
                    if date_col:
                        result['date'] = sku_data[date_col]
                    else:
                        result['date'] = datetime.now()
                    
                    return result.dropna(subset=['quantity'])
                else:
                    # Store available SKUs for debugging
                    analysis['available_skus'] = df[sku_col].unique()[:20].tolist()
            
            return None
            
        except Exception as e:
            print(f"Error extracting sales data: {e}")
            return None
    
    def extract_returns_with_ai(self, file, analysis: Dict[str, Any], target_sku: str) -> Optional[Dict[str, Any]]:
        """Extract returns data from a pre-filtered pivot report."""
        
        if 'error' in analysis:
            print(f"Cannot extract returns due to analysis error: {analysis['error']}")
            return None
        
        try:
            # Read all sheets
            sheets, _ = self._read_excel_safely(file)
            
            if not sheets:
                return None
            
            # For a pre-filtered pivot report, we need to find the total
            total_returns = None
            
            # Try AI-suggested location first
            if 'total_returns_location' in analysis:
                loc = analysis['total_returns_location']
                if isinstance(loc, dict):
                    sheet = loc.get('sheet', 0)
                    row = loc.get('row', 0)
                    col = loc.get('column', 0)
                    
                    sheet_name = list(sheets.keys())[0] if isinstance(sheet, int) else sheet
                    if sheet_name in sheets:
                        df = sheets[sheet_name]
                        try:
                            value = df.iloc[row, col]
                            total_returns = pd.to_numeric(value, errors='coerce')
                        except:
                            pass
            
            # If not found, try to extract from AI analysis directly
            if total_returns is None and 'return_quantity' in analysis:
                total_returns = pd.to_numeric(analysis['return_quantity'], errors='coerce')
            
            # If still not found, scan the data for numeric values
            if total_returns is None:
                # Use AI to find the total
                df = list(sheets.values())[0]  # First sheet
                data_sample = df.to_string()
                
                find_total_prompt = f"""
                This is a pivot table showing returns for SKU: {target_sku}
                Find the TOTAL RETURNS value in this data:
                
                {data_sample[:3000]}
                
                What is the total return quantity? Return ONLY the number.
                """
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=100,
                    messages=[{"role": "user", "content": find_total_prompt}]
                )
                
                try:
                    total_returns = float(response.content[0].text.strip())
                except:
                    # Last resort - sum all numeric values that look like quantities
                    for sheet_name, df in sheets.items():
                        # Skip first few rows (usually headers)
                        data_portion = df.iloc[4:, 1:]  # Common pattern for pivot tables
                        numeric_data = data_portion.apply(pd.to_numeric, errors='coerce')
                        
                        # Sum all positive values
                        total = numeric_data.sum().sum()
                        if total > 0:
                            total_returns = total
                            break
            
            if total_returns is not None and total_returns > 0:
                return {
                    'sku': target_sku,
                    'quantity': float(total_returns),
                    'source': 'pivot_returns',
                    'pre_filtered': True,
                    'date': datetime.now()
                }
            
            return None
            
        except Exception as e:
            print(f"Error extracting returns data: {e}")
            return None
    
    def analyze_misc_file(self, file) -> Optional[Dict[str, Any]]:
        """Analyze miscellaneous files (images, PDFs, etc.)."""
        
        file_info = {
            'filename': file.name,
            'type': file.type,
            'size': file.size
        }
        
        # Handle different file types
        if file.type.startswith('image/'):
            # For images, we could use vision API in the future
            file_info['content_type'] = 'image'
            file_info['description'] = f"Image file: {file.name}"
            
        elif file.type == 'application/pdf':
            # For PDFs, we could extract text in the future
            file_info['content_type'] = 'pdf'
            file_info['description'] = f"PDF document: {file.name}"
            
        elif file.type in ['text/plain', 'text/csv']:
            # Read text files
            try:
                content = file.read().decode('utf-8')
                file_info['content_type'] = 'text'
                file_info['preview'] = content[:500]
                file.seek(0)
            except:
                file_info['content_type'] = 'binary'
        
        else:
            file_info['content_type'] = 'other'
        
        return file_info
