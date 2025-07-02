# src/data_processing.py

"""
Module for standardizing data based on the new workflow:
- Filters sales data for a user-provided SKU.
- Assigns a total return quantity to that same SKU.
"""

import pandas as pd
from typing import Optional

def _find_column_name(df_columns: list, possible_names: list) -> Optional[str]:
    """Finds the first matching original column name from a list of possibilities."""
    column_map = {col.lower().strip(): col for col in df_columns}
    for name in possible_names:
        cleaned_name = name.lower().strip()
        if cleaned_name in column_map:
            return column_map[cleaned_name]
    return None

def standardize_sales_data(df: pd.DataFrame, target_sku: str) -> Optional[pd.DataFrame]:
    """
    Processes the Odoo sales data, standardizes it, and filters for the target SKU.
    """
    sku_col = _find_column_name(df.columns, ['SKU'])
    sales_col = _find_column_name(df.columns, ['Sales'])

    if not sku_col or not sales_col:
        return None

    # Standardize column names for consistency
    df = df.rename(columns={sku_col: 'sku', sales_col: 'quantity'})

    # Filter the DataFrame to get the data for only the SKU the user entered
    product_data = df[df['sku'] == target_sku].copy()

    if product_data.empty:
        return None # Return None if the SKU was not found in the sales file

    product_data['quantity'] = pd.to_numeric(product_data['quantity'], errors='coerce')
    product_data.dropna(subset=['sku', 'quantity'], inplace=True)

    return product_data[['sku', 'quantity']]

def standardize_returns_data(df: pd.DataFrame, target_sku: str) -> Optional[pd.DataFrame]:
    """
    Processes the parsed pivot table data and assigns the total returns to the target SKU.
    """
    # The parser now returns a df with one column: 'total_returned_quantity'
    if 'total_returned_quantity' not in df.columns or df.empty:
        return None

    total_returns = df['total_returned_quantity'].iloc[0]

    # Create a new DataFrame assigning the total returns to the user-provided SKU
    standardized_df = pd.DataFrame({
        'sku': [target_sku],
        'quantity': [total_returns]
    })
    
    return standardized_df
