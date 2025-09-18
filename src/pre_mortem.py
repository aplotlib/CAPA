# src/pre_mortem.py

from typing import List, Dict, Optional
import json
import anthropic

class PreMortem:
    """Handles proactive Pre-Mortem analysis logic."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize Pre-Mortem AI client: {e}")

    def generate_questions(self, scenario: str) -> List[str]:
        """Generates guiding questions for a pre-mortem session."""
        if not self.client:
            return ["AI client not initialized."]

        prompt = f"""
        You are a facilitator for a pre-mortem analysis. The team has defined the following failure scenario:
        "{scenario}"

        Generate a list of 5-7 thought-provoking questions to help the team brainstorm potential reasons for this failure.
        The questions should cover different domains like Design, Manufacturing, Supply Chain, Marketing, and Customer Support.

        Return a JSON list of strings.
        Example: ["What if our key supplier delivered a faulty batch of components?", "Could a misunderstanding of user needs lead to this outcome?"]

        Return ONLY the valid JSON list.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return json.loads(response)
        except Exception as e:
            print(f"Error generating pre-mortem questions: {e}")
            return [f"Error: {e}"]

    def summarize_answers(self, qa_list: List[Dict[str, str]]) -> str:
        """Summarizes the pre-mortem answers into a report."""
        if not self.client:
            return "AI client not initialized."

        context = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in qa_list])

        prompt = f"""
        You are a project manager summarizing the results of a pre-mortem analysis.
        The team has answered a series of questions about a potential failure scenario.

        Here is the transcript:
        {context}

        Synthesize the team's answers into a coherent summary.
        1. Start with a brief overview of the key themes that emerged.
        2. Group the identified risks into logical categories (e.g., Technical Risks, Market Risks, Operational Risks).
        3. For each category, list the specific risks identified.
        4. Conclude with a list of the top 3-5 highest-priority risks that require immediate mitigation planning.

        Format the output using Markdown.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return response
        except Exception as e:
            print(f"Error summarizing pre-mortem: {e}")
            return f"Error creating summary: {e}"
