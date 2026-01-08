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
        verbose = self.generate_text_with_verbosity(prompt, system_instruction, verbose_label, use_reasoning=use_reasoning)
        return concise, verbose

# --- Specialized Services ---

class AIService(AIServiceBase):
    def analyze_text(self, prompt: str, system_instruction: str = None) -> str:
        return self._generate_text(prompt, system_instruction)

    def transcribe_and_structure(self, audio_bytes: bytes, context: str = "") -> Dict[str, str]:
        if not self.client:
             return {"error": "AI Client not initialized."}

        # 1. Transcribe (Note: Google compatible endpoint doesn't support 'whisper-1' usually, 
        # so this might fail if using Gemini Key. We add a check.)
        if self.provider == 'gemini':
             return {"error": "Audio transcription is currently optimized for OpenAI keys only."}

        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav" 
            
            transcript_response = self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            transcript_text = transcript_response.text
        except Exception as e:
            return {"error": f"Transcription failed: {str(e)}"}

        # 2. Extract Structure with LLM
        system_prompt = "You are a Quality Assurance Assistant. Extract fields from the transcript. Return JSON."
        user_prompt = f"""
        CONTEXT: {context}
        TRANSCRIPT: {transcript_text}
        
        TASK:
        1. Parse the transcript.
        2. Extract fields: Issue Description, Root Cause, Immediate Actions.
        Return JSON.
        """
        return self._generate_json(user_prompt, system_prompt, use_reasoning=True)

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
        return self._generate_json(prompt, system, use_reasoning=True)

    def analyze_meeting_transcript(self, transcript_text: str) -> Dict[str, str]:
        system_prompt = "You are a QA Expert. Extract CAPA details (issue, root cause, actions) from notes. Return JSON."
        user_prompt = f"Analyze this transcript and return a JSON object:\n{transcript_text}"
        return self._generate_json(user_prompt, system_prompt, use_reasoning=True)

    def screen_recalls(self, product_description: str) -> str:
        system = "You are a Regulatory Expert. Screen device against FDA/MDR recall databases."
        user = f"Screen this device: {product_description}. List common recall reasons and keywords."
        return self._generate_text(user, system)

    def generate_search_keywords(self, product_name: str, description: str) -> list:
        system = "You are a Regulatory Search Expert. Generate search terms for recall databases."
        prompt = f"""
        Product: {product_name}
        Description: {description}
        
        Task:
        1. Identify the core device type (e.g., "infusion pump").
        2. Identify 3-4 synonyms or related medical terms (e.g., "syringe pump", "parenteral", "drug delivery").
        3. Identify potential hazard keywords (e.g., "occlusion", "software error").
        
        Return JSON: {{ "keywords": ["term1", "term2", "term3"] }}
        """
        response = self._generate_json(prompt, system, use_reasoning=True)
        return response.get('keywords', [])

    def assess_relevance(self, product_desc: str, recall_text: str) -> str:
        system = "You are a Safety Engineer. Assess if a recall is relevant to our product."
        prompt = f"""
        Our Product: {product_desc}
        Recall Data: {recall_text}
        
        Is this recall relevant to our product's technology or risks?
        Answer with 'High', 'Medium', or 'Low' followed by a 1-sentence explanation.
        """
        return self._generate_text(prompt, system)

class DesignControlsTriager(AIServiceBase):
    def generate_design_controls(self, name: str, ifu: str, user_needs: str, tech_reqs: str, risks: str) -> Dict[str, str]:
        system = "You are a Medical Device Systems Engineer (ISO 13485). Generate Design Control documentation in JSON format."
        prompt = f"""
        Product: {name}
        Description: {ifu}
        
        Inputs:
        - User Needs: {user_needs}
        - Tech Reqs: {tech_reqs}
        - Risks: {risks}
        
        Generate a JSON with keys: 'traceability_matrix', 'inputs', 'outputs', 'verification', 'validation', 'plan', 'transfer', 'dhf'.
        Each value should be a markdown string suitable for a report.
        """
        return self._generate_json(prompt, system, use_reasoning=True)

class UrraGenerator(AIServiceBase):
    def generate_urra(self, product_name: str, product_desc: str, user: str, environment: str) -> Dict[str, Any]:
        system = "You are a Usability Engineer (IEC 62366). Generate a Use-Related Risk Analysis (URRA). Return JSON."
        prompt = f"""
        Device: {product_name}
        Context: {product_desc}
        User: {user}
        Env: {environment}
        
        Generate a list of 5-7 critical usability risks.
        Return JSON with key 'urra_rows' containing a list of objects with keys:
        'Task', 'Hazard', 'Severity' (1-5), 'Probability' (1-5), 'Risk Level' (Low/Med/High), 'Mitigation'.
        """
        return self._generate_json(prompt, system, use_reasoning=True)

class ManualWriter(AIServiceBase):
    def generate_manual_section(self, section_title: str, product_name: str, product_ifu: str, user_inputs: Dict, target_language: str) -> str:
        system = f"You are a Technical Writer. Write a user manual section in {target_language}."
        prompt = f"""
        Section: {section_title}
        Product: {product_name}
        Context: {product_ifu}
        Key Details: {user_inputs}
        
        Write professional, clear, compliant content for this section using Markdown.
        """
        return self._generate_text(prompt, system)

