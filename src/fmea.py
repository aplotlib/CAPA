# src/fmea.py

from typing import Dict, List, Optional
import pandas as pd
import openai
import json
from utils import retry_with_backoff

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
    def suggest_failure_modes(self, issue_description: str, analysis_results: Optional[Dict], user_examples: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Suggests potential failure modes. If user_examples are provided, it expands on them.
        Otherwise, it generates initial suggestions based on the issue description.
        """
        if not self.client:
            return [{"Potential Failure Mode": "AI client not initialized.", "Potential Effect(s)": "", "Potential Cause(s)": ""}]

        context_parts = [f"Issue Description: {issue_description}"]
        if analysis_results and analysis_results.get('return_summary') is not None and not analysis_results['return_summary'].empty:
            summary_data = analysis_results['return_summary'].iloc[0]
            context_parts.append(f"Product SKU: {summary_data.get('sku', 'N/A')}")
            context_parts.append(f"Return Rate: {summary_data.get('return_rate', 0):.2f}%")
        
        context = "\n".join(context_parts)
        
        if user_examples:
            examples_str = json.dumps(user_examples, indent=2)
            system_prompt = """
            You are a senior quality engineer reviewing a preliminary FMEA. A user has provided initial failure modes.
            Your task is to expand on their work by identifying 3-4 additional, distinct failure modes they might have missed.
            Focus on different categories of risk like usability, long-term material degradation, manufacturing process errors, or environmental factors.
            Do NOT repeat the user's examples in your response.
            Return a single JSON object with a key "failure_modes" containing a list of objects.
            Each object must have these keys: "Potential Failure Mode", "Potential Effect(s)", "Potential Cause(s)".
            Return ONLY the valid JSON object.
            """
            user_prompt = f"## Overall Context\n{context}\n\n## User's Initial FMEA Entries\n{examples_str}"
        else:
            system_prompt = """
            You are a quality engineer conducting an FMEA. Based on the context, identify 3-5 potential failure modes.
            For each, suggest its potential effects and causes.
            Return a single JSON object with a key "failure_modes" containing a list of objects.
            Each object must have these keys: "Potential Failure Mode", "Potential Effect(s)", "Potential Cause(s)".
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
