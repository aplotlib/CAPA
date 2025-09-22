# src/document_generator.py

import json
from typing import Dict, Optional, Any, List
from io import BytesIO
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pandas as pd
import re

class CapaDocumentGenerator:
    """Generates formal, detailed reports from structured data."""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        # API key might be used for future summarization features
        pass

    def _parse_markdown_table(self, markdown_text: str) -> List[List[str]]:
        """Parses a Markdown table into a list of lists."""
        if not markdown_text or not isinstance(markdown_text, str):
            return [], []

        lines = markdown_text.strip().split('\n')
        
        # Find header line
        header_line_index = -1
        for i, line in enumerate(lines):
            if '|' in line and '---' in lines[i+1 if i+1 < len(lines) else i]:
                header_line_index = i
                break
        
        if header_line_index == -1:
            return [], []

        # Extract header
        header = [h.strip() for h in lines[header_line_index].split('|') if h.strip()]
        
        # Extract rows
        table_data = []
        for line in lines[header_line_index + 2:]:
            if '|' not in line:
                continue
            row = [cell.strip() for cell in line.split('|')]
            # Markdown tables often have an empty string at the start and end of each row split
            cleaned_row = row[1:-1] if len(row) > 1 else row
            if len(cleaned_row) == len(header):
                 table_data.append(cleaned_row)

        return header, table_data

    def _add_df_to_doc(self, doc: Document, df: pd.DataFrame):
        """Adds a Pandas DataFrame as a table to the Word document."""
        if df.empty:
            return
        
        table = doc.add_table(rows=1, cols=len(df.columns))
        table.style = 'Table Grid'
        
        # Add header
        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(df.columns):
            hdr_cells[i].text = str(col_name)

        # Add data rows
        for index, row in df.iterrows():
            row_cells = table.add_row().cells
            for i, value in enumerate(row):
                row_cells[i].text = str(value)

    def _add_markdown_table_to_doc(self, doc: Document, markdown_text: str):
        """Parses a Markdown table and adds it to the Word document."""
        header, data = self._parse_markdown_table(markdown_text)
        if not header or not data:
            # Fallback for plain text
            doc.add_paragraph(markdown_text)
            return

        table = doc.add_table(rows=1, cols=len(header))
        table.style = 'Table Grid'

        # Add header
        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(header):
            hdr_cells[i].text = col_name
        
        # Add data rows
        for row_data in data:
            row_cells = table.add_row().cells
            for i, cell_value in enumerate(row_data):
                row_cells[i].text = cell_value


    def export_all_to_docx(self, content: Dict[str, Any]) -> BytesIO:
        """Exports a combined, detailed report of all analyses to a Word document."""
        doc = Document()
        doc.add_heading(f"Combined Quality Report for SKU: {content.get('sku', 'N/A')}", level=1)
        p = doc.add_paragraph()
        p.add_run(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}").italic = True
        
        # --- Dashboard Section ---
        if content.get('dashboard'):
            doc.add_heading("Dashboard Summary & AI Insights", level=2)
            results = content['dashboard']
            summary_df = results.get('return_summary')
            if summary_df is not None and not summary_df.empty:
                doc.add_paragraph("The following table summarizes the key performance metrics for the target SKU during the analysis period.")
                self._add_df_to_doc(doc, summary_df)
            
            doc.add_heading("AI-Generated Insights", level=3)
            doc.add_paragraph(results.get('insights', 'No insights were generated.'))
            doc.add_page_break()

        # --- Device Classification Section ---
        if content.get('device_classification'):
            doc.add_heading("Medical Device Classification (U.S. FDA)", level=2)
            classification_data = content['device_classification']
            if "error" in classification_data:
                doc.add_paragraph(f"Error during classification: {classification_data['error']}")
            else:
                doc.add_paragraph(f"**Suggested Classification:** {classification_data.get('classification', 'N/A')}")
                doc.add_heading("Rationale", level=3)
                doc.add_paragraph(classification_data.get('rationale', 'No rationale provided.'))
                doc.add_heading("Primary Risks", level=3)
                doc.add_paragraph(classification_data.get('risks', 'No risks identified.'))
                doc.add_heading("General Regulatory Requirements", level=3)
                doc.add_paragraph(classification_data.get('regulatory_requirements', 'No requirements provided.'))
            doc.add_page_break()

        # --- FMEA Section ---
        if content.get('fmea') is not None and not content.get('fmea').empty:
            doc.add_heading("Failure Mode and Effects Analysis (FMEA)", level=2)
            doc.add_paragraph("This FMEA identifies potential failure modes, their effects, and causes, and ranks them by Risk Priority Number (RPN).")
            self._add_df_to_doc(doc, content['fmea'])
            doc.add_page_break()

        # --- ISO 14971 Risk Assessment ---
        if content.get('risk_assessment'):
            doc.add_heading("ISO 14971 Risk Assessment", level=2)
            doc.add_paragraph("The following table outlines risks based on the ISO 14971 standard, analyzing hazards, harms, and mitigations.")
            self._add_markdown_table_to_doc(doc, content['risk_assessment'])
            doc.add_page_break()

        # --- Use-Related Risk Analysis (URRA) ---
        if content.get('urra'):
            doc.add_heading("Use-Related Risk Analysis (URRA - IEC 62366)", level=2)
            doc.add_paragraph("This analysis identifies risks associated with the usability and user interface of the device, based on IEC 62366.")
            self._add_markdown_table_to_doc(doc, content['urra'])
            doc.add_page_break()

        # --- Pre-Mortem Section ---
        if content.get('pre_mortem'):
            doc.add_heading("Pre-Mortem Analysis Summary", level=2)
            doc.add_paragraph("This section summarizes the findings from the pre-mortem exercise, which proactively identifies potential reasons for project failure.")
            doc.add_paragraph(content['pre_mortem'])
            doc.add_page_break()

        # --- Vendor Email Section ---
        if content.get('vendor_email'):
            doc.add_heading("Vendor Communication Draft", level=2)
            doc.add_paragraph("The following email was drafted to communicate quality findings to the manufacturing partner.")
            doc.add_paragraph(content['vendor_email'])

        # --- Save document to buffer ---
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
