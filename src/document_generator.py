# src/document_generator.py

from typing import Dict, Optional, Any, List
from io import BytesIO
from datetime import datetime, date
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pandas as pd

class DocumentGenerator:
    """
    Generates formal Word documents for CAPA Reports, SCARs, and combined reports.
    """

    def _add_main_table_row(self, table, heading: str, content: str):
        """Helper to add a formatted row to the main CAPA/SCAR table."""
        row_cells = table.add_row().cells
        p = row_cells[0].paragraphs[0]
        p.add_run(heading).bold = True
        row_cells[1].text = content if content is not None else ''

    def generate_capa_docx(self, capa_data: Dict[str, Any]) -> BytesIO:
        """Generates a formal CAPA report matching the user-provided PDF template."""
        doc = Document()
        doc.add_heading("Corrective and Preventive Action (CAPA) Report", level=1)

        # --- Header Table ---
        header_table = doc.add_table(rows=2, cols=2)
        header_table.cell(0, 0).text = f"CAPA Number: {capa_data.get('capa_number', 'N/A')}"
        header_table.cell(0, 1).text = f"Date: {capa_data.get('date', date.today()).strftime('%Y-%m-%d')}"
        header_table.cell(1, 0).text = "To: [Name, Title, Organization]"
        header_table.cell(1, 1).text = f"Prepared By: {capa_data.get('prepared_by', '[Name, Title, Organization]')}"
        doc.add_paragraph()

        # --- Main Content Table ---
        main_table = doc.add_table(rows=1, cols=2)
        main_table.style = 'Table Grid'
        main_table.columns[0].width = Inches(1.5)
        main_table.columns[1].width = Inches(6.0)
        main_table.rows[0].cells[0].text = "Section" # Hidden Header
        main_table.rows[0].cells[1].text = "Details" # Hidden Header

        # --- Populate Main Table ---
        field_map = {
            "Issue": capa_data.get('issue_description', ''),
            "Immediate Actions/Corrections": capa_data.get('immediate_containment_actions', ''),
            "Root Cause": capa_data.get('root_cause', ''),
            "Corrective Action": capa_data.get('corrective_action', ''),
            "Implementation of Corrective Actions": capa_data.get('corrective_action_implementation', ''),
            "Preventive Action": capa_data.get('preventive_action', ''),
            "Implementation of Preventive Actions": capa_data.get('preventive_action_implementation', '')
        }
        for heading, content in field_map.items():
            self._add_main_table_row(main_table, heading, str(content))
        
        doc.add_page_break()

        # --- Effectiveness Check Section ---
        doc.add_heading("Effectiveness Check", level=2)
        eff_table = doc.add_table(rows=1, cols=2)
        eff_table.style = 'Table Grid'
        eff_table.columns[0].width = Inches(1.5)
        eff_table.columns[1].width = Inches(6.0)
        eff_table.rows[0].cells[0].text = "Section" # Hidden Header
        eff_table.rows[0].cells[1].text = "Details" # Hidden Header
        
        self._add_main_table_row(eff_table, "Effectiveness Check Plan", str(capa_data.get('effectiveness_verification_plan', '')))
        self._add_main_table_row(eff_table, "Effectiveness Check Findings", str(capa_data.get('effectiveness_check_findings', '')))

        # --- Signature Block ---
        doc.add_paragraph("\n\n")
        sig_p = doc.add_paragraph()
        sig_p.add_run("________________________________________\t\t\t").bold = False
        sig_p.add_run("____________________").bold = False
        
        sig_p2 = doc.add_paragraph()
        sig_p2.add_run("Signature, Quality Manager\t\t\t\t\t").bold = True
        sig_p2.add_run("Date of Signature").bold = True

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    def generate_scar_docx(self, capa_data: Dict[str, Any], vendor_name: str) -> BytesIO:
        """Generates a formal Supplier Corrective Action Request (SCAR) document."""
        doc = Document()
        doc.add_heading("Supplier Corrective Action Request (SCAR)", level=1)

        # --- Header Table ---
        header_table = doc.add_table(rows=3, cols=2)
        header_table.cell(0, 0).text = f"SCAR Number: {capa_data.get('capa_number', 'N/A').replace('CAPA', 'SCAR')}"
        header_table.cell(0, 1).text = f"Date: {date.today().strftime('%Y-%m-%d')}"
        header_table.cell(1, 0).text = f"To: {vendor_name}"
        header_table.cell(1, 1).text = f"From: {capa_data.get('prepared_by', 'Quality Department')}"
        header_table.cell(2, 0).merge(header_table.cell(2, 1))
        header_table.cell(2, 0).text = f"Product/SKU Affected: {capa_data.get('product_name', 'N/A')}"
        doc.add_paragraph()

        # --- Main Content Table ---
        main_table = doc.add_table(rows=1, cols=2)
        main_table.style = 'Table Grid'
        main_table.columns[0].width = Inches(2.0)
        main_table.columns[1].width = Inches(5.5)
        main_table.rows[0].cells[0].text = "Section"
        main_table.rows[0].cells[1].text = "Details"
        
        self._add_main_table_row(main_table, "Description of Non-conformance", str(capa_data.get('issue_description', '')))
        self._add_main_table_row(main_table, "Our Initial Root Cause Analysis", str(capa_data.get('root_cause', '')))
        self._add_main_table_row(main_table, "Action Required from Supplier", "Please investigate the non-conformance, perform a thorough root cause analysis, and provide a detailed corrective action plan to prevent recurrence.")
        self._add_main_table_row(main_table, "Response Due Date", f"A formal response is required within 15 business days, by {(date.today() + pd.Timedelta(days=21)).strftime('%Y-%m-%d')}.") # Approx 15 business days

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
