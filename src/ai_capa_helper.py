# src/ai_capa_helper.py

import json
from typing import Dict, Optional
import openai
from utils import retry_with_backoff
import src.prompts as prompts  # Import the new prompts file

class AICAPAHelper:
    """AI assistant for generating CAPA form suggestions using OpenAI."""

    def __init__(self, api_key: Optional[str] = None, models: Dict[str, str] = None):
        """
        Initialize with OpenAI API key and Model Config.
        """
        self.client = None
        self.fast_model = "gpt-4o-mini"
        self.reasoning_model = "gpt-4o"
        
        if models:
            self.fast_model = models.get('fast', "gpt-4o-mini")
            self.reasoning_model = models.get('reasoning', "gpt-4o")

        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
            except Exception as e:
                print(f"Failed to initialize AI helper: {e}")

    @retry_with_backoff()
    def transcribe_audio(self, audio_file) -> str:
        """Transcribes audio input using Whisper."""
        if not self.client:
            return "Error: AI client not initialized."
        
        try:
            audio_file.name = "input_audio.wav"
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
            return transcript
        except Exception as e:
            return f"Error transcribing audio: {e}"

    @retry_with_backoff()
    def refine_capa_input(self, field_name: str, rough_input: str, product_context: str) -> str:
        """
        Uses the FAST model to quickly polish text.
        """
        if not self.client: return "AI client not initialized."
        if not rough_input or len(rough_input) < 3: return rough_input

        # Use centralized prompt
        system_prompt = prompts.CAPA_REFINE_SYSTEM.format(field_name=field_name)
        
        user_prompt = f"""
        **Product Context:** {product_context}
        **Rough Input:** {rough_input}
        **Refined Output:**
        """

        try:
            # Uses FAST model for speed and cost efficiency
            response = self.client.chat.completions.create(
                model=self.fast_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.3 
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error refining input: {e}"

    @retry_with_backoff()
    def generate_capa_suggestions(self, issue_summary: str, analysis_results: Dict) -> Dict[str, str]:
        """
        Uses the REASONING model for complex synthesis.
        """
        if not self.client: return {}

        summary = analysis_results.get('return_summary', {}).iloc[0] if not analysis_results.get('return_summary', {}).empty else {}
        
        # Format user prompt using template
        user_prompt = prompts.CAPA_SUGGESTION_USER_TEMPLATE.format(
            issue_summary=issue_summary,
            sku=summary.get('sku', 'N/A'),
            return_rate=summary.get('return_rate', 0),
            total_returns=int(summary.get('total_returned', 0))
        )
        
        try:
            # Uses REASONING model for complex quality logic
            response = self.client.chat.completions.create(
                model=self.reasoning_model,
                messages=[
                    {"role": "system", "content": prompts.CAPA_SUGGESTION_SYSTEM},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error generating CAPA suggestions: {e}")
            return {"error": f"Failed to generate CAPA suggestions: {e}"}
