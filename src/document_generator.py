# src/document_generator.py

from typing import Dict, Optional, Any
from io import BytesIO
from datetime import date
import pandas as pd
from docx import Document
from docx.shared import Inches

class DocumentGenerator:
    """
    Generates formal Word documents for CAPA Reports, SCARs, and combined reports.
    """

    def _add_main_table_row(self, table, heading: str, content: str):
        """Helper to add a formatted row to the main CAPA/SCAR table."""
        row_cells = table.add_row().cells
        p = row_cells[0].paragraphs[0]
        p.add_run(heading).bold = True
        row_cells[1].text = str(content) if content is not None else ''

    def _add_df_as_table(self, doc, df: pd.DataFrame, title: str):
        """Helper to add a pandas DataFrame as a formatted table in the document."""
        doc.add_page_break()
        doc.add_heading(title, level=2)
        
        # Create a table with an extra row for headers
        table = doc.add_table(rows=1, cols=len(df.columns))
        table.style = 'Table Grid'
        
        # Add the header row
        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(df.columns):
            hdr_cells[i].text = str(col_name)
            hdr_cells[i].paragraphs[0].runs[0].font.bold = True

        # Add the data rows
        for index, row in df.iterrows():
            row_cells = table.add_row().cells
            for i, cell_value in enumerate(row):
                row_cells[i].text = str(cell_value)
    
    def generate_capa_docx(self, capa_data: Dict[str, Any], fmea_df: Optional[pd.DataFrame] = None) -> BytesIO:
        """Generates a formal CAPA report, now with an optional FMEA addendum."""
        doc = Document()
        doc.add_heading("Corrective and Preventive Action (CAPA) Report", level=1)

        # --- Header Table ---
        header_table = doc.add_table(rows=2, cols=2)
        header_table.cell(0, 0).text = f"CAPA Number: {capa_data.get('capa_number', 'N/A')}"
        initiation_date = capa_data.get('date', date.today())
        header_table.cell(0, 1).text = f"Date: {initiation_date.strftime('%Y-%m-%d') if isinstance(initiation_date, date) else initiation_date}"
        header_table.cell(1, 0).text = "To: [Name, Title, Organization]"
        header_table.cell(1, 1).text = f"Prepared By: {capa_data.get('prepared_by', '[Name, Title, Organization]')}"
        doc.add_paragraph()

        # --- Main Content Table ---
        main_table = doc.add_table(rows=1, cols=2)
        main_table.style = 'Table Grid'
        main_table.columns[0].width = Inches(1.5)
        main_table.columns[1].width = Inches(6.0)
        main_table.rows[0].cells[0].text = "Section"
        main_table.rows[0].cells[1].text = "Details"

        field_map = {
            "Product Name / Model": capa_data.get('product_name', ''),
            "Source of Issue": capa_data.get('source_of_issue', ''),
            "Problem Description": capa_data.get('issue_description', ''),
            "Immediate Containment Actions": capa_data.get('immediate_containment_actions', ''),
            "Root Cause Analysis": capa_data.get('root_cause', ''),
            "Corrective Action Plan": capa_data.get('corrective_action', ''),
            "Preventive Action Plan": capa_data.get('preventive_action', ''),
            "Effectiveness Verification Plan": capa_data.get('effectiveness_verification_plan', '')
        }
        for heading, content in field_map.items():
            self._add_main_table_row(main_table, heading, str(content))
        
        # --- NEW: Add FMEA data if it exists ---
        if fmea_df is not None and not fmea_df.empty:
            self._add_df_as_table(doc, fmea_df, "FMEA Addendum")

        # --- Closure & Signature Block ---
        doc.add_page_break()
        doc.add_heading("Verification & Closure", level=2)
        
        closure_p = doc.add_paragraph()
        closure_date = capa_data.get('closure_date')
        closure_p.add_run(f"Verification Findings: ").bold = True
        closure_p.add_run("\n\n")
        closure_p.add_run(f"Closed By: ").bold = True
        closure_p.add_run(f"{capa_data.get('closed_by', '______________________')}\n")
        closure_p.add_run(f"Closure Date: ").bold = True
        closure_p.add_run(f"{closure_date.strftime('%Y-%m-%d') if isinstance(closure_date, date) else '______________________'}")

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    def generate_scar_docx(self, capa_data: Dict[str, Any], vendor_name: str) -> BytesIO:
        """Generates a formal Supplier Corrective Action Request (SCAR) document."""
        doc = Document()
        doc.add_heading("Supplier Corrective Action Request (SCAR)", level=1)
        
        header_table = doc.add_table(rows=3, cols=2)
        header_table.cell(0, 0).text = f"SCAR Number: {capa_data.get('capa_number', 'N/A').replace('CAPA', 'SCAR')}"
        header_table.cell(0, 1).text = f"Date: {date.today().strftime('%Y-%m-%d')}"
        header_table.cell(1, 0).text = f"To: {vendor_name}"
        header_table.cell(1, 1).text = f"From: {capa_data.get('prepared_by', 'Quality Department')}"
        header_table.cell(2, 0).merge(header_table.cell(2, 1))
        header_table.cell(2, 0).text = f"Product/SKU Affected: {capa_data.get('product_name', 'N/A')}"
        doc.add_paragraph()

        main_table = doc.add_table(rows=1, cols=2)
        main_table.style = 'Table Grid'
        main_table.columns[0].width = Inches(2.0)
        main_table.columns[1].width = Inches(5.5)
        main_table.rows[0].cells[0].text = "Section"
        main_table.rows[0].cells[1].text = "Details"
        
        self._add_main_table_row(main_table, "Description of Non-conformance", str(capa_data.get('issue_description', '')))
        self._add_main_table_row(main_table, "Our Initial Root Cause Analysis", str(capa_data.get('root_cause', '')))
        self._add_main_table_row(main_table, "Action Required from Supplier", "Please investigate the non-conformance, perform a thorough root cause analysis, and provide a detailed corrective action plan to prevent recurrence.")
        self._add_main_table_row(main_table, "Response Due Date", f"A formal response is required within 15 business days.")

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