class ProjectCharterHelper(AIServiceBase):
    def generate_charter_draft(self, product_name: str, problem_statement: str, target_user: str) -> Dict[str, Any]:
        system = "You are a Project Manager in MedTech. Draft a Project Charter in JSON format."
        prompt = f"""
        Project: {product_name}
        Problem: {problem_statement}
        User: {target_user}
        
        Return JSON with keys: 'project_goal', 'scope', 'device_classification', 'applicable_standards' (list), 'stakeholders'.
        """
        return self._generate_json(prompt, system, use_reasoning=True)

class VendorEmailDrafter(AIServiceBase):
    def draft_vendor_email(self, goal: str, analysis_results: Any, sku: str, vendor: str, contact: str, english_level: int) -> str:
        system = "You are a Quality Manager writing to a supplier. Be professional and data-driven."
        prompt = f"""
        Vendor: {vendor}, Contact: {contact}
        SKU: {sku}
        Goal: {goal}
        Recipient English Level: {english_level}/5 (Adjust complexity accordingly).
        
        Draft the email body.
        """
        return self._generate_text(prompt, system)

class HumanFactorsHelper(AIServiceBase):
    def generate_hf_report_from_answers(self, name: str, ifu: str, answers: Dict) -> Dict[str, str]:
        system = "You are a Human Factors Engineer (IEC 62366). Draft an HFE Report in JSON."
        prompt = f"""
        Device: {name}
        User Profile: {answers.get('user_profile')}
        Critical Tasks: {answers.get('critical_tasks')}
        Harms: {answers.get('potential_harms')}
        
        Return JSON with keys: 'conclusion_statement', 'descriptions', 'device_interface', 'known_problems', 'hazards_analysis', 'preliminary_analyses', 'critical_tasks', 'validation_testing'.
        """
        return self._generate_json(prompt, system, use_reasoning=True)

class MedicalDeviceClassifier(AIServiceBase):
    def classify_device(self, description: str) -> Dict[str, str]:
        system = "You are a Regulatory Affairs Specialist. Classify medical devices (FDA/MDR). Return JSON."
        prompt = f"""
        Device Description: {description}
        
        Return JSON with keys: 
        'classification' (e.g., 'Class II / Class IIa'), 
        'rationale' (Why?), 
        'product_code' (FDA Product Code if applicable).
        """
        return self._generate_json(prompt, system, use_reasoning=True)

class MultiProviderAIService:
    def __init__(self, openai_key: str, gemini_key: str, model_overrides: Optional[Dict[str, Dict[str, str]]] = None):
        model_overrides = model_overrides or {}
        self.openai = AIService(openai_key, provider="openai", model_overrides=model_overrides.get("openai"))
        self.gemini = AIService(gemini_key, provider="gemini", model_overrides=model_overrides.get("gemini"))
        self.default_provider = "openai"

    def generate_dual_responses(self, prompt: str, system_instruction: str) -> Tuple[str, str]:
        concise = self.openai.generate_text_with_verbosity(prompt, system_instruction, "Pithy", use_reasoning=True)
        verbose = self.gemini.generate_text_with_verbosity(prompt, system_instruction, "Verbose", use_reasoning=True)
        return concise, verbose

    def _base(self) -> AIService:
        return self.openai if self.default_provider == "openai" else self.gemini

    def _generate_text(self, prompt: str, system_instruction: str = None, use_reasoning: bool = False) -> str:
        return self._base()._generate_text(prompt, system_instruction=system_instruction, use_reasoning=use_reasoning)

    def _generate_json(self, prompt: str, system_instruction: str = None, use_reasoning: bool = False) -> Dict[str, Any]:
        return self._base()._generate_json(prompt, system_instruction=system_instruction, use_reasoning=use_reasoning)

    def assess_relevance_json(self, my_context: str, record_text: str) -> Dict[str, str]:
        return self._base().assess_relevance_json(my_context, record_text)

    def generate_text_with_verbosity(
        self,
        prompt: str,
        system_instruction: str,
        verbosity: str,
        use_reasoning: bool = False,
    ) -> str:
        return self._base().generate_text_with_verbosity(
            prompt,
            system_instruction=system_instruction,
            verbosity=verbosity,
            use_reasoning=use_reasoning,
        )

# Singleton management for the main service
def get_ai_service():
    if 'ai_service' not in st.session_state:
        # Try to initialize if key is present
        provider = st.session_state.get("provider", "openai")
        model_overrides = st.session_state.get("model_overrides", {})
        if provider == "both":
            openai_key = st.session_state.get("openai_api_key")
            gemini_key = st.session_state.get("gemini_api_key")
            if openai_key and gemini_key:
                st.session_state.ai_service = MultiProviderAIService(openai_key, gemini_key, model_overrides=model_overrides)
            else:
                return None
        else:
            api_key = st.session_state.get('api_key')
            if api_key:
                st.session_state.ai_service = AIService(api_key, provider=provider, model_overrides=model_overrides.get(provider))
            else:
                return None
    return st.session_state.get('ai_service')
