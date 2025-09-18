# src/document_generator.py

import json
from typing import Dict, Optional
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

    def generate_ai_structured_content(self, capa_data: Dict, analysis_results: Dict) -> Dict:
        """Generate structured CAPA content using AI model."""
        if not self.client:
            return self._get_default_template(capa_data, analysis_results)
        
        summary = analysis_results.get('return_summary', {}).iloc[0] if not analysis_results.get('return_summary', {}).empty else {}
        prompt = f"""
        You are a medical device QA expert creating a formal CAPA report.
        Based on the following data, generate a comprehensive JSON for each section.
        - CAPA Number: {capa_data.get('capa_number', 'TBD')}
        - Product: {capa_data.get('product', 'TBD')}
        - Return Rate: {summary.get('return_rate', 'N/A')}%
        - Quality Insights: {analysis_results.get('insights', 'N/A')}

        Generate a complete CAPA report with the JSON structure: {{
          "executive_summary": "...", "issue": "...", "immediate_actions": "...",
          "investigation_methodology": "...", "root_cause": "...", "corrective_action_plan": "...",
          "preventive_action_plan": "...", "effectiveness_check_plan": "..."
        }}
        Return ONLY valid JSON.
        """
        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return json.loads(response)
        except Exception as e:
            print(f"Error generating AI content: {e}")
            return self._get_default_template(capa_data, analysis_results)

    def _get_default_template(self, capa_data: Dict, analysis_results: Dict) -> Dict:
        return {"executive_summary": "Default executive summary.", "issue": "Default issue description."}

    def export_to_docx(self, capa_data: Dict, content: Dict) -> BytesIO:
        """Export content to a professionally formatted Word document."""
        doc = Document()
        doc.add_heading(f"CAPA Report: {capa_data.get('product', 'N/A')}", level=1)
        doc.add_paragraph(f"CAPA Number: {capa_data.get('capa_number', 'TBD')}\nDate: {capa_data.get('date', 'TBD')}")

        for section, text in content.items():
            doc.add_heading(section.replace('_', ' ').title(), level=2)
            doc.add_paragraph(str(text))

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
        
    def export_fmea_to_excel(self, fmea_df: pd.DataFrame, sku: str) -> BytesIO:
        """Export FMEA data to an Excel file."""
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            fmea_df.to_excel(writer, sheet_name='FMEA', index=False)
            writer.book.worksheets[0].column_dimensions['A'].width = 30
            writer.book.worksheets[0].column_dimensions['B'].width = 30
            writer.book.worksheets[0].column_dimensions['D'].width = 30
            writer.book.worksheets[0].column_dimensions['F'].width = 30
        buffer.seek(0)
        return buffer
        
    def export_text_to_docx(self, text: str, title: str) -> BytesIO:
        """Export plain text to a formatted Word document."""
        doc = Document()
        doc.add_heading(title, level=1)
        doc.add_paragraph(text)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
