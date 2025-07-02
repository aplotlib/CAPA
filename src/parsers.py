# src/parsers.py

"""
Unified module for parsing all supported file formats.
Includes a custom parser for the Odoo inventory forecast format.
"""

import pandas as pd
import pdfplumber
from docx import Document
from PIL import Image
import pytesseract
from io import BytesIO, StringIO
from typing import Optional, IO

def _parse_odoo_forecast(file: IO[bytes]) -> pd.DataFrame:
    """
    Custom parser for the Odoo Inventory Forecast file.
    It skips the first row and uses the second row as the header.
    """
    try:
        file.seek(0)
        # Use header=1 to specify that the headers are on the second row (index 1)
        return pd.read_csv(file, header=1, encoding='utf-8-sig')
    except Exception as e:
        print(f"Error parsing Odoo forecast file: {e}")
        return pd.DataFrame()

def _parse_standard_csv(file: IO[bytes]) -> pd.DataFrame:
    """Parses a standard CSV file."""
    try:
        file.seek(0)
        return pd.read_csv(file, encoding='utf-8-sig', on_bad_lines='skip')
    except Exception:
        return pd.DataFrame()

# (Other parsers like _parse_pdf, _parse_word_document remain the same)
def _parse_pdf(file: IO[bytes]) -> pd.DataFrame:
    # ...
    return pd.DataFrame()

def _parse_word_document(file: IO[bytes]) -> pd.DataFrame:
    # ...
    return pd.DataFrame()

def _parse_image(file: IO[bytes]) -> pd.DataFrame:
    # ...
    return pd.DataFrame()


def parse_file(uploaded_file: IO[bytes], filename: str) -> Optional[pd.DataFrame]:
    """
    Factory function to parse an uploaded file based on its name or extension.
    """
    filename_lower = filename.lower()
    
    # Prioritize custom parsers based on filename patterns
    if 'odoo' in filename_lower and 'inventory' in filename_lower:
        return _parse_odoo_forecast(uploaded_file)
    
    # NOTE: The Pivot Return Report is too complex for a generic parser.
    # It requires a report with SKU-level data. We will treat it as a standard CSV for now.
    if 'return' in filename_lower:
        return _parse_standard_csv(uploaded_file)
    
    # Fallback to extension-based parsing
    if filename_lower.endswith(('.xlsx', '.xls')):
        # A simple excel parser (can be expanded if needed)
        return pd.read_excel(uploaded_file)
    elif filename_lower.endswith('.pdf'):
        return _parse_pdf(uploaded_file)
    elif filename_lower.endswith('.docx'):
        return _parse_word_document(uploaded_file)
    elif filename_lower.endswith(('.png', '.jpg', '.jpeg')):
        return _parse_image(uploaded_file)
    else:
        return _parse_standard_csv(uploaded_file)
