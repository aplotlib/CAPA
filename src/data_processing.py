# src/data_processing.py

"""
Module for cleaning, standardizing, and merging data from various sources.
"""

import pandas as pd
from typing import Dict, List, Optional

def standardize_sales_data(df: pd.DataFrame, report_period_days: int) -> Optional[pd.DataFrame]:
    """
    Standardizes sales summary data from files like the Odoo forecast.

    Args:
        df: A raw DataFrame from a sales summary file.
        report_period_days: The selected reporting period in days (e.g., 30, 90).

    Returns:
        A cleaned DataFrame with standardized columns.
    """
    # Normalize column names to lowercase and strip spaces for reliable mapping
    df.columns = df.columns.str.lower().str.strip()

    # Define the specific sales column to use based on the selected period
    sales_col_name = f'sales last {report_period_days} days'

    # Check if the required sales column and a product identifier exist
    if sales_col_name not in df.columns or 'product' not in df.columns:
        # This file is not the expected Odoo forecast format, return None
        return None

    # Create a new DataFrame with just the essential columns
    # Map 'product' to 'sku' and the dynamic sales column to 'quantity'
    standardized_df = df[['product', sales_col_name]].copy()
    standardized_df.rename(columns={
        'product': 'sku',
        sales_col_name: 'quantity'
    }, inplace=True)

    # Standardize data types
    standardized_df['sku'] = standardized_df['sku'].astype(str)
    standardized_df['quantity'] = pd.to_numeric(standardized_df['quantity'], errors='coerce')

    # Drop rows where essential data is invalid (e.g., non-numeric quantity)
    standardized_df.dropna(subset=['sku', 'quantity'], inplace=True)

    return standardized_df

def standardize_returns_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Standardizes column names and data types for returns data.

    Args:
        df: A raw DataFrame from a returns file.

    Returns:
        A cleaned DataFrame with standardized columns.
    """
    column_mapping = {
        # Standard names
        'return-date': 'return_date',
        'return_date': 'return_date',
        'sku': 'sku',
        'order-id': 'order_id',
        'quantity': 'quantity',
        'reason': 'reason',
        'customer-comments': 'customer_comments',
        
        # Mappings for the user's 'Pivot Return Report' file
        'fnsku': 'sku',
        'return quantity': 'quantity',
        'return reason': 'reason'
    }
    
    df.columns = df.columns.str.lower().str.strip()
    df = df.rename(columns=column_mapping)
    
    required_cols = ['return_date', 'sku', 'quantity', 'reason']
    if not all(col in df.columns for col in required_cols):
        return None
        
    # CRITICAL: Ensure 'return_date' is parsed correctly into a datetime object for filtering
    df['return_date'] = pd.to_datetime(df['return_date'], errors='coerce')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    df['sku'] = df['sku'].astype(str)
    
    if 'customer_comments' not in df.columns:
        df['customer_comments'] = ''
    df['customer_comments'] = df['customer_comments'].fillna('')

    df.dropna(subset=required_cols, inplace=True)
    
    return df

def combine_dataframes(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Concatenates a list of DataFrames into a single DataFrame.
    """
    if not dataframes:
        return pd.DataFrame()
    
    valid_dfs = [df for df in dataframes if df is not None and not df.empty]
    
    if not valid_dfs:
        return pd.DataFrame()
        
    return pd.concat(valid_dfs, ignore_index=True)
