# src/data_processing.py

import pandas as pd
import re
from typing import Optional

class DataProcessor:
    """Processes and standardizes data from various sources."""
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initializes the DataProcessor.
        The API key is passed for potential future AI-driven data cleaning or validation features.
        """
        self.api_key = openai_api_key

    def _find_header_row(self, df: pd.DataFrame, keywords: list) -> Optional[int]:
        """
        Scans the first few rows of a DataFrame to find a row containing specific keywords.
        Returns the index of the row if found, otherwise None.
        """
        # check columns first
        if any(k.lower() in str(c).lower() for c in df.columns for k in keywords):
            return -1 # Header is already correct

        # Scan first 10 rows
        for i, row in df.head(10).iterrows():
            row_str = " ".join(row.astype(str)).lower()
            if all(k.lower() in row_str for k in keywords):
                return i
        return None

    def process_sales_data(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes and normalizes sales data.
        Handles standard CSVs and Odoo Inventory Forecast exports.
        """
        if sales_df is None or sales_df.empty:
            return pd.DataFrame()
        
        # 1. Detect and Fix Header
        # Look for "sku" and ("quantity" or "sales")
        header_idx = self._find_header_row(sales_df, ["sku", "sales"])
        if header_idx is None:
             header_idx = self._find_header_row(sales_df, ["sku", "quantity"])

        if header_idx is not None and header_idx != -1:
            # Promote row to header
            new_header = sales_df.iloc[header_idx]
            sales_df = sales_df[header_idx + 1:].copy()
            sales_df.columns = new_header
            sales_df.reset_index(drop=True, inplace=True)

        # 2. Normalize Columns
        sales_df.columns = [str(c).lower().strip() for c in sales_df.columns]
        
        # Map 'Sales' to 'quantity' if 'quantity' doesn't exist
        if 'quantity' not in sales_df.columns and 'sales' in sales_df.columns:
            sales_df.rename(columns={'sales': 'quantity'}, inplace=True)

        # Ensure required columns exist
        if 'sku' not in sales_df.columns or 'quantity' not in sales_df.columns:
            # Fallback: Try to find SKU in 'product title' or similar if explicit SKU col is missing?
            # For now, strict check to avoid bad data.
            print("Error: Sales DataFrame missing 'sku' or 'quantity/sales' column.")
            return pd.DataFrame()

        # 3. Clean Data
        sales_df['sku'] = sales_df['sku'].astype(str).str.strip()
        # Remove commas and convert to numeric
        sales_df['quantity'] = (
            sales_df['quantity']
            .astype(str)
            .str.replace(',', '')
            .apply(pd.to_numeric, errors='coerce')
            .fillna(0)
        )
        
        # Group by SKU and sum
        processed_df = sales_df.groupby('sku').agg({'quantity': 'sum'}).reset_index()
        return processed_df

    def process_returns_data(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes and normalizes returns data.
        Handles standard CSVs and Nested Pivot Return Reports.
        """
        if returns_df is None or returns_df.empty:
            return pd.DataFrame()

        # Strategy A: Standard Clean CSV (sku, quantity)
        # Check if we have standard headers
        clean_cols = [str(c).lower().strip() for c in returns_df.columns]
        if 'sku' in clean_cols and 'quantity' in clean_cols:
            returns_df.columns = clean_cols
            returns_df['sku'] = returns_df['sku'].astype(str).str.strip()
            returns_df['quantity'] = pd.to_numeric(returns_df['quantity'], errors='coerce').fillna(0)
            return returns_df.groupby('sku')['quantity'].sum().reset_index()

        # Strategy B: Pivot Return Report (Complex Parsing)
        # The file has SKUs embedded in strings like "[SKU] Product Name" 
        # and the total quantity is often the last column.
        
        extracted_data = []
        
        # Iterate through rows to find SKU patterns
        # We look at the first column for the SKU pattern
        first_col = returns_df.columns[0]
        
        for index, row in returns_df.iterrows():
            # Check first column for "[SKU]" pattern
            cell_text = str(row[first_col])
            match = re.search(r'\[(.*?)\]', cell_text)
            
            if match:
                sku = match.group(1).strip()
                
                # Assume the Total Quantity is in the last column
                # We iterate backwards to find the first valid number
                qty = 0
                for val in reversed(row.values):
                    try:
                        # Try to parse as float (handles strings with numbers)
                        # We ignore cell_text itself if it ends up being the last column (unlikely but possible)
                        val_str = str(val).replace(',', '').strip()
                        if val_str and val_str.replace('.', '', 1).isdigit():
                            qty = float(val_str)
                            break
                    except:
                        continue
                
                if qty > 0:
                    extracted_data.append({'sku': sku, 'quantity': qty})

        if extracted_data:
            processed_df = pd.DataFrame(extracted_data)
            # Sum duplicates if the same SKU appears multiple times (e.g. under different months)
            return processed_df.groupby('sku')['quantity'].sum().reset_index()

        # Strategy C: Fallback to standard processing if Regex failed
        # (This handles the case where maybe headers were just lowercase/uppercase mismatch)
        print("Warning: Could not parse Returns file as Pivot Report. Attempting fallback.")
        return self._fallback_standard_process(returns_df)

    def _fallback_standard_process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Helper to try and process a generic DF if specific strategies fail."""
        # Try to find SKU col
        sku_col = next((c for c in df.columns if 'sku' in str(c).lower()), None)
        # Try to find Qty col
        qty_col = next((c for c in df.columns if any(x in str(c).lower() for x in ['qty', 'quantity', 'sales', 'return'])), None)

        if sku_col and qty_col:
            df = df.rename(columns={sku_col: 'sku', qty_col: 'quantity'})
            df['sku'] = df['sku'].astype(str).str.strip()
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
            return df.groupby('sku')['quantity'].sum().reset_index()
            
        return pd.DataFrame()
