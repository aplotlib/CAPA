# src/data_processing.py

import pandas as pd
import re
from typing import Optional

class DataProcessor:
    """Processes and standardizes data from various sources."""
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initializes the DataProcessor.
        """
        self.api_key = openai_api_key

    def _normalize_sku(self, sku: str) -> str:
        """
        Normalizes a SKU to its parent form.
        Matches the pattern: Letters (Category) + Numbers (ID) -> Strips everything after.
        Example: 
        - MOB1027BLU -> MOB1027
        - MOB1027 -> MOB1027
        - AC-500-RED -> AC-500
        """
        if pd.isna(sku):
            return "UNKNOWN"

        if not isinstance(sku, str):
            sku = str(sku)
            
        sku = sku.strip().upper()
        # Remove common wrapper characters
        sku = sku.strip("[](){}<> ")

        # Regex: Start with 1+ Letters, optional hyphen, 1+ Digits.
        # This captures the "Parent" part and ignores the variant suffix.
        match = re.match(r'^([A-Z]+-?\d+)', sku)
        if match:
            return match.group(1)
        
        # FIX: Fallback logic for SKUs that don't match the specific regex (e.g. numeric SKUs)
        # We assume if there's a space, the first part is the ID
        if ' ' in sku:
            return sku.split(' ')[0]
            
        return sku

    def _find_header_row(self, df: pd.DataFrame, keywords: list) -> Optional[int]:
        """
        Scans the first few rows of a DataFrame to find a row containing specific keywords.
        """
        # 1. Check existing columns
        cols_str = " ".join([str(c) for c in df.columns]).lower()
        if all(k.lower() in cols_str for k in keywords):
            return -1 # Current header is correct

        # 2. Scan first 15 rows
        for i, row in df.head(15).iterrows():
            # Convert row to string, handle potential NaNs
            row_str = " ".join(row.astype(str).fillna('')).lower()
            if all(k.lower() in row_str for k in keywords):
                return i
        return None

    def process_sales_data(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes sales data (e.g., Odoo Forecast).
        Aggregates variants (MOB1027BLU) into parents (MOB1027).
        """
        if sales_df is None or sales_df.empty:
            return pd.DataFrame()
        
        # 1. Header Detection
        # Keywords: 'sku' AND ('sales' OR 'quantity')
        header_idx = self._find_header_row(sales_df, ["sku", "sales"])
        if header_idx is None:
             header_idx = self._find_header_row(sales_df, ["sku", "quantity"])

        if header_idx is not None and header_idx != -1:
            # Set new header
            new_header = sales_df.iloc[header_idx]
            sales_df = sales_df[header_idx + 1:].copy()
            sales_df.columns = new_header
            sales_df.reset_index(drop=True, inplace=True)

        # 2. Column Normalization
        sales_df.columns = [str(c).lower().strip() for c in sales_df.columns]
        
        # Map specific Odoo/Sales columns to 'quantity'
        if 'quantity' not in sales_df.columns:
            if 'sales' in sales_df.columns:
                sales_df.rename(columns={'sales': 'quantity'}, inplace=True)
            elif 'total units' in sales_df.columns: # Fallback for some reports
                sales_df.rename(columns={'total units': 'quantity'}, inplace=True)

        if 'sku' not in sales_df.columns or 'quantity' not in sales_df.columns:
            # Return empty but with correct columns to prevent downstream errors
            print("Error: Sales DataFrame missing 'sku' or 'quantity' column.")
            return pd.DataFrame(columns=['sku', 'quantity'])

        # 3. SKU Normalization & Aggregation
        sales_df['sku'] = sales_df['sku'].apply(self._normalize_sku)
        
        # Clean Quantity
        sales_df['quantity'] = (
            sales_df['quantity']
            .astype(str)
            .str.replace(',', '')
            .apply(pd.to_numeric, errors='coerce')
            .fillna(0)
        )
        
        # Group sum by parent SKU
        processed_df = sales_df.groupby('sku')['quantity'].sum().reset_index()
        return processed_df

    def process_returns_data(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes returns data (Nested Pivot Reports).
        Aggregates variants into parents.
        """
        if returns_df is None or returns_df.empty:
            return pd.DataFrame()

        # Strategy A: Standard CSV check
        clean_cols = [str(c).lower().strip() for c in returns_df.columns]
        if 'sku' in clean_cols and 'quantity' in clean_cols:
            returns_df.columns = clean_cols
            returns_df['sku'] = returns_df['sku'].apply(self._normalize_sku)
            returns_df['quantity'] = pd.to_numeric(returns_df['quantity'], errors='coerce').fillna(0)
            return returns_df.groupby('sku')['quantity'].sum().reset_index()

        # Strategy B: Pivot Report Parsing
        extracted_data = []
        # Typically the hierarchy is in the first column
        first_col = returns_df.columns[0]
        
        for index, row in returns_df.iterrows():
            cell_text = str(row[first_col]).strip()
            
            # 1. Try Extracting from Brackets [] or ()
            # Looks for [MOB1027BLU] or (MOB1027BLU)
            match = re.search(r'[\[\(](.*?)[\]\)]', cell_text)
            
            # 2. If no brackets, look for raw SKU pattern (Letters+Numbers) in the text
            if not match:
                # Look for sequence like MOB1027BLU
                match = re.search(r'([A-Z]{3,}-?\d+)', cell_text.upper())

            if match:
                raw_sku = match.group(1).strip()
                parent_sku = self._normalize_sku(raw_sku)
                
                # 3. Find Quantity (Last valid number in the row)
                # Pivot tables often have monthly cols, then a Total col at the end.
                qty = 0
                for val in reversed(row.values):
                    try:
                        val_str = str(val).replace(',', '').strip()
                        # Check if it's a number (allow float)
                        if val_str and val_str.replace('.', '', 1).isdigit():
                            qty = float(val_str)
                            # We found the total (last col), stop looking
                            break
                    except:
                        continue
                
                # Only add if we found a positive return quantity
                if qty > 0:
                    extracted_data.append({'sku': parent_sku, 'quantity': qty})

        if extracted_data:
            processed_df = pd.DataFrame(extracted_data)
            # Sum up all variants (MOB1027BLU + MOB1027RED -> MOB1027 total)
            return processed_df.groupby('sku')['quantity'].sum().reset_index()

        # Strategy C: Fallback
        return self._fallback_standard_process(returns_df)

    def _fallback_standard_process(self, df: pd.DataFrame) -> pd.DataFrame:
        sku_col = next((c for c in df.columns if 'sku' in str(c).lower()), None)
        qty_col = next((c for c in df.columns if any(x in str(c).lower() for x in ['qty', 'quantity', 'sales', 'return'])), None)

        if sku_col and qty_col:
            df = df.rename(columns={sku_col: 'sku', qty_col: 'quantity'})
            df['sku'] = df['sku'].apply(self._normalize_sku)
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
            return df.groupby('sku')['quantity'].sum().reset_index()
            
        return pd.DataFrame()
