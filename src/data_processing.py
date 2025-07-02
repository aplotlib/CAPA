# src/data_processing.py

"""
Module for cleaning, standardizing, and merging data from various sources.
This version uses a highly robust and flexible column identification method.
"""

import pandas as pd
from typing import List, Optional

def _find_column_name(df_columns: list, possible_names: list) -> Optional[str]:
    """
    Finds the first matching original column name from a list of possibilities,
    ignoring case and leading/trailing whitespace.
    """
    # Create a mapping of cleaned column names (lowercase, stripped) to their original format
    column_map = {col.lower().strip(): col for col in df_columns}
    for name in possible_names:
        cleaned_name = name.lower().strip()
        if cleaned_name in column_map:
            # Return the original, case-sensitive column name
            return column_map[cleaned_name]
    return None

def standardize_sales_data(df: pd.DataFrame, report_period_days: int) -> Optional[pd.DataFrame]:
    """
    Standardizes sales summary data with robust, flexible column finding.
    """
    # Use the helper to find columns, allowing for variations like 'Product' or 'product'
    sku_col = _find_column_name(df.columns, ['Product', 'SKU'])
    quantity_col = _find_column_name(df.columns, [f'Sales Last {report_period_days} Days'])

    # If either essential column isn't found, the file is not compatible
    if not sku_col or not quantity_col:
        return None

    # Create the standardized DataFrame using the found column names
    standardized_df = pd.DataFrame({
        'sku': df[sku_col],
        'quantity': df[quantity_col]
    })

    # Standardize data types and clean up data
    standardized_df['sku'] = standardized_df['sku'].astype(str)
    standardized_df['quantity'] = pd.to_numeric(standardized_df['quantity'], errors='coerce')
    standardized_df.dropna(subset=['sku', 'quantity'], inplace=True)
    
    # Exclude items with zero sales from the analysis
    standardized_df = standardized_df[standardized_df['quantity'] > 0]

    return standardized_df

def standardize_returns_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Standardizes returns data with robust, flexible column finding.
    """
    # Find each required and optional column using a list of possible names
    date_col = _find_column_name(df.columns, ['Return date', 'return-date'])
    sku_col = _find_column_name(df.columns, ['FNSKU', 'SKU'])
    quantity_col = _find_column_name(df.columns, ['Quantity', 'Return Quantity'])
    reason_col = _find_column_name(df.columns, ['Return reason', 'Reason'])
    comments_col = _find_column_name(df.columns, ['Customer comments', 'customer-comments'])

    # If any of the essential columns are missing, we cannot proceed
    if not all([date_col, sku_col, quantity_col, reason_col]):
        return None

    # Build the standardized DataFrame
    standardized_df = pd.DataFrame({
        'return_date': df[date_col],
        'sku': df[sku_col],
        'quantity': df[quantity_col],
        'reason': df[reason_col]
    })

    # Include optional customer comments column if it exists
    if comments_col:
        standardized_df['customer_comments'] = df[comments_col].fillna('')
    else:
        standardized_df['customer_comments'] = ''

    # Standardize data types and clean up
    standardized_df['return_date'] = pd.to_datetime(standardized_df['return_date'], errors='coerce')
    standardized_df['quantity'] = pd.to_numeric(standardized_df['quantity'], errors='coerce')
    standardized_df['sku'] = standardized_df['sku'].astype(str)
    standardized_df.dropna(subset=['return_date', 'sku', 'quantity', 'reason'], inplace=True)

    return standardized_df

def combine_dataframes(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """Concatenates a list of DataFrames into a single DataFrame."""
    if not dataframes:
        return pd.DataFrame()
    
    valid_dfs = [df for df in dataframes if df is not None and not df.empty]
    
    if not valid_dfs:
        return pd.DataFrame()
        
    return pd.concat(valid_dfs, ignore_index=True)
