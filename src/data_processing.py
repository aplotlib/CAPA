# src/data_processing.py

"""
Module for cleaning, standardizing, and merging data from various sources.
"""

import pandas as pd
from typing import Dict, List, Optional

def standardize_sales_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Standardizes column names and data types for sales data.

    Args:
        df: A raw DataFrame from a sales file.

    Returns:
        A cleaned DataFrame with standardized columns, or None if essential columns are missing.
    """
    column_mapping = {
        'date': 'order_date',
        'order date': 'order_date',
        'purchase date': 'order_date',
        'order_date': 'order_date',
        'sku': 'sku',
        'product sku': 'sku',
        'product_sku': 'sku',
        'item_sku': 'sku',
        'quantity': 'quantity',
        'qty': 'quantity',
        'units': 'quantity',
        'order id': 'order_id',
        'order_id': 'order_id',
        'order number': 'order_id',
        'channel': 'channel',
        'sales channel': 'channel',
        'marketplace': 'channel',
    }
    
    # Normalize column names to lowercase and strip spaces
    df.columns = df.columns.str.lower().str.strip()
    df = df.rename(columns=column_mapping)

    # Check for essential columns
    required_cols = ['order_date', 'sku', 'quantity']
    if not all(col in df.columns for col in required_cols):
        return None

    # Standardize data types
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    df['sku'] = df['sku'].astype(str)

    # Drop rows where essential data is invalid
    df.dropna(subset=required_cols, inplace=True)
    
    return df

def standardize_returns_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Standardizes column names and data types for returns data.

    Args:
        df: A raw DataFrame from a returns file.

    Returns:
        A cleaned DataFrame with standardized columns, or None if essential columns are missing.
    """
    column_mapping = {
        'return-date': 'return_date',
        'return_date': 'return_date',
        'sku': 'sku',
        'order-id': 'order_id',
        'order id': 'order_id',
        'asin': 'asin',
        'product-name': 'product_name',
        'quantity': 'quantity',
        'reason': 'reason',
        'return reason': 'reason',
        'customer-comments': 'customer_comments',
        'customer comments': 'customer_comments',
        'comments': 'customer_comments',
        'detailed-disposition': 'disposition'
    }
    
    df.columns = df.columns.str.lower().str.strip()
    df = df.rename(columns=column_mapping)
    
    required_cols = ['return_date', 'sku', 'quantity', 'reason']
    if not all(col in df.columns for col in required_cols):
        return None
        
    df['return_date'] = pd.to_datetime(df['return_date'], errors='coerce')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    df['sku'] = df['sku'].astype(str)
    
    # Fill missing comments with empty string to avoid errors in analysis
    if 'customer_comments' not in df.columns:
        df['customer_comments'] = ''
    df['customer_comments'] = df['customer_comments'].fillna('')

    df.dropna(subset=required_cols, inplace=True)
    
    return df

def combine_dataframes(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Concatenates a list of DataFrames into a single DataFrame.

    Args:
        dataframes: A list of pandas DataFrames to combine.

    Returns:
        A single, combined DataFrame.
    """
    if not dataframes:
        return pd.DataFrame()
    
    # Filter out empty or None dataframes before concatenation
    valid_dfs = [df for df in dataframes if df is not None and not df.empty]
    
    if not valid_dfs:
        return pd.DataFrame()
        
    return pd.concat(valid_dfs, ignore_index=True)

def process_manual_entries(manual_entries: List[Dict], data_type: str) -> Optional[pd.DataFrame]:
    """

    Converts a list of manual entry dictionaries to a standardized DataFrame.

    Args:
        manual_entries: A list of dictionaries, where each is a manual entry.
        data_type: The type of data ('sales' or 'returns').

    Returns:
        A standardized DataFrame of the manual entries.
    """
    if not manual_entries:
        return None

    manual_df = pd.DataFrame(manual_entries)
    manual_df['source'] = 'manual_entry'
    
    if data_type == 'sales':
        return standardize_sales_data(manual_df)
    elif data_type == 'returns':
        return standardize_returns_data(manual_df)
    
    return None
