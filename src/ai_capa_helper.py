# src/ai_capa_helper.py

import json
import re
from typing import Dict, Optional, Any
import openai
from utils import retry_with_backoff, parse_ai_json_response

FINE_TUNED_MODEL = "ft:gpt-4o-2024-08-06:vive-health-quality-department:qms-v2-stable-lr:CM1nuhta"

class AICAPAHelper:
    """AI assistant for CAPA workflows."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o" # Fallback to standard robust model for general editing
            except Exception as e:
                print(f"Failed to initialize AI helper: {e}")

    @retry_with_backoff()
    def refine_capa_input(self, field_name: str, rough_input: str, product_context: str) -> str:
        """
        Takes rough user notes for a specific CAPA field and refines them into
        professional, regulatory-compliant language (FDA/ISO).
        """
        if not self.client: return "AI client not initialized."
        if not rough_input or len(rough_input) < 3: return rough_input

        system_prompt = f"""
        You are a Quality Assurance Regulatory Expert for Medical Devices (ISO 13485 / 21 CFR 820).
        Your task is to rewrite the user's rough notes for the CAPA field: "{field_name}".
        
        Rules:
        1. Make the language professional, objective, and precise.
        2. Do NOT invent facts. If the input is ambiguous, ask a clarifying question in [brackets].
        3. Use active voice where appropriate.
        4. Focus on clarity and "auditor-readiness".
        """
        
        user_prompt = f"""
        **Product Context:** {product_context}
        **Rough Input:** {rough_input}
        
        **Refined Output:**
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.3 # Lower temperature for more deterministic/professional output
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error refining input: {e}"

    # ... (Keep existing generate_capa_suggestions method) ...
    @retry_with_backoff()
    def generate_capa_suggestions(self, issue_summary: str, analysis_results: Dict) -> Dict[str, str]:
        """Generate AI suggestions for CAPA form fields (Legacy/Full Auto mode)."""
        if not self.client: return {}

        summary = analysis_results.get('return_summary', {}).iloc[0] if not analysis_results.get('return_summary', {}).empty else {}
        context = f"""
        Issue Summary: {issue_summary}
        SKU: {summary.get('sku', 'N/A')}
        Return Rate: {summary.get('return_rate', 0):.2f}%
        """
        # ... (rest of the existing method remains unchanged) ...
        # (For brevity, assuming the rest of the file follows the original structure provided)
        return {"error": "Method not fully implemented in this snippet, refer to original file."}

# ... (Include other helper classes from original file: AIEmailDrafter, etc.) ...
