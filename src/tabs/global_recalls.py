import json
import google.generativeai as genai
from typing import Dict, List, Optional

class AIService:
    """
    Wrapper for Google Gemini API to handle Regulatory Intelligence tasks.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model_name = "gemini-2.0-flash-exp" # Or gemini-1.5-pro, using flash for speed
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    def _generate_json(self, prompt: str, system_instruction: str) -> Dict:
        """
        Helper to safely generate and parse JSON from the LLM.
        """
        if not self.model:
            return {"error": "AI Service not initialized (Missing API Key)."}

        full_prompt = f"{system_instruction}\n\n{prompt}"
        
        try:
            # Force JSON mode in prompt (or via config if supported by specific model version)
            # Adding explicit formatting instruction
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            
            text = response.text
            # Clean markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
                
            return json.loads(text.strip())
        except Exception as e:
            return {"error": str(e), "raw": text if 'text' in locals() else "No response"}

    def generate_search_keywords(self, term: str, context: str) -> List[str]:
        """
        Expands a search term into synonyms for regulatory searching.
        """
        system = "You are a regulatory search expert. Return a JSON list of 3-5 synonyms or related technical terms."
        prompt = f"Term: '{term}'. Context: '{context}'. Return strictly a JSON object: {{'keywords': ['word1', 'word2']}}"
        
        res = self._generate_json(prompt, system)
        return res.get("keywords", [])

    def assess_relevance_json(self, my_context: str, record_text: str) -> Dict[str, str]:
        """
        Analyzes a recall record against user's product context.
        """
        system = "You are a Regulatory Safety Officer. Analyze the recall for relevance to the user's product. Return JSON."
        prompt = f"""
        USER CONTEXT (My Product):
        {my_context}
        
        RECALL RECORD:
        {record_text}
        
        TASK:
        1. Compare 'My Firm' and 'My Model' against the Recall Record.
        2. If they match, Risk is HIGH.
        3. If the Recall is for a competitor but same device type, Risk is MEDIUM (Market surveillance).
        4. If unrelated, Risk is LOW.
        5. If the record is not in English, TRANSLATE the key issue in the analysis.
        
        Return JSON strictly:
        {{
            "risk": "High" | "Medium" | "Low",
            "analysis": "Short explanation. Mention if translation was applied."
        }}
        """
        return self._generate_json(prompt, system)
