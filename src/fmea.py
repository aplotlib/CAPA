# src/fmea.py

from typing import Dict, List, Optional
import pandas as pd
import anthropic
import json

class FMEA:
    """Handles Failure Mode and Effects Analysis logic."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize FMEA AI client: {e}")

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

        prompt = f"""
        You are a quality engineer conducting a Failure Mode and Effects Analysis (FMEA).
        Based on the provided context, identify 3 to 5 potential failure modes.

        Context:
        {context}

        For each failure mode, suggest its potential effects on the customer and its potential root causes.
        
        Return a JSON list of objects. Each object must have these exact keys:
        "Potential Failure Mode", "Potential Effect(s)", "Potential Cause(s)".

        Example:
        [
          {{
            "Potential Failure Mode": "Seal on the device housing fails prematurely.",
            "Potential Effect(s)": "Loss of sterility, internal components exposed to moisture, device malfunction.",
            "Potential Cause(s)": "Incorrect material specification for seal, high temperature during storage, manufacturing defect in the sealing process."
          }}
        ]

        Return ONLY the valid JSON list.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return json.loads(response)
        except Exception as e:
            print(f"Error suggesting failure modes: {e}")
            return [{"Potential Failure Mode": "Error generating AI suggestions.", "Potential Effect(s)": str(e), "Potential Cause(s)": ""}]
