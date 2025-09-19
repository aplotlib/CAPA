# src/document_generator.py

import json
from typing import Dict, Optional, Any
from io import BytesIO
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pandas as pd
import anthropic

class CapaDocumentGenerator:
    """Generates formal reports from structured data."""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.client = None
        if anthropic_api_key:
            try:
                self.client = anthropic.Anthropic(api_key=anthropic_api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")

    def export_text_to_docx(self, text: str, title: str) -> BytesIO:
        """Export plain text to a formatted Word document."""
        doc = Document()
        doc.add_heading(title, level=1)
        doc.add_paragraph(text)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
        
    def export_fmea_to_excel(self, fmea_df: pd.DataFrame, sku: str) -> BytesIO:
        """Export FMEA data to an Excel file."""
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            fmea_df.to_excel(writer, sheet_name='FMEA', index=False)
            # Auto-adjust columns
            for column in writer.book.worksheets[0].columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2)
                writer.book.worksheets[0].column_dimensions[column_letter].width = adjusted_width
        buffer.seek(0)
        return buffer

    def export_all_to_docx(self, content: Dict[str, Any]) -> BytesIO:
        """Exports a combined report of all selected analyses to a Word document."""
        doc = Document()
        doc.add_heading(f"Combined Quality Report for SKU: {content.get('sku', 'N/A')}", level=1)
        doc.add_paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # --- Dashboard Section ---
        if content.get('dashboard'):
            doc.add_heading("Dashboard & CAPA Insights", level=2)
            results = content['dashboard']
            summary = results.get('return_summary')
            if summary is not None and not summary.empty:
                summary_data = summary.iloc[0]
                doc.add_paragraph(
                    f"Return Rate: {summary_data['return_rate']:.2f}% | "
                    f"Total Sold: {int(summary_data['total_sold'])} | "
                    f"Total Returned: {int(summary_data['total_returned'])}"
                )
            doc.add_paragraph(results.get('insights', 'No insights generated.'))
            doc.add_page_break()

        # --- FMEA Section ---
        if content.get('fmea') is not None and not content.get('fmea').empty:
            doc.add_heading("Failure Mode and Effects Analysis (FMEA)", level=2)
            fmea_df = content['fmea']
            
            # Add FMEA table to the document
            table = doc.add_table(rows=1, cols=len(fmea_df.columns))
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            for i, col_name in enumerate(fmea_df.columns):
                hdr_cells[i].text = col_name

            for index, row in fmea_df.iterrows():
                row_cells = table.add_row().cells
                for i, value in enumerate(row):
                    row_cells[i].text = str(value)
            doc.add_page_break()

        # --- Pre-Mortem Section ---
        if content.get('pre_mortem'):
            doc.add_heading("Pre-Mortem Summary", level=2)
            doc.add_paragraph(content['pre_mortem'])
            doc.add_page_break()

        # --- Vendor Email Section ---
        if content.get('vendor_email'):
            doc.add_heading("Vendor Email Draft", level=2)
            doc.add_paragraph(content['vendor_email'])

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
