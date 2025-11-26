# src/ai_capa_helper.py

import json
import re
from typing import Dict, Optional, Any
import openai
from io import BytesIO
from utils import retry_with_backoff, parse_ai_json_response

# Define the new model name as a constant
FINE_TUNED_MODEL = "ft:gpt-4o-2024-08-06:vive-health-quality-department:qms-v2-stable-lr:CM1nuhta"

class AICAPAHelper:
    """AI assistant for generating CAPA form suggestions using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o" 
            except Exception as e:
                print(f"Failed to initialize AI helper: {e}")

    @retry_with_backoff()
    def transcribe_audio(self, audio_file) -> str:
        """
        Transcribes audio input using OpenAI's Whisper model.
        Expects a file-like object from st.audio_input.
        """
        if not self.client:
            return "Error: AI client not initialized."
        
        try:
            # st.audio_input returns a BytesIO object. We need to give it a name attribute
            # so the OpenAI library knows what format it is (e.g., .wav).
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
        Takes rough user notes for a specific CAPA field and refines them into
        professional, regulatory-compliant language (FDA/ISO).
        """
        if not self.client: return "AI client not initialized."
        if not rough_input or len(rough_input) < 3: return rough_input

        system_prompt = f"""
        You are a Quality Assurance Regulatory Expert for Medical Devices (ISO 13485 / 21 CFR 820).
        Your task is to rewrite the user's rough notes for the CAPA field: "{field_name}".
        
        **Guiding Principles (from '15 Steps to Risk-Based CAPA'):**
        1. **Risk-Based:** Ensure the language reflects the appropriate level of urgency and severity.
        2. **Fact-Based:** Focus on objective evidence (Man, Machine, Material, Method, Environment).
        3. **Auditor-Ready:** Use professional, precise technical writing (active voice).
        
        Do NOT invent facts. Refine only the provided input.
        """
        
        user_prompt = f"""
        **Product Context:** {product_context}
        **Rough Input:** {rough_input}
        
        **Refined Output:**
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
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
        """Generate AI suggestions for CAPA form fields."""
        if not self.client: return {}

        summary = analysis_results.get('return_summary', {}).iloc[0] if not analysis_results.get('return_summary', {}).empty else {}
        context = f"""
        Issue Summary: {issue_summary}
        SKU: {summary.get('sku', 'N/A')}
        Return Rate: {summary.get('return_rate', 0):.2f}%
        Total Returns: {int(summary.get('total_returned', 0))}
        """

        system_prompt = """
        You are a medical device quality expert helping to complete a CAPA form based on the provided context.
        Generate content for each CAPA field following ISO 13485, FDA 21 CFR 820.100, and EU MDR standards.
        Return ONLY a valid JSON object with keys for all relevant fields: "issue_description", "root_cause", "corrective_action", "preventive_action", and "effectiveness_verification_plan".
        """
        user_prompt = f"Here is the context for the CAPA form:\n{context}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error generating CAPA suggestions: {e}")
            return {"error": f"Failed to generate CAPA suggestions: {e}"}


class AIEmailDrafter:
    """AI assistant for drafting vendor communications using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = FINE_TUNED_MODEL
            except Exception as e:
                print(f"Failed to initialize AI Email Drafter: {e}")

    @retry_with_backoff()
    def draft_vendor_email(self, goal: str, analysis_results: Dict, sku: str,
                           vendor_name: str, contact_name: str, english_ability: int) -> str:
        if not self.client: return "AI client not initialized."
        summary = analysis_results.get('return_summary', {}).iloc[0] if not analysis_results.get('return_summary', {}).empty else {}
        context = f"""- Product SKU: {sku}\n- Recent Return Rate: {summary.get('return_rate', 0):.2f}%\n- AI Insights: {analysis_results.get('insights', 'N/A')}"""
        if english_ability <= 2: language_instruction = "IMPORTANT: Use very simple words, short sentences, and basic grammar."
        else: language_instruction = "Use standard professional business English."
        system_prompt = f"""You are a quality manager writing a collaborative email to a manufacturing partner, {vendor_name}. Tone must be reasonable, not accusatory. Goal: Start a productive, data-driven conversation. Recipient's English Ability: {english_ability}/5. {language_instruction} Draft a professional email to {contact_name}. Propose 1-2 realistic KPIs and a reasonable timeline (e.g., "initial analysis within 15 days"). Return only the full email text."""
        user_prompt = f"**Email Goal:** {goal}\n\n**Data Context:**\n{context}"
        try:
            response = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], max_tokens=2000)
            return response.choices[0].message.content
        except Exception as e: return f"An error occurred: {e}"

