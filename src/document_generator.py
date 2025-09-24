# src/document_generator.py

from typing import Dict, Optional, Any, List
from io import BytesIO
from datetime import datetime, date
from docx import Document
from docx.shared import Inches
import pandas as pd

class CapaDocumentGenerator:
    """Generates formal, detailed Word document reports from structured data."""

    def __init__(self):
        """Initializes the document generator."""
        pass

    def _parse_markdown_table(self, markdown_text: str) -> (List[str], List[List[str]]):
        """
        Parses a Markdown table into a header and a list of rows.
        Handles potential formatting errors gracefully.
        """
        if not isinstance(markdown_text, str) or not markdown_text.strip():
            return [], []

        lines = [line.strip() for line in markdown_text.strip().split('\n')]
        lines = [line for line in lines if line]

        if len(lines) < 2:
            return [], []

        header_line, separator_line, data_lines = None, None, []
        for i, line in enumerate(lines):
            if '|' in line and i + 1 < len(lines) and '---' in lines[i+1]:
                header_line, separator_line, data_lines = lines[i], lines[i+1], lines[i+2:]
                break
        
        if not header_line or not separator_line:
            return [], []

        header = [h.strip() for h in header_line.split('|') if h.strip()]
        table_data = []
        for line in data_lines:
            if '|' in line:
                row = [cell.strip() for cell in line.split('|')]
                cleaned_row = row[1:-1] if len(row) > 2 and not row[0] and not row[-1] else row
                if len(cleaned_row) == len(header):
                    table_data.append(cleaned_row)
        return header, table_data

    def _add_df_to_doc(self, doc: Document, df: pd.DataFrame):
        """Adds a Pandas DataFrame as a table to the Word document."""
        if df.empty:
            return
        
        table = doc.add_table(rows=1, cols=len(df.columns))
        table.style = 'Table Grid'
        
        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(df.columns):
            hdr_cells[i].text = str(col_name)

        for index, row in df.iterrows():
            row_cells = table.add_row().cells
            for i, value in enumerate(row):
                row_cells[i].text = str(value)

    def _add_markdown_table_to_doc(self, doc: Document, markdown_text: str):
        """Parses a Markdown table and adds it to the Word document."""
        header, data = self._parse_markdown_table(markdown_text)
        if not header or not data:
            doc.add_paragraph(markdown_text)
            return

        table = doc.add_table(rows=1, cols=len(header))
        table.style = 'Table Grid'

        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(header):
            hdr_cells[i].text = col_name
        
        for row_data in data:
            row_cells = table.add_row().cells
            for i, cell_value in enumerate(row_data):
                row_cells[i].text = cell_value
    
    def _add_capa_to_doc(self, doc: Document, capa_data: Dict[str, Any]):
        """Adds the CAPA form data to the Word document in a structured table."""
        doc.add_heading("Corrective and Preventive Action (CAPA) Report", level=2)
        table = doc.add_table(rows=0, cols=2)
        table.style = 'Table Grid'
        
        def add_row(field_name: str, value: Any):
            row_cells = table.add_row().cells
            row_cells[0].text = field_name
            if isinstance(value, date):
                value = value.strftime('%Y-%m-%d')
            row_cells[1].text = str(value if value is not None else '')

        field_map = {
            'capa_number': "CAPA Number", 'date': "Initiation Date", 'product_name': "Product Name/Model",
            'prepared_by': "Prepared By", 'source_of_issue': "Source of Issue", 'issue_description': "Description of Non-conformity",
            'immediate_containment_actions': "Immediate Actions", 'risk_severity': "Risk Severity (1-5)",
            'risk_probability': "Risk Probability (1-5)", 'root_cause': "Root Cause Analysis",
            'corrective_action': "Corrective Action(s)", 'preventive_action': "Preventive Action(s)",
            'effectiveness_verification_plan': "Verification Plan", 'closed_by': "Closed By", 'closure_date': "Closure Date"
        }
        for key, name in field_map.items():
            add_row(name, capa_data.get(key, ''))
        doc.add_page_break()

    def export_all_to_docx(self, content: Dict[str, Any]) -> BytesIO:
        """Exports a combined report of all analyses to a Word document."""
        doc = Document()
        doc.add_heading(f"Combined Quality Report for SKU: {content.get('sku', 'N/A')}", level=1)
        p = doc.add_paragraph()
        p.add_run(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}").italic = True
        
        if content.get('dashboard'):
            doc.add_heading("Dashboard Summary & AI Insights", level=2)
            results = content['dashboard']
            summary_df = results.get('return_summary')
            if summary_df is not None and not summary_df.empty:
                self._add_df_to_doc(doc, summary_df)
            doc.add_heading("AI-Generated Insights", level=3)
            doc.add_paragraph(results.get('insights', 'No insights were generated.'))
            doc.add_page_break()
            
        if content.get('capa'):
            self._add_capa_to_doc(doc, content['capa'])

        if content.get('fmea') is not None and not content.get('fmea').empty:
            doc.add_heading("Failure Mode and Effects Analysis (FMEA)", level=2)
            self._add_df_to_doc(doc, content['fmea'])
            doc.add_page_break()

        if content.get('risk_assessment'):
            doc.add_heading("ISO 14971 Risk Assessment", level=2)
            self._add_markdown_table_to_doc(doc, content['risk_assessment'])
            doc.add_page_break()

        if content.get('urra'):
            doc.add_heading("Use-Related Risk Analysis (URRA - IEC 62366)", level=2)
            self._add_markdown_table_to_doc(doc, content['urra'])
            doc.add_page_break()

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
