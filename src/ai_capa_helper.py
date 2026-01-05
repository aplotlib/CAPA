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
        self.fast_model = "gemini-2.0-flash-exp"
        self.reasoning_model = "gemini-2.0-flash-thinking-exp"

        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Failed to initialize AI helper: {e}")

    @retry_with_backoff()
    def transcribe_audio(self, audio_file) -> str:
        """Transcribes audio input using Gemini (Multimodal capabilities)."""
        if not self.client:
            return "Error: AI client not initialized."
        
        try:
            # Gemini 2.0 Flash is multimodal and can handle audio directly
            prompt = "Transcribe the following audio file accurately."
            
            # Need to read file bytes if not already bytes
            if hasattr(audio_file, 'read'):
                audio_bytes = audio_file.read()
            else:
                audio_bytes = audio_file

            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                    prompt
                ]
            )
            return response.text
        except Exception as e:
            return f"Error transcribing audio: {e}"

    @retry_with_backoff()
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
            
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=user_prompt,
                config=config
            )
            return response.text.strip()
        except Exception as e:
            return f"Error refining input: {e}"

    @retry_with_backoff()
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
            
            response = self.client.models.generate_content(
                model=self.reasoning_model,
                contents=user_prompt,
                config=config
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Error generating CAPA suggestions: {e}")
            return {"error": f"Failed to generate CAPA suggestions: {e}"}