class MedicalDeviceClassifier:
    """Classifies medical devices based on FDA regulations using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try: self.client = openai.OpenAI(api_key=api_key); self.model = FINE_TUNED_MODEL
            except Exception as e: print(f"Failed to initialize Medical Device Classifier: {e}")

    @retry_with_backoff()
    def classify_device(self, device_description: str) -> Dict[str, str]:
        if not self.client: return {"error": "AI client is not initialized."}
        system_prompt = """You are an expert in U.S. FDA medical device classification (21 CFR 862-892). Analyze the device description. Return a single, valid JSON object with keys: "classification", "rationale" (citing regulation number), "risks" (bulleted list), and "regulatory_requirements" (bulleted list). Return ONLY the valid JSON object."""
        user_prompt = f"**Device Description:**\n{device_description}"
        raw_content = ""
        try:
            response = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], max_tokens=2500, temperature=0.2, response_format={"type": "json_object"})
            raw_content = response.choices[0].message.content
            return parse_ai_json_response(raw_content)
        except json.JSONDecodeError:
            return {"error": "AI response did not contain a valid JSON object."}
        except Exception as e: return {"error": f"Failed to classify the device due to an AI model error: {e}"}

class RiskAssessmentGenerator:
    """Generates risk assessments based on ISO 14971 using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try: self.client = openai.OpenAI(api_key=api_key); self.model = FINE_TUNED_MODEL
            except Exception as e: print(f"Failed to initialize Risk Assessment Generator: {e}")

    @retry_with_backoff()
    def generate_assessment(self, product_name: str, sku: str, product_description: str) -> str:
        if not self.client: return "Error: AI client for Risk Assessment is not initialized."
        system_prompt = "You are a certified risk management expert (ISO 14971). Generate a formal risk assessment as a Markdown table. Columns: `Hazard`, `Foreseeable Sequence of Events`, `Hazardous Situation`, `Potential Harm`, `Severity (S)`, `Probability (P)`, `Risk Level`, and `Proposed Mitigation`. Identify 5-7 risks. Use a 1-5 scale for S and P. Determine Risk Level. Propose concrete mitigations."
        user_prompt = f"**Product:** {product_name} (SKU: {sku})\n**Description:** {product_description}"
        try:
            response = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], max_tokens=3000, temperature=0.3)
            return response.choices[0].message.content
        except Exception as e: return f"An error occurred: {e}"

