# src/parsers.py

"""
Unified module for parsing all supported file formats, including Excel,
PDF, Word, TXT, and images.
"""

import pandas as pd
import pdfplumber
import docx2txt
from docx import Document
from PIL import Image
import pytesseract
from io import BytesIO
from typing import Optional, IO

def _parse_excel(file: IO[bytes]) -> pd.DataFrame:
    """Parses an Excel file (.xlsx, .xls), combining all sheets."""
    try:
        excel_file = pd.ExcelFile(file)
        all_sheets = [pd.read_excel(excel_file, sheet_name=sheet) for sheet in excel_file.sheet_names]
        return pd.concat(all_sheets, ignore_index=True) if all_sheets else pd.DataFrame()
    except Exception as e:
        print(f"Error parsing Excel file: {e}")
        return pd.DataFrame()

def _parse_pdf(file: IO[bytes]) -> pd.DataFrame:
    """Extracts tables and text from a PDF file."""
    all_data = []
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        all_data.append(df)
        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
    except Exception as e:
        print(f"Error parsing PDF file: {e}")
        return pd.DataFrame()

def _parse_word_document(file: IO[bytes]) -> pd.DataFrame:
    """Extracts tables from a Word document (.docx)."""
    all_tables = []
    try:
        doc = Document(file)
        for table in doc.tables:
            data = [[cell.text for cell in row.cells] for row in table.rows]
            if data:
                df = pd.DataFrame(data[1:], columns=data[0])
                all_tables.append(df)
        return pd.concat(all_tables, ignore_index=True) if all_tables else pd.DataFrame()
    except Exception as e:
        print(f"Error parsing Word document: {e}")
        return pd.DataFrame()

def _parse_amazon_fba_returns(file: IO[bytes]) -> pd.DataFrame:
    """Parses the specific tab-separated format of Amazon FBA returns text files."""
    try:
        # Use StringIO to handle the decoded string as a file
        content = file.read().decode('utf-8')
        return pd.read_csv(StringIO(content), sep='\t')
    except Exception as e:
        print(f"Error parsing Amazon FBA returns file: {e}")
        return pd.DataFrame()

def _parse_generic_text(file: IO[bytes]) -> pd.DataFrame:
    """Parses a generic text file, trying CSV and then TSV format."""
    try:
        # Try CSV first
        df = pd.read_csv(file, on_bad_lines='skip')
        # If it results in a single column, it might be tab-separated
        if len(df.columns) == 1:
            file.seek(0) # Reset file pointer
            df_tsv = pd.read_csv(file, sep='\t', on_bad_lines='skip')
            if len(df_tsv.columns) > 1:
                return df_tsv
        return df
    except Exception as e:
        print(f"Error parsing generic text file: {e}")
        return pd.DataFrame()

def _parse_image(file: IO[bytes]) -> pd.DataFrame:
    """Performs OCR on an image file and returns the extracted text."""
    try:
        image = Image.open(file)
        text = pytesseract.image_to_string(image)
        return pd.DataFrame({'extracted_text': [text]})
    except Exception as e:
        print(f"Error parsing image file: {e}")
        return pd.DataFrame()

def parse_file(uploaded_file: IO[bytes], filename: str) -> Optional[pd.DataFrame]:
    """
    Factory function to parse an uploaded file based on its extension and content.

    Args:
        uploaded_file: The file-like object to parse.
        filename: The original name of the file.

    Returns:
        A pandas DataFrame with the parsed data, or None if parsing fails.
    """
    filename_lower = filename.lower()
    
    # --- Specialized Parsers First ---
    # Amazon FBA returns are .txt but have a specific format
    if filename_lower.endswith('.txt'):
        try:
            content_preview = uploaded_file.read(1024).decode('utf-8')
            uploaded_file.seek(0) # Reset buffer
            if 'return-date' in content_preview and 'order-id' in content_preview:
                return _parse_amazon_fba_returns(uploaded_file)
            else:
                return _parse_generic_text(uploaded_file)
        except Exception:
            uploaded_file.seek(0)
            return _parse_generic_text(uploaded_file)
            
    # --- General Parsers by Extension ---
    elif filename_lower.endswith(('.xlsx', '.xls')):
        return _parse_excel(uploaded_file)
    elif filename_lower.endswith('.pdf'):
        return _parse_pdf(uploaded_file)
    elif filename_lower.endswith('.docx'):
        return _parse_word_document(uploaded_file)
    elif filename_lower.endswith('.csv'):
        return _parse_generic_text(uploaded_file)
    elif filename_lower.endswith(('.png', '.jpg', '.jpeg')):
        return _parse_image(uploaded_file)
        
    return None
