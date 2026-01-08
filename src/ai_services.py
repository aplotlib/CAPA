import streamlit as st
import openai
from typing import Optional, Dict, Any, List, Tuple
import json
import logging
import io
from src.utils import retry_with_backoff

# Setup Logger
logger = logging.getLogger(__name__)

class AIServiceBase:
    """Base class for all AI Services using OpenAI SDK (compatible with Gemini)."""
    def __init__(self, api_key: str, provider: str = "openai", model_overrides: Optional[Dict[str, str]] = None):
        if not api_key:
            self.client = None
            logger.warning("AIService initialized without API Key.")
            return

        self.provider = provider
        model_overrides = model_overrides or {}

        try:
            if self.provider == "gemini":
                if api_key.startswith("sk-"):
                    logger.warning("Gemini API key appears to be an OpenAI key. Check GEMINI_API_KEY/GOOGLE_API_KEY.")
                # Route through Google's OpenAI-compatible endpoint
                self.client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                )
                self.fast_model = model_overrides.get("fast", "gemini-1.5-flash")
                self.reasoning_model = model_overrides.get("reasoning", "gemini-1.5-pro")
            else:
                # Default OpenAI
                self.client = openai.OpenAI(api_key=api_key)
                self.fast_model = model_overrides.get("fast", "gpt-4o-mini")
                self.reasoning_model = model_overrides.get("reasoning", "gpt-4o")
                
        except Exception as e:
            logger.error(f"Failed to initialize AI Client ({self.provider}): {e}")
            self.client = None

    def _format_gemini_key_error(self, error: Exception) -> str | None:
        if self.provider != "gemini":
            return None
        message = str(error)
        if "API_KEY_INVALID" in message or "API key not valid" in message:
            return (
                "Error: Gemini API key invalid. Set GEMINI_API_KEY or GOOGLE_API_KEY with a valid Google AI Studio key."
            )
        return None

    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def _generate_with_retry(self, model: str, messages: List[Dict[str, str]], response_format=None, temperature=0.7):
        """Internal method to execute generation with retries."""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        if response_format:
            kwargs["response_format"] = response_format
            
        return self.client.chat.completions.create(**kwargs)

    def _generate_json(self, prompt: str, system_instruction: str = None, use_reasoning: bool = False) -> Dict[str, Any]:
        """Helper to generate JSON responses safely."""
        if not self.client:
            return {"error": "AI Client not initialized (Missing API Key)."}

        messages = []
        
        # FAILSAFE: The API strictly requires the word "JSON" in the prompt 
        # when response_format is set to json_object.
        if system_instruction:
            if "json" not in system_instruction.lower():
                system_instruction = f"{system_instruction} Respond strictly in JSON format."
            messages.append({"role": "system", "content": system_instruction})
        else:
            messages.append({"role": "system", "content": "You are a helpful assistant. Respond strictly in JSON format."})
            
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._generate_with_retry(
                model=self.reasoning_model if use_reasoning else self.fast_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3
            )
            content = response.choices[0].message.content
            if not content:
                return {"error": "Empty response from AI"}
            return json.loads(content)
        except json.JSONDecodeError:
             return {"error": "Failed to decode AI response as JSON"}
        except Exception as e:
            gemini_hint = self._format_gemini_key_error(e)
            if gemini_hint:
                return {"error": gemini_hint}
            logger.error(f"AI Generation Error: {e}")
            return {"error": str(e)}

    def _generate_text(self, prompt: str, system_instruction: str = None, use_reasoning: bool = False) -> str:
        """Helper to generate text responses."""
        if not self.client:
            return "Error: AI Client not initialized (Missing API Key)."

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._generate_with_retry(
                model=self.reasoning_model if use_reasoning else self.fast_model,
                messages=messages,
                temperature=0.4
            )
            return response.choices[0].message.content
        except Exception as e:
            gemini_hint = self._format_gemini_key_error(e)
            if gemini_hint:
                return gemini_hint
            logger.error(f"AI Text Generation Error: {e}")
            return f"Error: {str(e)}"

    @staticmethod
    def _verbosity_instruction(level: str) -> str:
        if level == "Pithy":
            return "Be extremely concise. Use 3-5 bullets, max 120 words."
        if level == "Verbose":
            return "Be thorough and structured with headings and bullet points. Include key context and caveats."
        return "Be concise but clear. Use short paragraphs or bullets."

    def generate_text_with_verbosity(self, prompt: str, system_instruction: str, verbosity: str, use_reasoning: bool = False) -> str:
        verbosity_note = self._verbosity_instruction(verbosity)
        merged_instruction = f"{system_instruction}\n{verbosity_note}".strip()
        return self._generate_text(prompt, system_instruction=merged_instruction, use_reasoning=use_reasoning)

    def generate_dual_responses(
        self,
        prompt: str,
        system_instruction: str,
        concise_label: str = "Pithy",
        verbose_label: str = "Verbose",
        use_reasoning: bool = False,
    ) -> Tuple[str, str]:
        concise = self.generate_text_with_verbosity(prompt, system_instruction, concise_label, use_reasoning=use_reasoning)
