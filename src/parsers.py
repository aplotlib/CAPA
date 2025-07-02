# src/parsers.py

"""
Module for parsing files, with custom logic for the user's specific
Odoo forecast and Pivot Table returns report.
"""

import pandas as pd
from typing import Optional, IO

def _parse_odoo_forecast(file: IO[bytes]) -> pd.DataFrame:
    """
    Custom parser for the Odoo Inventory Forecast file.
    It skips the first row and uses the second row as the header.
    """
    try:
        file.seek(0)
        # Use header=1 to specify that headers are on the second row (index 1)
        return pd.read_csv(file, header=1, encoding='utf-8-sig', on_bad_lines='skip')
    except Exception as e:
        print(f"Error parsing Odoo forecast file: {e}")
        return pd.DataFrame()

def _parse_pivot_returns(file: IO[bytes]) -> pd.DataFrame:
    """
    Custom parser for the user's specific returns pivot table.
    It reads the complex structure and sums all return values.
    """
    try:
        file.seek(0)
        # Read the file without headers to manually process rows
        df = pd.read_csv(file, header=None, encoding='utf-8-sig')
        
        # The actual return quantities start from the 5th row (index 4)
        # and from the second column (index 1) onwards.
        returns_data = df.iloc[4:, 1:]
        
        # Convert all values to numeric, coercing errors to NaN
        numeric_returns = returns_data.apply(pd.to_numeric, errors='coerce')
        
        # Calculate the total sum of all returned units in the table
        total_returns = numeric_returns.sum().sum()
        
        # Return a DataFrame with a single row for the total returns
        return pd.DataFrame({'total_returned_quantity': [total_returns]})
    except Exception as e:
        print(f"Error parsing pivot returns file: {e}")
        return pd.DataFrame()

def _parse_standard_csv(file: IO[bytes]) -> pd.DataFrame:
    """Parses a standard CSV file, used for manual entry or misc files."""
    try:
        file.seek(0)
        return pd.read_csv(file, encoding='utf-8-sig', on_bad_lines='skip')
    except Exception:
        return pd.DataFrame()

def parse_file(uploaded_file: IO[bytes], filename: str) -> Optional[pd.DataFrame]:
    """
    Factory function to parse a file, prioritizing custom parsers.
    """
    filename_lower = filename.lower()
    
    # Use custom parsers based on filename patterns
    if 'odoo' in filename_lower and 'inventory' in filename_lower:
        return _parse_odoo_forecast(uploaded_file)
    
    if 'return' in filename_lower:
        return _parse_pivot_returns(uploaded_file)
    
    # Fallback for any other file
    return _parse_standard_csv(uploaded_file)
