# src/data_processing.py

"""
Module for cleaning and standardizing data.
Now tailored for the specific Odoo file format.
"""

import pandas as pd
from typing import List, Optional

def _find_column_name(df_columns: list, possible_names: list) -> Optional[str]:
    """Finds the first matching original column name from a list of possibilities."""
    column_map = {col.lower().strip(): col for col in df_columns}
    for name in possible_names:
        cleaned_name = name.lower().strip()
        if cleaned_name in column_map:
            return column_map[cleaned_name]
    return None

def standardize_sales_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Standardizes sales data from the Odoo file format.
    """
    # Find columns based on the new, correct names from the Odoo file
    sku_col = _find_column_name(df.columns, ['SKU'])
    sales_col = _find_column_name(df.columns, ['Sales'])
    on_hand_col = _find_column_name(df.columns, ['On Hand'])

    # SKU and Sales are essential for the analysis
    if not sku_col or not sales_col:
        return None

    standardized_df = pd.DataFrame({
        'sku': df[sku_col],
        'quantity': df[sales_col] # Using the 'Sales' column as the quantity sold
    })

    # Include 'on_hand' quantity if available
    if on_hand_col:
        standardized_df['on_hand'] = pd.to_numeric(df[on_hand_col], errors='coerce')

    standardized_df['sku'] = standardized_df['sku'].astype(str)
    standardized_df['quantity'] = pd.to_numeric(standardized_df['quantity'], errors='coerce')
    standardized_df.dropna(subset=['sku', 'quantity'], inplace=True)

    return standardized_df

def standardize_returns_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Standardizes returns data from a standard (non-pivot) report.
    """
    date_col = _find_column_name(df.columns, ['Return date', 'return-date'])
    sku_col = _find_column_name(df.columns, ['FNSKU', 'SKU'])
    quantity_col = _find_column_name(df.columns, ['Quantity', 'Return Quantity'])
    reason_col = _find_column_name(df.columns, ['Return reason', 'Reason'])

    # This will fail with the pivot table because there is no SKU column.
    if not all([date_col, sku_col, quantity_col, reason_col]):
        return None

    # This part of the code will execute once a valid returns file is provided
    standardized_df = pd.DataFrame({
        'return_date': df[date_col], 'sku': df[sku_col],
        'quantity': df[quantity_col], 'reason': df[reason_col]
    })
    standardized_df['return_date'] = pd.to_datetime(standardized_df['return_date'], errors='coerce')
    standardized_df['quantity'] = pd.to_numeric(standardized_df['quantity'], errors='coerce')
    standardized_df.dropna(subset=['return_date', 'sku', 'quantity'], inplace=True)
    return standardized_df

def combine_dataframes(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """Concatenates a list of DataFrames into a single DataFrame."""
    if not dataframes: return pd.DataFrame()
    valid_dfs = [df for df in dataframes if df is not None and not df.empty]
    if not valid_dfs: return pd.DataFrame()
    return pd.concat(valid_dfs, ignore_index=True)
