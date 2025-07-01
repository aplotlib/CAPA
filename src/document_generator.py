# src/document_generator.py

"""
Module for generating formal CAPA documents in a structured table format,
compliant with the provided CAPA Report.pdf example.
"""

import json
from typing import Dict, Optional, List
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import anthropic

class CapaDocumentGenerator:
    """
    Generates a formal, table-based CAPA report from structured data.
    """
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        Initializes the Anthropic client if an API key is provided.
        """
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key) if anthropic_api_key else None

    def _build_capa_prompt(self, capa_data: Dict, analysis_results: Dict) -> str:
        """Constructs a prompt for the AI to generate a JSON-structured CAPA report."""
        
        prompt = f"""
        You are a medical device quality assurance expert. Based on the following data, generate the content for a formal CAPA report.
        Return the response as a single, valid JSON object and nothing else. Do not include any introductory text or code block formatting.

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
          "issue": "Detailed description of the issue, referencing the source (e.g., audit, nonconformance). Elaborate on the provided issue summary.",
          "immediate_actions": "Describe the immediate actions to contain the issue (e.g., 'stop the bleeding').",
          "root_cause": "Elaborate on the root cause finding. Describe the analysis method if possible (e.g., 5 Whys, Fishbone).",
          "corrective_action_plan": "Detail the plan to correct the underlying issue.",
          "corrective_action_implementation": "Define responsibilities and due dates for the corrective actions (Who will do what by when?).",
          "preventive_action_plan": "Detail the plan to prevent the issue from recurring.",
          "preventive_action_implementation": "Describe how you will verify that the actions taken were effective and did not introduce new risks.",
          "effectiveness_check_plan": "What objective evidence will be gathered to demonstrate effectiveness?",
          "effectiveness_check_findings": "This section should be left as 'To be completed upon verification.'",
          "additional_comments": "Provide any relevant additional comments or leave this field empty."
        }}
        """
        return prompt

    def generate_ai_structured_content(self, capa_data: Dict, analysis_results: Dict) -> Optional[Dict]:
        """
        Generates structured CAPA content using the AI and returns it as a dictionary.
        """
        if not self.anthropic_client:
            return None
            
        prompt = self._build_capa_prompt(capa_data, analysis_results)
        
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            json_response = response.content[0].text
            # Clean potential markdown formatting
            if json_response.strip().startswith("```json"):
                json_response = json_response.strip()[7:-3]
            
            return json.loads(json_response)
        except Exception as e:
            print(f"Error generating or parsing AI content: {e}")
            return None

    def export_to_docx(self, capa_data: Dict, content: Dict) -> BytesIO:
        """
        Exports the content to a Word document formatted as a structured table.
        """
        doc = Document()
        
        # --- Header Information ---
        doc.add_heading('CAPA Report', level=1)
        doc.add_paragraph(f"CAPA Number: {capa_data.get('capa_number', 'N/A')}")
        doc.add_paragraph(f"Date: {capa_data.get('date', 'N/A')}")
        doc.add_paragraph(f"Prepared By: {capa_data.get('prepared_by', 'N/A')}")
        doc.add_paragraph() # Spacer

        # --- Main Content Table ---
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        table.autofit = False
        table.columns[0].width = int(doc.default_section.page_width * 0.25)
        table.columns[1].width = int(doc.default_section.page_width * 0.65)
        
        # Define the sections in the order they should appear
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

        # Populate the table
        for i, (title, text) in enumerate(sections):
            if i > 0:
                row_cells = table.add_row().cells
            else:
                row_cells = table.rows[0].cells
            
            # Title Cell
            p_title = row_cells[0].paragraphs[0]
            p_title.add_run(title).bold = True
            
            # Content Cell
            row_cells[1].text = text

        # --- Signature Block ---
        doc.add_paragraph()
        sig_p = doc.add_paragraph()
        sig_p.add_run("Signature, Principal Investigator: _________________________").style.font.size = Pt(11)
        sig_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        date_p = doc.add_paragraph()
        date_p.add_run("Date of Signature: _________________________").style.font.size = Pt(11)
        date_p.alignment = WD_ALIGN_PARAGRAPH.LEFT

        name_p = doc.add_paragraph()
        name_p.add_run("Printed Name, Principal Investigator: _________________________").style.font.size = Pt(11)
        name_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Save to buffer
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
