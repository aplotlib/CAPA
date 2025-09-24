# src/data_processing.py

import pandas as pd
from typing import Optional

class DataProcessor:
    """Processes and standardizes data from various sources."""
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initializes the DataProcessor.
        The API key is passed for potential future AI-driven data cleaning or validation features.
        """
        self.api_key = openai_api_key

    def process_sales_data(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes and normalizes sales data.
        It expects a DataFrame with at least 'sku' and 'quantity' columns.
        """
        if sales_df is None or sales_df.empty:
            return pd.DataFrame()
        
        # Ensure required columns exist
        if 'sku' not in sales_df.columns or 'quantity' not in sales_df.columns:
            # Handle error appropriately, maybe log it or raise an exception
            print("Error: Sales DataFrame must contain 'sku' and 'quantity' columns.")
            return pd.DataFrame()

        # Standardize data types to prevent errors during processing
        sales_df['sku'] = sales_df['sku'].astype(str).str.strip()
        sales_df['quantity'] = pd.to_numeric(sales_df['quantity'], errors='coerce').fillna(0)
        
        # Group by SKU and sum the quantities
        processed_df = sales_df.groupby('sku').agg({'quantity': 'sum'}).reset_index()
        return processed_df

    def process_returns_data(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes and normalizes returns data.
        It expects a DataFrame with at least 'sku' and 'quantity' columns.
        """
        if returns_df is None or returns_df.empty:
            return pd.DataFrame()

        # Ensure required columns exist
        if 'sku' not in returns_df.columns or 'quantity' not in returns_df.columns:
            print("Error: Returns DataFrame must contain 'sku' and 'quantity' columns.")
            return pd.DataFrame()

        # Standardize data types
        returns_df['sku'] = returns_df['sku'].astype(str).str.strip()
        returns_df['quantity'] = pd.to_numeric(returns_df['quantity'], errors='coerce').fillna(0)
        
        # Group by SKU and sum the quantities
        processed_df = returns_df.groupby('sku').agg({'quantity': 'sum'}).reset_index()
        return processed_df
