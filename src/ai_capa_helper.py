# src/ai_capa_helper.py

import json
from typing import Dict, Optional, Any
import openai
from .utils import retry_with_backoff

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
                self.model = FINE_TUNED_MODEL
            except Exception as e:
                print(f"Failed to initialize AI helper: {e}")

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

# ... (AIEmailDrafter, MedicalDeviceClassifier, RiskAssessmentGenerator, UseRelatedRiskAnalyzer remain the same) ...

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
        try:
            response = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], max_tokens=2500, temperature=0.2, response_format={"type": "json_object"})
            return json.loads(response.choices[0].message.content)
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

# --- NEW/MODIFIED CLASS for Human Factors ---
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
        
        Return ONLY a valid JSON object with keys for each section: "conclusion_statement",
        "descriptions", "device_interface", "known_problems", "hazards_analysis", 
        "preliminary_analyses", "critical_tasks", and "validation_testing".
        """
        user_prompt = f"""
        **Product Name:** {product_name}
        **Product Description:** {product_desc}

        **User's Answers to Key Questions:**
        1. **User Profile & Environment:** {user_answers.get('user_profile')}
        2. **Critical Tasks:** {user_answers.get('critical_tasks')}
        3. **Potential Harms from Errors:** {user_answers.get('potential_harms')}

        Now, generate the full HFE report draft based on this information.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error generating HF report from answers: {e}")
            return {"error": f"Failed to generate HF report from answers: {e}"}
