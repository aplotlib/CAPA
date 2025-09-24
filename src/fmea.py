# src/fmea.py

from typing import Dict, List, Optional
import pandas as pd
import openai
import json
from .utils import retry_with_backoff

class FMEA:
    """Handles Failure Mode and Effects Analysis logic using OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize FMEA OpenAI client: {e}")

    @retry_with_backoff()
    def suggest_failure_modes(self, issue_description: str, analysis_results: Optional[Dict]) -> List[Dict]:
        """Suggests potential failure modes based on an issue description using AI."""
        if not self.client:
            return [{"Potential Failure Mode": "AI client not initialized.", "Potential Effect(s)": "", "Potential Cause(s)": ""}]

        context_parts = [f"Issue Description: {issue_description}"]
        
        if analysis_results:
            summary = analysis_results.get('return_summary')
            if summary is not None and not summary.empty:
                summary_data = summary.iloc[0]
                context_parts.append(f"Product SKU: {summary_data.get('sku', 'N/A')}")
                context_parts.append(f"Return Rate: {summary_data.get('return_rate', 0):.2f}%")
        
        context = "\n".join(context_parts)

        system_prompt = """
        You are a quality engineer conducting a Failure Mode and Effects Analysis (FMEA).
        Based on the provided context, identify 3 to 5 potential failure modes.
        For each failure mode, suggest its potential effects on the customer and its potential root causes.
        
        Return a single JSON object with a key "failure_modes" which contains a list of objects.
        Each object in the list must have these exact keys:
        "Potential Failure Mode", "Potential Effect(s)", "Potential Cause(s)".
        Return ONLY the valid JSON object.
        """
        user_prompt = f"Here is the context for the FMEA:\n{context}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("failure_modes", [])
        except Exception as e:
            print(f"Error suggesting failure modes: {e}")
            return [{"Potential Failure Mode": "Error generating AI suggestions.", "Potential Effect(s)": str(e), "Potential Cause(s)": ""}]
