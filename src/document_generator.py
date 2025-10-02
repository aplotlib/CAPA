# src/document_generator.py

from typing import Dict, Any, List, Optional
from io import BytesIO
from datetime import date
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

class DocumentGenerator:
    """
    Generates a single, comprehensive Word document summarizing a project,
    allowing users to select which components to include.
    """

    def _add_main_table_row(self, table, heading: str, content: Any):
        """Helper to add a formatted row to a two-column table."""
        row_cells = table.add_row().cells
        p = row_cells[0].paragraphs[0]
        p.add_run(heading).bold = True
        row_cells[1].text = str(content) if content is not None else ''

    def _add_df_as_table(self, doc, df: pd.DataFrame, title: str):
        """Helper to add a pandas DataFrame as a formatted table in the document."""
        if df is None or df.empty:
            return
        doc.add_page_break()
        doc.add_heading(title, level=2)
        
        table = doc.add_table(rows=1, cols=len(df.columns))
        table.style = 'Table Grid'
        
        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(df.columns):
            hdr_cells[i].text = str(col_name)
            hdr_cells[i].paragraphs[0].runs[0].font.bold = True

        for _, row in df.iterrows():
            row_cells = table.add_row().cells
            for i, cell_value in enumerate(row):
                row_cells[i].text = str(cell_value)

    def _add_markdown_text(self, doc, text: str, title: str):
        """Adds text, potentially in Markdown, as a new section."""
        if not text:
            return
        doc.add_page_break()
        doc.add_heading(title, level=2)
        doc.add_paragraph(text)
        
    def _generate_executive_summary(self, session_data: Dict[str, Any], ai_context_helper: Any) -> str:
        """Uses AI to generate a high-level executive summary."""
        if ai_context_helper:
            prompt = (
                "Based on the full application context, generate a concise, professional executive summary for a final project report. "
                "The summary should briefly outline the problem, key findings from the analyses (like top risks from FMEA), and the planned corrective actions. "
                "Conclude with a 'Recommendations' section suggesting the next logical steps."
            )
            try:
                return ai_context_helper.generate_response(prompt)
            except Exception:
                return "Could not generate AI summary."
        return "AI helper not available."

    def generate_summary_docx(self, session_data: Dict[str, Any], selected_sections: List[str]) -> BytesIO:
        """
        Generates a single comprehensive report based on selected sections.
        """
        doc = Document()
        doc.add_heading("Project Summary Report", level=1)
        
        # --- AI Executive Summary ---
        summary_text = self._generate_executive_summary(session_data, session_data.get('ai_context_helper'))
        doc.add_heading("Executive Summary", level=2)
        doc.add_paragraph(summary_text)
        
        # --- CAPA Form Section ---
        if "CAPA Form" in selected_sections and session_data.get('capa_data'):
            capa_data = session_data['capa_data']
            doc.add_page_break()
            doc.add_heading("Corrective and Preventive Action (CAPA) Details", level=2)
            
            main_table = doc.add_table(rows=1, cols=2)
            main_table.style = 'Table Grid'
            main_table.columns[0].width = Inches(2.0)
            main_table.columns[1].width = Inches(5.5)
            main_table.rows[0].cells[0].text = "Section"
            main_table.rows[0].cells[1].text = "Details"

            field_map = {
                "CAPA Number": capa_data.get('capa_number', 'N/A'),
                "Product Name / Model": capa_data.get('product_name', 'N/A'),
                "Initiation Date": capa_data.get('date', date.today()).strftime('%Y-%m-%d'),
                "Problem Description": capa_data.get('issue_description', ''),
                "Immediate Actions/Corrections": capa_data.get('immediate_actions', ''),
                "Root Cause Analysis": capa_data.get('root_cause', ''),
                "Corrective Action Plan": capa_data.get('corrective_action', ''),
                "Implementation of Corrective Actions": capa_data.get('implementation_of_corrective_actions', ''),
                "Preventive Action Plan": capa_data.get('preventive_action', ''),
                "Implementation of Preventive Actions": capa_data.get('implementation_of_preventive_actions', ''),
                "Effectiveness Check Plan": capa_data.get('effectiveness_verification_plan', '')
            }
            for heading, content in field_map.items():
                self._add_main_table_row(main_table, heading, content)

        # --- CAPA Closure Section ---
        if "CAPA Closure" in selected_sections and session_data.get('capa_closure_data'):
            self._generate_capa_closure_section(doc, session_data['capa_closure_data'])

        # --- FMEA Section ---
        if "FMEA" in selected_sections and session_data.get('fmea_data') is not None:
            self._add_df_as_table(doc, session_data['fmea_data'], "Failure Mode and Effects Analysis (FMEA)")

        # --- ISO 14971 Assessment Section ---
        if "ISO 14971 Assessment" in selected_sections and session_data.get('risk_assessment'):
            self._add_markdown_text(doc, session_data['risk_assessment'], "ISO 14971 Risk Assessment")
            
        # --- URRA Section ---
        if "URRA" in selected_sections and session_data.get('urra'):
            self._add_markdown_text(doc, session_data['urra'], "Use-Related Risk Analysis (URRA)")

        # --- Vendor Email Section ---
        if "Vendor Email Draft" in selected_sections and session_data.get('vendor_email_draft'):
            self._add_markdown_text(doc, session_data['vendor_email_draft'], "Vendor Communication Draft")

        # --- Human Factors Report Section ---
        if "Human Factors Report" in selected_sections and session_data.get('human_factors_data'):
            self._generate_human_factors_section(doc, session_data['human_factors_data'])

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    
    def _generate_capa_closure_section(self, doc: Document, closure_data: Dict[str, Any]):
        """Generates the CAPA Effectiveness Check & Closure section of the report."""
        if not closure_data.get('original_capa'):
            return # Don't add the section if there's no data

        doc.add_page_break()
        doc.add_heading("CAPA Effectiveness Check & Closure", level=2)
        
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        table.columns[0].width = Inches(2.0)
        table.columns[1].width = Inches(5.5)

        # Implementation Details
        self._add_main_table_row(table, "Implemented By", closure_data.get('implemented_by', ''))
        impl_date = closure_data.get('implementation_date')
        self._add_main_table_row(table, "Implementation Date", impl_date.strftime('%Y-%m-%d') if impl_date else '')
        self._add_main_table_row(table, "Implementation Details", closure_data.get('implementation_details', ''))

        # Performance Metrics
        original_rate = "N/A"
        if closure_data.get('original_metrics'):
            original_rate = f"{closure_data['original_metrics']['return_summary'].iloc[0]['return_rate']:.2f}%"
        self._add_main_table_row(table, "Initial Return Rate", original_rate)
        
        new_rate = "N/A"
        if closure_data.get('new_metrics'):
            new_rate = f"{closure_data['new_metrics']['return_summary'].iloc[0]['return_rate']:.2f}%"
        self._add_main_table_row(table, "Post-Implementation Return Rate", new_rate)
        
        # Findings and Closure
        self._add_main_table_row(table, "Effectiveness Check Findings", closure_data.get('effectiveness_summary', ''))
        self._add_main_table_row(table, "Closed By", closure_data.get('closed_by', ''))
        closure_date = closure_data.get('closure_date')
        self._add_main_table_row(table, "Closure Date", closure_date.strftime('%Y-%m-%d') if closure_date else '')

    def _generate_human_factors_section(self, doc: Document, hf_data: Dict[str, Any]):
        """Generates the Human Factors section of the report."""
        doc.add_page_break()
        doc.add_heading("Human Factors and Usability Engineering Report", level=2)

        section_map = {
            "Conclusion": "conclusion_statement",
            "Descriptions of Intended Device Users, Uses, Use Environments, and Training": "descriptions",
            "Description of Device User Interface": "device_interface",
            "Summary of Known Use Problems": "known_problems",
            "Analysis of Hazards and Risks Associated with Use of the Device": "hazards_analysis",
            "Summary of Preliminary Analyses and Evaluations": "preliminary_analyses",
            "Description and Categorization of Critical Tasks": "critical_tasks",
            "Details of Human Factors Validation Testing": "validation_testing"
        }

        for title, key in section_map.items():
            doc.add_heading(title, level=3)
            content = hf_data.get(key, "No data provided for this section.")
            doc.add_paragraph(str(content))

    def generate_scar_docx(self, capa_data: Dict[str, Any], vendor_name: str) -> BytesIO:
        """Generates a standalone Supplier Corrective Action Request (SCAR) document."""
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
        
        self._add_main_table_row(main_table, "Description of Non-conformance", capa_data.get('issue_description', ''))
        self._add_main_table_row(main_table, "Our Initial Root Cause Analysis", capa_data.get('root_cause', ''))
        self._add_main_table_row(main_table, "Action Required from Supplier", "Please investigate the non-conformance, perform a thorough root cause analysis, and provide a detailed corrective action plan to prevent recurrence.")
        self._add_main_table_row(main_table, "Response Due Date", f"A formal response is required within 15 business days.")

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
