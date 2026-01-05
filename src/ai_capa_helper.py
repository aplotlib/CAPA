import json
from typing import Dict, Optional
import openai
import io
from src.utils import retry_with_backoff
import src.prompts as prompts

class AICAPAHelper:
    """AI assistant for generating CAPA form suggestions using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with OpenAI API key.
        """
        self.client = None
        self.fast_model = "gpt-4o-mini"
        self.reasoning_model = "gpt-4o"

        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
            except Exception as e:
                print(f"Failed to initialize AI helper: {e}")

    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def _generate_unsafe(self, model, messages, response_format=None, temperature=0.7):
        """Internal retriable method."""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        if response_format:
            kwargs["response_format"] = response_format
            
        return self.client.chat.completions.create(**kwargs)

    def transcribe_audio(self, audio_file) -> str:
        """Transcribes audio input using OpenAI Whisper."""
        if not self.client:
            return "Error: AI client not initialized."
        
        try:
            # Handle bytes or file-like
            if isinstance(audio_file, bytes):
                f = io.BytesIO(audio_file)
                f.name = "audio.wav"
                audio_file = f
            
            # Using Whisper-1 model
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            return response.text
        except Exception as e:
            return f"Error transcribing audio: {e}"

    def refine_capa_input(self, field_name: str, rough_input: str, product_context: str) -> str:
        """
        Uses the FAST model to quickly polish text.
        """
        if not self.client: return "AI client not initialized."
        if not rough_input or len(rough_input) < 3: return rough_input

        # This method produces TEXT, not JSON, so no special prompt fixes needed
        messages = [
            {"role": "system", "content": prompts.CAPA_REFINE_SYSTEM.format(field_name=field_name)},
            {"role": "user", "content": f"**Product Context:** {product_context}\n**Rough Input:** {rough_input}\n**Refined Output:**"}
        ]

        try:
            response = self._generate_unsafe(
                model=self.fast_model,
                messages=messages,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
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
        
        # FAILSAFE: Ensure "JSON" is in system prompt
        system_content = prompts.CAPA_SUGGESTION_SYSTEM
        if "json" not in system_content.lower():
             system_content += " You must respond strictly in JSON format."

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self._generate_unsafe(
                model=self.reasoning_model,
                messages=messages,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"Error generating CAPA suggestions: {e}")
            return {"error": f"Failed to generate CAPA suggestions: {e}"}
