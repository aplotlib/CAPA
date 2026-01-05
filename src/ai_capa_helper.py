# src/ai_capa_helper.py

import json
from typing import Dict, Optional
from google import genai
from google.genai import types
from src.utils import retry_with_backoff
import src.prompts as prompts

class AICAPAHelper:
    """AI assistant for generating CAPA form suggestions using Google Gemini."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with Google Gemini API key.
        """
        self.client = None
        # Switch to 1.5-flash for better stability and quota handling
        self.fast_model = "gemini-1.5-flash" 
        self.reasoning_model = "gemini-2.0-flash-thinking-exp"

        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Failed to initialize AI helper: {e}")

    @retry_with_backoff(retries=5, backoff_in_seconds=2)
    def _generate_unsafe(self, model, contents, config=None):
        """Internal retriable method."""
        return self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )

    def transcribe_audio(self, audio_file) -> str:
        """Transcribes audio input using Gemini (Multimodal capabilities)."""
        if not self.client:
            return "Error: AI client not initialized."
        
        try:
            prompt = "Transcribe the following audio file accurately."
            
            # Need to read file bytes if not already bytes
            if hasattr(audio_file, 'read'):
                audio_bytes = audio_file.read()
            else:
                audio_bytes = audio_file

            contents = [
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                prompt
            ]
            
            # Use retriable internal method
            response = self._generate_unsafe(
                model=self.fast_model,
                contents=contents
            )
            return response.text
        except Exception as e:
            if "429" in str(e):
                return "Error: API Quota Exceeded (429). Please try again later."
            return f"Error transcribing audio: {e}"

    def refine_capa_input(self, field_name: str, rough_input: str, product_context: str) -> str:
        """
        Uses the FAST model to quickly polish text.
        """
        if not self.client: return "AI client not initialized."
        if not rough_input or len(rough_input) < 3: return rough_input

        system_prompt = prompts.CAPA_REFINE_SYSTEM.format(field_name=field_name)
        
        user_prompt = f"""
        **Product Context:** {product_context}
        **Rough Input:** {rough_input}
        **Refined Output:**
        """

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=500
            )
            
            response = self._generate_unsafe(
                model=self.fast_model,
                contents=user_prompt,
                config=config
            )
            return response.text.strip()
        except Exception as e:
            if "429" in str(e):
                return "Error: Quota exceeded (429)."
            return f"Error refining input: {e}"

    def generate_capa_suggestions(self, issue_summary: str, analysis_results: Dict) -> Dict[str, str]:
        """
        Uses the REASONING model for complex synthesis.
        """
        if not self.client: return {}

        summary = analysis_results.get('return_summary', {}).iloc[0] if not analysis_results.get('return_summary', {}).empty else {}
        
        user_prompt = prompts.CAPA_SUGGESTION_USER_TEMPLATE.format(
            issue_summary=issue_summary,
            sku=summary.get('sku', 'N/A'),
            return_rate=summary.get('return_rate', 0),
            total_returns=int(summary.get('total_returned', 0))
        )
        
        try:
            config = types.GenerateContentConfig(
                system_instruction=prompts.CAPA_SUGGESTION_SYSTEM,
                response_mime_type="application/json"
            )
            
            # Using reasoning model here, which might be more prone to 429
            # Fallback to fast model if reasoning fails? 
            # For now, just retry.
            response = self._generate_unsafe(
                model=self.reasoning_model,
                contents=user_prompt,
                config=config
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Error generating CAPA suggestions: {e}")
            if "429" in str(e):
                return {"error": "API Quota Exceeded (429). Please try again in a minute."}
            return {"error": f"Failed to generate CAPA suggestions: {e}"}
