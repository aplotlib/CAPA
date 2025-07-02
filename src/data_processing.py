# src/data_processing.py
import pandas as pd
from typing import Optional
def _find_column_name(df_columns: list, possible_names: list) -> Optional[str]:
    column_map = {str(col).lower().strip(): str(col) for col in df_columns}
    for name in possible_names:
        if name.lower().strip() in column_map: return column_map[name.lower().strip()]
    return None
def standardize_sales_data(df: pd.DataFrame, target_sku: str) -> Optional[pd.DataFrame]:
    sku_col = _find_column_name(df.columns, ['SKU']); sales_col = _find_column_name(df.columns, ['Sales'])
    if not sku_col or not sales_col: return None
    df[sku_col] = df[sku_col].astype(str)
    df = df.rename(columns={sku_col: 'sku', sales_col: 'quantity'})
    product_data = df[df['sku'] == target_sku].copy()
    if product_data.empty: return None
    product_data['quantity'] = pd.to_numeric(product_data['quantity'], errors='coerce')
    product_data.dropna(subset=['sku', 'quantity'], inplace=True)
    return product_data[['sku', 'quantity']]
def standardize_returns_data(df: pd.DataFrame, target_sku: str) -> Optional[pd.DataFrame]:
    if 'total_returned_quantity' not in df.columns or df.empty: return None
    total_returns = df['total_returned_quantity'].iloc[0]
    return pd.DataFrame({'sku': [target_sku], 'quantity': [total_returns]})
