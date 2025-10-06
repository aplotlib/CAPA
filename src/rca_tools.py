# src/rca_tools.py

from typing import Dict, List
import openai
from utils import retry_with_backoff

class RootCauseAnalyzer:
    """
    A class to provide guided root cause analysis tools with AI assistance.
    """
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o"

    @retry_with_backoff()
    def suggest_next_why(self, previous_answer: str) -> str:
        """
        Uses AI to suggest the next logical "Why?" question in a 5 Whys analysis.
        """
        system_prompt = """
        You are a quality engineering expert facilitating a 5 Whys root cause analysis.
        A user has provided an answer to a "Why?" question. Your task is to formulate the next logical "Why?" question to dig deeper.
        The question should be concise and directly challenge the previous answer.
        Return ONLY the suggested question as a single string.
        """
        user_prompt = f"The previous answer was: '{previous_answer}'. What is the next 'Why?' question?"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=100,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating suggestion: {e}"

    @retry_with_backoff()
    def suggest_fishbone_causes(self, problem: str, category: str) -> List[str]:
        """
        Uses AI to brainstorm potential causes for a specific category in a Fishbone diagram.
        """
        system_prompt = """
        You are an expert in root cause analysis, brainstorming for a Fishbone (Ishikawa) diagram.
        Given a problem statement and a specific cause category, generate a list of 3-5 plausible potential causes that fit within that category.
        Return a single JSON object with a key "causes" which contains a list of strings.
        Return ONLY the valid JSON object.
        """
        user_prompt = f"""
        Problem Statement (Effect): "{problem}"
        Cause Category: "{category}"

        Brainstorm potential causes for this category.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=500,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            result = response.json()
            # The API response is a JSON string, so we need to parse it twice.
            import json
            parsed_result = json.loads(result['choices'][0]['message']['content'])
            return parsed_result.get("causes", [])
        except Exception as e:
            return [f"Error generating suggestions: {e}"]

    def generate_fishbone_markdown(self, problem: str, causes: Dict[str, List[str]]) -> str:
        """
        Generates a Markdown representation of the Fishbone diagram.
        """
        markdown = f"## Fishbone Diagram for: {problem}\n\n"
        for category, cause_list in causes.items():
            markdown += f"### {category}\n"
            if cause_list:
                for cause in cause_list:
                    markdown += f"- {cause}\n"
            else:
                markdown += "- *(No causes listed)*\n"
            markdown += "\n"
        return markdown
