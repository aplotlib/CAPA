# src/data_processing.py

import pandas as pd
from typing import Optional, Dict, Any

class DataProcessor:
    """Processes and standardizes data from various sources."""
    def __init__(self, anthropic_api_key: Optional[str] = None):
        # API key can be used for future AI-driven data cleaning
        pass

    def process_sales_data(self, sales_df: pd.DataFrame, target_sku: str) -> pd.DataFrame:
        """Process and normalize sales data."""
        if sales_df is None or sales_df.empty:
            return pd.DataFrame()
        # Assuming parser has already structured it with 'sku' and 'quantity'
        sales_df['sku'] = sales_df['sku'].astype(str).str.strip()
        return sales_df.groupby('sku').agg({'quantity': 'sum'}).reset_index()

    def process_returns_data(self, returns_df: pd.DataFrame, target_sku: str) -> pd.DataFrame:
        """Process and normalize returns data."""
        if returns_df is None or returns_df.empty:
            return pd.DataFrame()
        # Assuming parser has already structured it with 'sku' and 'quantity'
        returns_df['sku'] = returns_df['sku'].astype(str).str.strip()
        return returns_df.groupby('sku').agg({'quantity': 'sum'}).reset_index()
