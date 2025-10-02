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
    def expand_failure_modes(self, issue_description: str, analysis_results: Optional[Dict], user_examples: List[Dict]) -> List[Dict]:
        """
        Suggests additional failure modes based on user examples and overall context.
        """
        if not self.client:
            return [{"Potential Failure Mode": "AI client not initialized.", "Potential Effect(s)": "", "Potential Cause(s)": ""}]

        context_parts = [f"Issue Description: {issue_description}"]
        if analysis_results and analysis_results.get('return_summary') is not None:
            summary_data = analysis_results['return_summary'].iloc[0]
            context_parts.append(f"Product SKU: {summary_data.get('sku', 'N/A')}")
            context_parts.append(f"Return Rate: {summary_data.get('return_rate', 0):.2f}%")
        
        examples_str = json.dumps(user_examples, indent=2)
        context = "\n".join(context_parts)

        system_prompt = """
        You are a senior quality engineer reviewing a preliminary FMEA.
        A user has provided some initial failure modes. Your task is to expand on their work by identifying 3-4 additional, distinct failure modes they might have missed.
        Focus on different categories of risk like usability, long-term material degradation, manufacturing process errors, or environmental factors.
        
        Return a single JSON object with a key "failure_modes" which contains a list of objects.
        Each object in the list must have these exact keys:
        "Potential Failure Mode", "Potential Effect(s)", "Potential Cause(s)".
        Do NOT repeat the user's examples in your response.
        Return ONLY the valid JSON object.
        """
        user_prompt = f"## Overall Context\n{context}\n\n## User's Initial FMEA Entries\n{examples_str}"

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
            print(f"Error expanding failure modes: {e}")
            return [{"Potential Failure Mode": "Error generating AI suggestions.", "Potential Effect(s)": str(e), "Potential Cause(s)": ""}]