class UseRelatedRiskAnalyzer:
    """Generates a Use-Related Risk Analysis (URRA) based on IEC 62366 using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try: self.client = openai.OpenAI(api_key=api_key); self.model = FINE_TUNED_MODEL
            except Exception as e: print(f"Failed to initialize Use-Related Risk Analyzer: {e}")
    
    @retry_with_backoff()
    def generate_urra(self, product_name: str, product_description: str, intended_user: str, use_environment: str) -> str:
        if not self.client: return "Error: AI client for URRA is not initialized."
        system_prompt = "You are a human factors engineering expert (IEC 62366). Generate a formal Use-Related Risk Analysis (URRA) in a Markdown table. Columns: `Use Task`, `Potential Use Error`, `Foreseeable Consequences`, `Potential Harm`, `Severity (S)`, `Probability (P)`, `Risk Level`, `Proposed Mitigation/Design Recommendation`. Identify 5-7 critical use tasks. Brainstorm errors, consequences. Assign S & P (1-5), determine Risk Level, and provide actionable design recommendations."
        user_prompt = f"**Product:** {product_name}\n**Description:** {product_description}\n**User:** {intended_user}\n**Environment:** {use_environment}"
        try:
            response = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], max_tokens=3000, temperature=0.4)
            return response.choices[0].message.content
        except Exception as e: return f"An error occurred: {e}"

class AIHumanFactorsHelper:
    """AI assistant for generating Human Factors report content."""
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = FINE_TUNED_MODEL
            except Exception as e:
                print(f"Failed to initialize AIHumanFactorsHelper: {e}")

    @retry_with_backoff()
    def generate_hf_report_from_answers(self, product_name: str, product_desc: str, user_answers: Dict[str, str]) -> Dict[str, str]:
        """Generates a full HFE report draft from answers to broad questions."""
        if not self.client:
            return {"error": "AI client is not initialized."}
        
        system_prompt = """
        You are a Human Factors Engineering (HFE) expert drafting a report that aligns with FDA guidance.
        A user has provided high-level answers to key questions. Your task is to expand these answers into a comprehensive, professionally worded draft for all sections of an HFE report.
        Extrapolate from the user's answers, product name, and description to create detailed, plausible content for each section.
        
        IMPORTANT: Your final output must be a single, valid, and complete JSON object. Ensure that all property names and string values are enclosed in double quotes. Do not include any text or formatting outside of the main JSON object.
        The JSON object must have keys for each section: "conclusion_statement",
        "descriptions", "device_interface", "known_problems", "hazards_analysis", 
        "preliminary_analyses", "critical_tasks", and "validation_testing". Ensure the JSON is not truncated.
        """
        user_prompt = f"""
        **Product Name:** {product_name}
        **Product Description:** {product_desc}

        **User's Answers to Key Questions:**
        1. **User Profile & Environment:** {user_answers.get('user_profile')}
        2. **Critical Tasks:** {user_answers.get('critical_tasks')}
        3. **Potential Harms from Errors:** {user_answers.get('potential_harms')}

        Now, generate the full HFE report draft.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=4095,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content
            return parse_ai_json_response(raw_content)
        except json.JSONDecodeError as e:
            return {"error": f"AI response was invalid or incomplete: {e}"}
        except Exception as e:
            print(f"Error generating HF report from answers: {e}")
            return {"error": f"Failed to generate HF report from answers: {e}"}

