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

    def _normalize_sku(self, sku: str) -> str:
        """
        Normalizes a SKU to its parent form based on the pattern:
        Category (3 letters) + Parent ID (4 digits) + Variant (optional suffix).
        Example: MOB1027BLU -> MOB1027
        """
        if not isinstance(sku, str):
            return str(sku)
            
        sku = sku.strip().upper()
        # Pattern: Start with 3 letters, then 4 digits. Capture that group.
        # Everything after is considered a variant suffix.
        match = re.match(r'^([A-Z]{3}\d{4})', sku)
        if match:
            return match.group(1)
        return sku

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
        Aggregates variants to parent SKUs.
        """
        if sales_df is None or sales_df.empty:
            return pd.DataFrame()
        
        # 1. Detect and Fix Header
        header_idx = self._find_header_row(sales_df, ["sku", "sales"])
        if header_idx is None:
             header_idx = self._find_header_row(sales_df, ["sku", "quantity"])

        if header_idx is not None and header_idx != -1:
            new_header = sales_df.iloc[header_idx]
            sales_df = sales_df[header_idx + 1:].copy()
            sales_df.columns = new_header
            sales_df.reset_index(drop=True, inplace=True)

        # 2. Normalize Columns
        sales_df.columns = [str(c).lower().strip() for c in sales_df.columns]
        
        # Map 'Sales' to 'quantity'
        if 'quantity' not in sales_df.columns and 'sales' in sales_df.columns:
            sales_df.rename(columns={'sales': 'quantity'}, inplace=True)

        if 'sku' not in sales_df.columns or 'quantity' not in sales_df.columns:
            print("Error: Sales DataFrame missing 'sku' or 'quantity/sales' column.")
            return pd.DataFrame()

        # 3. Clean Data & Normalize SKUs
        sales_df['sku'] = sales_df['sku'].astype(str).apply(self._normalize_sku)
        
        sales_df['quantity'] = (
            sales_df['quantity']
            .astype(str)
            .str.replace(',', '')
            .apply(pd.to_numeric, errors='coerce')
            .fillna(0)
        )
        
        # Group by normalized SKU
        processed_df = sales_df.groupby('sku').agg({'quantity': 'sum'}).reset_index()
        return processed_df

    def process_returns_data(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes and normalizes returns data.
        Handles standard CSVs and Nested Pivot Return Reports.
        Aggregates variants to parent SKUs.
        """
        if returns_df is None or returns_df.empty:
            return pd.DataFrame()

        # Strategy A: Standard Clean CSV
        clean_cols = [str(c).lower().strip() for c in returns_df.columns]
        if 'sku' in clean_cols and 'quantity' in clean_cols:
            returns_df.columns = clean_cols
            returns_df['sku'] = returns_df['sku'].astype(str).apply(self._normalize_sku)
            returns_df['quantity'] = pd.to_numeric(returns_df['quantity'], errors='coerce').fillna(0)
            return returns_df.groupby('sku')['quantity'].sum().reset_index()

        # Strategy B: Pivot Return Report
        extracted_data = []
        first_col = returns_df.columns[0]
        
        for index, row in returns_df.iterrows():
            cell_text = str(row[first_col])
            # Look for [SKU] pattern
            match = re.search(r'\[(.*?)\]', cell_text)
            
            if match:
                raw_sku = match.group(1).strip()
                parent_sku = self._normalize_sku(raw_sku)
                
                # Find quantity (last valid number in row)
                qty = 0
                for val in reversed(row.values):
                    try:
                        val_str = str(val).replace(',', '').strip()
                        if val_str and val_str.replace('.', '', 1).isdigit():
                            qty = float(val_str)
                            break
                    except:
                        continue
                
                if qty > 0:
                    extracted_data.append({'sku': parent_sku, 'quantity': qty})

        if extracted_data:
            processed_df = pd.DataFrame(extracted_data)
            return processed_df.groupby('sku')['quantity'].sum().reset_index()

        # Strategy C: Fallback
        print("Warning: Could not parse Returns file as Pivot Report. Attempting fallback.")
        return self._fallback_standard_process(returns_df)

    def _fallback_standard_process(self, df: pd.DataFrame) -> pd.DataFrame:
        sku_col = next((c for c in df.columns if 'sku' in str(c).lower()), None)
        qty_col = next((c for c in df.columns if any(x in str(c).lower() for x in ['qty', 'quantity', 'sales', 'return'])), None)

        if sku_col and qty_col:
            df = df.rename(columns={sku_col: 'sku', qty_col: 'quantity'})
            df['sku'] = df['sku'].astype(str).apply(self._normalize_sku)
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
            return df.groupby('sku')['quantity'].sum().reset_index()
            
        return pd.DataFrame()
