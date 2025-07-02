# src/document_generator.py

import json
from typing import Dict, Optional, List
from io import BytesIO
from docx import Document
import anthropic

class CapaDocumentGenerator:
    """Generates a formal, table-based CAPA report from structured data."""
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initializes the Anthropic client if an API key is provided."""
        if anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        else:
            self.anthropic_client = None

    def _build_capa_prompt(self, capa_data: Dict, analysis_results: Dict) -> str:
        """Constructs a detailed prompt for the AI to generate a JSON-structured CAPA report."""
        summary_df = analysis_results.get('return_summary')
        return_rate = summary_df['return_rate'].iloc[0] if summary_df is not None and not summary_df.empty else 'N/A'

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
        - Analysis Data: The return rate for this SKU is {return_rate}%.

        **JSON STRUCTURE TO GENERATE:**
        {{
          "issue": "Detailed description of the issue, elaborating on the provided summary and incorporating the return rate.",
          "immediate_actions": "Describe immediate actions to contain the issue (e.g., quarantine stock, notify customers).",
          "root_cause": "Elaborate on the root cause finding. Suggest potential investigation methods if the finding is brief.",
          "corrective_action_plan": "Detail the plan to correct the underlying issue, including specific, actionable steps.",
          "corrective_action_implementation": "Define responsibilities and due dates for corrective actions (e.g., 'Engineering team to complete redesign by Q3').",
          "preventive_action_plan": "Detail the plan to prevent recurrence across similar products or processes.",
          "preventive_action_implementation": "Describe how to verify the actions taken were effective (e.g., 'Monitor return rates for 6 months').",
          "effectiveness_check_plan": "What objective evidence will be gathered to prove the solution worked?",
          "effectiveness_check_findings": "This section should be left as 'To be completed upon verification.'",
          "additional_comments": "Any relevant additional comments or context."
        }}
        """
        return prompt

    def generate_ai_structured_content(self, capa_data: Dict, analysis_results: Dict) -> Optional[Dict]:
        """Generates structured CAPA content using the AI model."""
        if not self.anthropic_client:
            st.error("Anthropic API key not configured.")
            return None # Or return a default structure
        
        prompt = self._build_capa_prompt(capa_data, analysis_results)
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            # The response is a JSON string in the 'text' attribute of the first content block
            json_response_text = response.content[0].text
            return json.loads(json_response_text)
        except Exception as e:
            print(f"Error generating or parsing AI content: {e}")
            return None

    def export_to_docx(self, capa_data: Dict, content: Dict) -> BytesIO:
        """Exports the content to a Word document formatted as a structured table."""
        doc = Document()
        doc.add_heading('CAPA Report', level=1)
        # Add header info...
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        # Add table content...
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
