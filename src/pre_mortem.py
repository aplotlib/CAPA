# src/pre_mortem.py

from typing import List, Dict, Optional
import json
import openai
from utils import retry_with_backoff

class PreMortem:
    """Handles proactive Pre-Mortem analysis logic using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize Pre-Mortem OpenAI client: {e}")

    @retry_with_backoff()
    def generate_questions(self, scenario: str) -> List[str]:
        """Generates guiding questions for a pre-mortem session based on Ishikawa/Fishbone categories."""
        if not self.client:
            return ["AI client not initialized."]

        system_prompt = """
        You are a facilitator for a product-focused pre-mortem analysis. Your goal is to generate 5-7 thought-provoking questions based on the "Fishbone" / Ishikawa root cause analysis categories.
        The questions should explore potential failures related to:
        - **Machine/Equipment:** Tooling, manufacturing equipment, test hardware.
        - **Method/Process:** Manufacturing processes, assembly instructions, QC procedures.
        - **Material:** Raw materials, component specs, supplier quality.
        - **Manpower/People:** Training, skill issues, human error.
        - **Measurement:** Inspection methods, calibration, test accuracy.
        - **Mother Nature/Environment:** Shipping conditions, storage, use environment.
        
        Return a single JSON object with a key "questions" which contains a list of strings. Each string should be a question.
        Return ONLY the valid JSON object.
        """
        user_prompt = f"""
        The team has defined the following failure scenario:
        "{scenario}"
        
        Now, generate questions based on the Fishbone categories to explore how this failure could happen.
        Example of a good question (Method/Process): "What if the heat-sealing process for the packaging was inconsistent, leading to sterile barrier failures?"
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("questions", ["Failed to parse questions from AI."])
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from AI response: {e}")
            return ["Error parsing AI response."]
        except Exception as e:
            print(f"Error generating pre-mortem questions: {e}")
            return [f"Error: {e}"]

    @retry_with_backoff()
    def summarize_answers(self, qa_list: List[Dict[str, str]]) -> str:
        """Summarizes the pre-mortem answers into a report."""
        if not self.client:
            return "AI client not initialized."

        context = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in qa_list])

        system_prompt = """
        You are a project manager summarizing the results of a product pre-mortem analysis.
        Synthesize the team's answers into a coherent summary using Markdown.
        1. Start with a brief overview of the key themes that emerged.
        2. Group the identified risks into the Fishbone categories (Machine, Method, Material, Manpower, Measurement, Environment).
        3. For each category, list the specific risks identified.
        4. Conclude with a list of the top 3-5 highest-priority risks that require immediate mitigation planning.
        """
        user_prompt = f"Here is the transcript from the session:\n{context}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error summarizing pre-mortem: {e}")
            return f"Error creating summary: {e}"
