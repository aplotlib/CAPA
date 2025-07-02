# src/parsers.py

import pandas as pd
from typing import Optional, IO

def _robust_read_csv(file: IO[bytes], **kwargs) -> pd.DataFrame:
    """A robust CSV reader that tries different encodings."""
    try:
        file.seek(0)
        return pd.read_csv(file, encoding='utf-8-sig', **kwargs)
    except Exception:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding='latin1', engine='python', **kwargs)
        except Exception as e:
            print(f"CRITICAL: Failed to read CSV. Error: {e}")
            return pd.DataFrame()

def _parse_odoo_forecast(file: IO[bytes]) -> pd.DataFrame:
    """Custom parser for the Odoo Inventory Forecast file (headers on row 2)."""
    return _robust_read_csv(file, header=1, on_bad_lines='skip')

def _parse_pivot_returns(file: IO[bytes]) -> pd.DataFrame:
    """Custom parser for the returns pivot table."""
    df = _robust_read_csv(file, header=None)
    if df.empty:
        return pd.DataFrame()
    
    returns_data = df.iloc[4:, 1:]
    numeric_returns = returns_data.apply(pd.to_numeric, errors='coerce')
    total_returns = numeric_returns.sum().sum()
    
    return pd.DataFrame({'total_returned_quantity': [total_returns]})

def parse_file(uploaded_file: IO[bytes], filename: str) -> Optional[pd.DataFrame]:
    """Factory function to route to the correct parser."""
    filename_lower = filename.lower()
    
    if 'odoo' in filename_lower and 'inventory' in filename_lower:
        return _parse_odoo_forecast(uploaded_file)
    
    if 'return' in filename_lower:
        return _parse_pivot_returns(uploaded_file)
    
    # Fallback for misc files (images will not parse to a dataframe here, but won't error)
    try:
        return _robust_read_csv(uploaded_file)
    except Exception:
        return pd.DataFrame({'file_content': [f"Could not parse file: {filename}"]})
