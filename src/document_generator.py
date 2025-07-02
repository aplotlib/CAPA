# src/document_generator.py

import json
from typing import Dict, Optional
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import anthropic

class CapaDocumentGenerator:
    """
    Generates a formal, table-based CAPA report from structured data,
    with an option to use AI for content generation.
    """
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initializes the Anthropic client if an API key is provided."""
        if anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        else:
            self.anthropic_client = None

    def _build_capa_prompt(self, capa_data: Dict, analysis_results: Dict) -> str:
        """Constructs a prompt for the AI to generate a JSON-structured CAPA report."""
        prompt = f"""
        You are a medical device quality assurance expert. Based on the following data, generate the content for a formal CAPA report.
        Return the response as a single, valid JSON object.

        **INPUT DATA:**
        - CAPA Number: {capa_data.get('capa_number', 'TBD')}
        - Product: {capa_data.get('product', 'TBD')}
        - SKU: {capa_data.get('sku', 'TBD')}
        - Issue Summary: {capa_data.get('issue_description', 'No description provided.')}
        - Root Cause Finding: {capa_data.get('root_cause', 'TBD')}
        - Corrective Action Plan: {capa_data.get('corrective_action', 'TBD')}
        - Preventive Action Plan: {capa_data.get('preventive_action', 'TBD')}
        - Analysis Data: Overall return rate is {analysis_results.get('overall_return_rate', 0):.2f}%.

        **JSON STRUCTURE TO GENERATE:**
        {{
          "issue": "Detailed description of the issue.",
          "immediate_actions": "Describe immediate actions taken to contain the issue.",
          "root_cause": "Elaborate on the root cause finding.",
          "corrective_action_plan": "Detail the plan to correct the underlying issue.",
          "corrective_action_implementation": "Define responsibilities and due dates for corrective actions.",
          "preventive_action_plan": "Detail the plan to prevent recurrence.",
          "preventive_action_implementation": "Describe how to verify the actions taken were effective.",
          "effectiveness_check_plan": "What objective evidence will be gathered?",
          "effectiveness_check_findings": "To be completed upon verification.",
          "additional_comments": "Any relevant additional comments."
        }}
        """
        return prompt

    def generate_ai_structured_content(self, capa_data: Dict, analysis_results: Dict) -> Optional[Dict]:
        """Generates structured CAPA content using the AI model."""
        if not self.anthropic_client:
            # Fallback to a simple structure if no API key is provided
            return {
                "issue": capa_data.get('issue_description', ''),
                "immediate_actions": "To be determined.",
                "root_cause": capa_data.get('root_cause', ''),
                "corrective_action_plan": capa_data.get('corrective_action', ''),
                "corrective_action_implementation": "To be determined.",
                "preventive_action_plan": capa_data.get('preventive_action', ''),
                "preventive_action_implementation": "To be determined.",
                "effectiveness_check_plan": "To be determined.",
                "effectiveness_check_findings": "To be completed upon verification.",
                "additional_comments": ""
            }
        
        prompt = self._build_capa_prompt(capa_data, analysis_results)
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            json_response = response.content[0].text
            return json.loads(json_response)
        except Exception as e:
            print(f"Error generating or parsing AI content: {e}")
            return None

    def export_to_docx(self, capa_data: Dict, content: Dict) -> BytesIO:
        """Exports the content to a Word document formatted as a structured table."""
        doc = Document()
        doc.add_heading('CAPA Report', level=1)
        doc.add_paragraph(f"CAPA Number: {capa_data.get('capa_number', 'N/A')}")
        doc.add_paragraph(f"Date: {capa_data.get('date', 'N/A')}")
        doc.add_paragraph(f"Prepared By: {capa_data.get('prepared_by', 'N/A')}")
        doc.add_paragraph()

        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        
        sections = [
            ("Issue", content.get('issue', '')),
            ("Immediate Actions/Corrections", content.get('immediate_actions', '')),
            ("Root Cause", content.get('root_cause', '')),
            ("Corrective Action", content.get('corrective_action_plan', '')),
            ("Implementation of Corrective Actions", content.get('corrective_action_implementation', '')),
            ("Preventive action", content.get('preventive_action_plan', '')),
            ("Implementation of Preventive Actions", content.get('preventive_action_implementation', '')),
            ("Effectiveness Check Plan", content.get('effectiveness_check_plan', '')),
            ("Effectiveness Check Findings", content.get('effectiveness_check_findings', '')),
            ("Additional Comments", content.get('additional_comments', ''))
        ]

        for i, (title, text) in enumerate(sections):
            row_cells = table.add_row().cells if i > 0 else table.rows[0].cells
            p_title = row_cells[0].paragraphs[0]
            p_title.add_run(title).bold = True
            row_cells[1].text = text

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
