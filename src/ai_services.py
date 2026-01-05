import streamlit as st
from google import genai
from google.genai import types
from typing import Optional, Dict, Any, List
import json
import logging

# Setup Logger
logger = logging.getLogger(__name__)

class AIServiceBase:
    """Base class for all AI Services using Google GenAI SDK."""
    def __init__(self, api_key: str):
        if not api_key:
            # Don't crash immediately, allow graceful degradation
            self.client = None
            logger.warning("AIService initialized without API Key.")
            return

        try:
            self.client = genai.Client(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize GenAI Client: {e}")
            self.client = None
            
        # Model Configuration
        self.fast_model = "gemini-2.0-flash-exp" 
        self.reasoning_model = "gemini-2.0-flash-thinking-exp"

    def _generate_json(self, prompt: str, system_instruction: str = None) -> Dict[str, Any]:
        """Helper to generate JSON responses safely."""
        if not self.client:
            return {"error": "AI Client not initialized (Missing API Key)."}

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
                response_mime_type="application/json"
            )
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=prompt,
                config=config
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"AI Generation Error: {e}")
            return {"error": str(e)}

    def _generate_text(self, prompt: str, system_instruction: str = None) -> str:
        """Helper to generate text responses."""
        if not self.client:
            return "Error: AI Client not initialized (Missing API Key)."

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4
            )
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            logger.error(f"AI Text Generation Error: {e}")
            return f"Error: {str(e)}"

# --- Specialized Services ---

class AIService(AIServiceBase):
    def analyze_text(self, prompt: str, system_instruction: str = None) -> str:
        return self._generate_text(prompt, system_instruction)

    def transcribe_and_structure(self, audio_bytes: bytes, context: str = "") -> Dict[str, str]:
        if not self.client:
             return {"error": "AI Client not initialized."}

        prompt_text = f"""
        You are a Quality Assurance Assistant. 
        Listen to this dictation regarding a potential Quality Event or CAPA.
        CONTEXT: {context}
        TASK:
        1. Transcribe the audio accurately.
        2. Extract fields: Issue Description, Root Cause, Immediate Actions.
        """
        try:
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                    prompt_text
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            return {"error": str(e)}

    def analyze_meeting_transcript(self, transcript_text: str) -> Dict[str, str]:
        system_prompt = "You are a QA Expert. Extract CAPA details (issue, root cause, actions) from notes."
        user_prompt = f"Analyze this transcript:\n{transcript_text}"
        return self._generate_json(user_prompt, system_prompt)

    def screen_recalls(self, product_description: str) -> str:
        system = "You are a Regulatory Expert. Screen device against FDA/MDR recall databases."
        user = f"Screen this device: {product_description}. List common recall reasons and keywords."
        return self._generate_text(user, system)

class DesignControlsTriager(AIServiceBase):
    def generate_design_controls(self, name: str, ifu: str, user_needs: str, tech_reqs: str, risks: str) -> Dict[str, str]:
        system = "You are a Medical Device Systems Engineer (ISO 13485). Generate Design Control documentation."
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
        return self._generate_json(prompt, system)

class UrraGenerator(AIServiceBase):
    def generate_urra(self, product_name: str, product_desc: str, user: str, environment: str) -> Dict[str, Any]:
        system = "You are a Usability Engineer (IEC 62366). Generate a Use-Related Risk Analysis (URRA)."
        prompt = f"""
        Device: {product_name}
        Context: {product_desc}
        User: {user}
        Env: {environment}
        
        Generate a list of 5-7 critical usability risks.
        Return JSON with key 'urra_rows' containing a list of objects with keys:
        'Task', 'Hazard', 'Severity' (1-5), 'Probability' (1-5), 'Risk Level' (Low/Med/High), 'Mitigation'.
        """
        return self._generate_json(prompt, system)

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
        system = "You are a Project Manager in MedTech. Draft a Project Charter."
        prompt = f"""
        Project: {product_name}
        Problem: {problem_statement}
        User: {target_user}
        
        Return JSON with keys: 'project_goal', 'scope', 'device_classification', 'applicable_standards' (list), 'stakeholders'.
        """
        return self._generate_json(prompt, system)

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
        system = "You are a Human Factors Engineer (IEC 62366). Draft an HFE Report."
        prompt = f"""
        Device: {name}
        User Profile: {answers.get('user_profile')}
        Critical Tasks: {answers.get('critical_tasks')}
        Harms: {answers.get('potential_harms')}
        
        Return JSON with keys: 'conclusion_statement', 'descriptions', 'device_interface', 'known_problems', 'hazards_analysis', 'preliminary_analyses', 'critical_tasks', 'validation_testing'.
        """
        return self._generate_json(prompt, system)

class MedicalDeviceClassifier(AIServiceBase):
    def classify_device(self, description: str) -> Dict[str, str]:
        system = "You are a Regulatory Affairs Specialist. Classify medical devices (FDA/MDR)."
        prompt = f"""
        Device Description: {description}
        
        Return JSON with keys: 
        'classification' (e.g., 'Class II / Class IIa'), 
        'rationale' (Why?), 
        'product_code' (FDA Product Code if applicable).
        """
        return self._generate_json(prompt, system)

# Singleton management for the main service
def get_ai_service():
    if 'ai_service' not in st.session_state:
        # Try to initialize if key is present
        api_key = st.session_state.get('api_key')
        if api_key:
            st.session_state.ai_service = AIService(api_key)
        else:
            return None
    return st.session_state.get('ai_service')