class AIDesignControlsTriager:
    """AI assistant for determining the need for design controls and generating them."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize AIDesignControlsTriager: {e}")

    @retry_with_backoff()
    def triage_device(self, device_description: str) -> Dict[str, str]:
        """Analyzes a device description to recommend if design controls are needed."""
        if not self.client:
            return {"error": "AI client is not initialized."}

        system_prompt = """
        You are an FDA compliance expert specializing in 21 CFR 820.30 (Design Controls).
        Your task is to analyze a product description and determine if design controls are legally required, recommended as a best practice, or not required.

        - **Legally Required**: All Class II and Class III devices. Also, specific Class I devices listed in the regulation (tracheobronchial suction catheters, surgeon's gloves, protective restraints, devices with computer software, manual radionuclide applicator systems, radionuclide teletherapy sources).
        - **Recommended**: Most other Class I devices or products with moderate risk where formal controls would significantly improve safety and effectiveness, even if not strictly mandated.
        - **Not Required**: Very low-risk consumer goods that are not considered medical devices.

        Analyze the user's description and provide a clear recommendation.
        Return ONLY a valid JSON object with three keys: "recommendation" (one of "Design Controls Legally Required", "Design Controls Recommended", "Design Controls Not Required"), "rationale" (a clear, concise explanation for your decision, citing the device class if applicable), and "next_steps" (suggested next actions for the user).
        """
        user_prompt = f"**Product Description:**\n{device_description}"

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
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error in design controls triage: {e}")
            return {"error": f"Failed to generate triage recommendation: {e}"}

    @retry_with_backoff()
    def generate_design_controls(self, product_name: str, product_ifu: str, user_needs: str, tech_reqs: str, risks: str) -> Dict[str, str]:
        """Generates a full design controls document draft from user answers."""
        if not self.client:
            return {"error": "AI client is not initialized."}

        system_prompt = """
        You are a Senior R&D Engineer and Regulatory Affairs Specialist, an expert in FDA 21 CFR 820.30 and ISO 13485.
        Your task is to draft a comprehensive Design Controls document for a new medical device based on high-level user inputs.
        Structure your output as a single, valid JSON object. For each key, provide detailed, professional content formatted with Markdown.

        The JSON object must contain these exact keys: "inputs", "outputs", "verification", "validation", "plan", "transfer", "dhf", and "traceability_matrix".

        For the "traceability_matrix", generate a Markdown table that links User Needs to Design Inputs, Outputs, Verification, and Validation activities.
        Example Traceability Matrix Row:
        | User Need | Design Input | Design Output | Verification | Validation |
        |---|---|---|---|---|
        | Patient needs to track ROM at home | The device shall measure knee flexion with +/- 1 degree accuracy | Firmware implements a Kalman filter for the 9-axis IMU | Protocol VT-001: Bench test confirms accuracy against a goniometer | Protocol VL-002: Usability study with 15 post-op patients confirms they can track ROM |
        
        Generate professional, plausible content for all sections.
        """
        user_prompt = f"""
        **Product Name:** {product_name}
        **Product Intended For Use:** {product_ifu}

        **User's High-Level Answers:**
        1. **Core User Needs:** {user_needs}
        2. **Key Technical Requirements:** {tech_reqs}
        3. **Significant Known Risks:** {risks}

        Now, generate the full Design Controls document draft.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return {"error": "AI returned incomplete or invalid JSON. Please try again."}
        except Exception as e:
            print(f"Error generating design controls draft: {e}")
            return {"error": f"Failed to generate design controls draft: {e}"}

class ProductManualWriter:
    """AI assistant for generating a product user manual."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize ProductManualWriter: {e}")

    @retry_with_backoff()
    def generate_manual_section(self, section_title: str, product_name: str, product_ifu: str, user_inputs: Dict, target_language: str = "English") -> str:
        """Generates a specific section of the user manual."""
        if not self.client:
            return "AI client is not initialized."

        system_prompt = f"""
        You are an expert technical writer creating a user manual for the medical device '{product_name}'.
        Your task is to write the '{section_title}' section of the manual.
        The manual should be clear, concise, and easy for a layperson to understand, adhering to medical device documentation standards.
        The target language for the output is {target_language}.
        Use Markdown for formatting (e.g., headings, bullet points, bold text).
        """
        user_prompt = f"""
        **Product Name:** {product_name}
        **Intended For Use:** {product_ifu}

        **User-Provided Information:**
        - **Key Features:** {user_inputs.get('features', 'Not provided.')}
        - **Step-by-Step Instructions:** {user_inputs.get('instructions', 'Not provided.')}
        - **Safety Warnings:** {user_inputs.get('warnings', 'Not provided.')}

        Please write the content for the '{section_title}' section now.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=3000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating manual section '{section_title}': {e}")
            return f"Failed to generate section: {e}"
            
class AIProjectCharterHelper:
    """
    AI assistant for drafting a project charter.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize AIProjectCharterHelper: {e}")

    @retry_with_backoff()
    def generate_charter_draft(self, product_name: str, problem: str, user: str) -> Dict[str, Any]:
        """Generates a draft of a project charter from a few key inputs."""
        if not self.client: return {"error": "AI client not initialized."}
        
        system_prompt = """
        You are a senior project manager and regulatory affairs expert specializing in medical devices.
        A user has provided initial information for a new product. Your task is to expand this into a formal project charter draft.
        - Extrapolate a plausible "Project Goal" from the problem statement.
        - Define a reasonable "Project Scope".
        - Suggest a likely FDA "Device Classification" (Class I, Class II, or Class III) based on the description.
        - Propose a list of "Applicable Standards & Regulations" based on the classification.
        - Suggest key "Stakeholders".
        Return ONLY a single, valid JSON object with these exact keys: "problem_statement", "project_goal", "scope", "device_classification", "applicable_standards" (as a list of strings), and "stakeholders".
        """
        user_prompt = f"""
        **Product Name:** {product_name}
        **Problem it Solves:** {problem}
        **Target User:** {user}
        
        Now, generate the complete project charter draft as a JSON object.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content
            return parse_ai_json_response(raw_content)
        except Exception as e:
            return {"error": f"Failed to generate project charter draft: {e}"}
