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
    Generates comprehensive Word and Excel documents from session data.
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
        # Simple cleaning of markdown for paragraph text
        cleaned_text = text.replace('**', '').replace('`', '').replace('###', '').replace('##', '')
        doc.add_paragraph(cleaned_text)

    def _parse_and_add_markdown_table(self, doc, markdown_text: str, title: str):
        """
        NEW: Parses a Markdown table string and adds it as a proper table to the document,
        cleaning up formatting artifacts.
        """
        if not markdown_text:
            return
        
        doc.add_page_break()
        doc.add_heading(title, level=2)
        
        lines = [line.strip() for line in markdown_text.strip().split('\n') if line.strip() and not line.strip().startswith(('###', '##'))]
        
        if not lines or '|' not in lines[0]:
            doc.add_paragraph(markdown_text) # Fallback for non-table content
            return
            
        header_line = lines[0]
        headers = [h.strip() for h in header_line.strip('|').split('|')]
        
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        for i, header in enumerate(headers):
            hdr_cells[i].text = header.replace('**', '')

        data_lines = [line for line in lines if '|' in line and '---' not in line and line != header_line]

        for line in data_lines:
            row_cells = table.add_row().cells
            cells = [c.strip().replace('**', '').replace('`', '') for c in line.strip('|').split('|')]
            for i, cell_text in enumerate(cells):
                if i < len(row_cells):
                    row_cells[i].text = cell_text
        
    def _generate_executive_summary(self, session_data: Dict[str, Any]) -> str:
        """Uses AI to generate a high-level executive summary."""
        ai_context_helper = session_data.get('ai_context_helper')
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
        
        summary_text = self._generate_executive_summary(session_data)
        doc.add_heading("Executive Summary", level=2)
        doc.add_paragraph(summary_text)
        
        if "CAPA Form" in selected_sections and session_data.get('capa_data'):
            self._generate_capa_form_section(doc, session_data['capa_data'])

        if "CAPA Closure" in selected_sections and session_data.get('capa_closure_data'):
            self._generate_capa_closure_section(doc, session_data['capa_closure_data'])

        if "FMEA" in selected_sections and session_data.get('fmea_data') is not None:
            self._add_df_as_table(doc, session_data['fmea_data'], "Failure Mode and Effects Analysis (FMEA)")

        if "ISO 14971 Assessment" in selected_sections and session_data.get('risk_assessment'):
            self._parse_and_add_markdown_table(doc, session_data['risk_assessment'], "ISO 14971 Risk Assessment")
            
        if "URRA" in selected_sections and session_data.get('urra'):
            self._parse_and_add_markdown_table(doc, session_data['urra'], "Use-Related Risk Analysis (URRA)")

        if "Vendor Email Draft" in selected_sections and session_data.get('vendor_email_draft'):
            self._add_markdown_text(doc, session_data['vendor_email_draft'], "Vendor Communication Draft")

        if "Human Factors Report" in selected_sections and session_data.get('human_factors_data'):
            self._generate_human_factors_section(doc, session_data['human_factors_data'])

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    def _generate_capa_form_section(self, doc: Document, capa_data: Dict[str, Any]):
        doc.add_page_break()
        doc.add_heading("Corrective and Preventive Action (CAPA) Details", level=2)
        table = doc.add_table(rows=1, cols=2, style='Table Grid')
        table.columns[0].width = Inches(2.0)
        table.columns[1].width = Inches(5.5)
        field_map = {
            "CAPA Number": capa_data.get('capa_number', 'N/A'),
            "Product Name / Model": capa_data.get('product_name', 'N/A'),
            "Initiation Date": capa_data.get('date', date.today()).strftime('%Y-%m-%d'),
            "Problem Description": capa_data.get('issue_description', ''),
            "Immediate Actions/Corrections": capa_data.get('immediate_actions', ''),
            "Root Cause Analysis": capa_data.get('root_cause', ''),
            "Corrective Action Plan": capa_data.get('corrective_action', ''),
            "Preventive Action Plan": capa_data.get('preventive_action', ''),
            "Effectiveness Check Plan": capa_data.get('effectiveness_verification_plan', '')
        }
        for heading, content in field_map.items():
            self._add_main_table_row(table, heading, content)
    
    def _generate_capa_closure_section(self, doc: Document, closure_data: Dict[str, Any]):
        if not closure_data.get('original_capa'): return
        doc.add_page_break()
        doc.add_heading("CAPA Effectiveness Check & Closure", level=2)
        table = doc.add_table(rows=0, cols=2, style='Table Grid')
        table.columns[0].width = Inches(2.0)
        table.columns[1].width = Inches(5.5)
        self._add_main_table_row(table, "Effectiveness Check Findings", closure_data.get('effectiveness_summary', ''))
        self._add_main_table_row(table, "Closed By", closure_data.get('closed_by', ''))
        closure_date = closure_data.get('closure_date')
        self._add_main_table_row(table, "Closure Date", closure_date.strftime('%Y-%m-%d') if closure_date else '')

    def _generate_human_factors_section(self, doc: Document, hf_data: Dict[str, Any]):
        doc.add_page_break()
        doc.add_heading("Human Factors and Usability Engineering Report", level=2)
        section_map = {
            "Conclusion": "conclusion_statement", "Descriptions": "descriptions",
            "Device User Interface": "device_interface", "Known Use Problems": "known_problems",
            "Hazards and Risks Analysis": "hazards_analysis", "Preliminary Analyses": "preliminary_analyses",
            "Critical Tasks": "critical_tasks", "Validation Testing": "validation_testing"
        }
        for title, key in section_map.items():
            doc.add_heading(title, level=3)
            doc.add_paragraph(str(hf_data.get(key, "No data provided.")))

    def _add_section_heading(self, doc, text: str):
        """Helper to add a bolded section heading."""
        p = doc.add_paragraph()
        p.add_run(text).bold = True

    def generate_project_charter_docx(self, charter_data: Dict[str, Any]) -> BytesIO:
        """
        NEW: Generates a project charter Word document.
        """
        doc = Document()
        doc.add_heading(charter_data.get('project_name', 'Project Charter'), level=1)
        doc.add_paragraph(f"Date: {date.today().strftime('%Y-%m-%d')}")
        
        doc.add_heading("1. Project Overview & Business Case", level=2)
        self._add_section_heading(doc, "Problem Statement")
        doc.add_paragraph(charter_data.get('problem_statement', 'N/A'))
        self._add_section_heading(doc, "Project Goal")
        doc.add_paragraph(charter_data.get('project_goal', 'N/A'))
        self._add_section_heading(doc, "Project Scope")
        doc.add_paragraph(charter_data.get('scope', 'N/A'))

        doc.add_heading("2. Regulatory & Quality Strategy", level=2)
        self._add_section_heading(doc, "Device Classification (FDA)")
        doc.add_paragraph(charter_data.get('device_classification', 'N/A'))
        self._add_section_heading(doc, "Applicable Standards & Regulations")
        standards = charter_data.get('applicable_standards', [])
        if standards:
            for standard in standards:
                doc.add_paragraph(standard, style='List Bullet')
        else:
            doc.add_paragraph("N/A")

        doc.add_heading("3. Key Stakeholders", level=2)
        doc.add_paragraph(charter_data.get('stakeholders', 'N/A'))
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    def generate_scar_docx(self, capa_data: Dict[str, Any], vendor_name: str) -> BytesIO:
        # This function remains the same
        pass

    def generate_capa_tracker_excel(self, session_data: Dict[str, Any]) -> BytesIO:
        """
        NEW: Generates an Excel file with key CAPA data for tracking in a master sheet.
        """
        capa_data = session_data.get('capa_data', {})
        status = "Closed" if capa_data.get('closure_date') else "Open"
        
        data = {
            'CAPA Number': [capa_data.get('capa_number', 'N/A')],
            'Status': [status],
            'Product SKU': [capa_data.get('product_name', 'N/A')],
            'Initiation Date': [capa_data.get('date')],
            'Closure Date': [capa_data.get('closure_date')],
            'Issue Description': [capa_data.get('issue_description', '')],
            'Root Cause': [capa_data.get('root_cause', '')],
            'Corrective Action': [capa_data.get('corrective_action', '')],
        }
        df = pd.DataFrame(data)

        for date_col in ['Initiation Date', 'Closure Date']:
            if not df[date_col].isna().all():
                df[date_col] = pd.to_datetime(df[date_col]).dt.strftime('%Y-%m-%d')

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='CAPA_Tracker_Data')
            for i, col in enumerate(df.columns):
                col_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                writer.sheets['CAPA_Tracker_Data'].set_column(i, i, col_len)
        output.seek(0)
        return output
