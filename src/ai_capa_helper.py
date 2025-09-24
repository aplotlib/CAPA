# src/ai_capa_helper.py

import json
from typing import Dict, Optional
import openai
from .utils import retry_with_backoff

class AICAPAHelper:
    """AI assistant for generating CAPA form suggestions using OpenAI."""

    def __init__(self, api_key: Optional[str] = None): #<-- FIX: api_key parameter was missing
        """Initialize with OpenAI API key."""
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
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
        Return ONLY a valid JSON object with keys for the most critical fields: "issue_description", "root_cause_analysis", "corrective_action", "preventive_action", and "effectiveness_verification_plan".
        """
        user_prompt = f"Here is the context for the CAPA form:\n{context}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error generating CAPA suggestions: {e}")
            return {}

class AIEmailDrafter:
    """AI assistant for drafting vendor communications using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize AI Email Drafter: {e}")

    @retry_with_backoff()
    def draft_vendor_email(self, goal: str, analysis_results: Dict, sku: str,
                           vendor_name: str, contact_name: str, english_ability: int) -> str:
        """Drafts a conservative and collaborative email to a vendor."""
        if not self.client:
            return "AI client not initialized. Please configure the API key."

        summary = analysis_results.get('return_summary', {}).iloc[0] if not analysis_results.get('return_summary', {}).empty else {}
        context = f"""
        - Product SKU: {sku}
        - Recent Return Rate: {summary.get('return_rate', 0):.2f}%
        - Total Units Sold (period): {int(summary.get('total_sold', 0))}
        - Total Units Returned (period): {int(summary.get('total_returned', 0))}
        - AI Insights: {analysis_results.get('insights', 'N/A')}
        """
        
        if english_ability <= 2:
            language_instruction = "IMPORTANT: The recipient has limited English proficiency. Use very simple words, short sentences, and basic grammar. Avoid jargon, idioms, and complex phrasing."
        elif english_ability == 3:
            language_instruction = "Use clear and professional language, but avoid overly complex terminology."
        else:
            language_instruction = "Use standard professional business English."

        system_prompt = f"""
        You are a quality assurance manager writing an email to a valued manufacturing partner, {vendor_name}.
        Your tone must be super reasonable, conservative, and collaborative, NOT demanding or accusatory.
        The goal is to start a productive, data-driven conversation to solve a problem together.
        Recipient's English Ability: {english_ability}/5. {language_instruction}
        Draft a professional email to {contact_name}.
        - Start politely.
        - Present key data concisely.
        - Frame the issue as a mutual challenge.
        - Ask for their perspective and suggestions for a joint investigation.
        - Do not assign blame or demand specific actions.
        - End with a collaborative closing statement.
        Return only the full email text.
        """
        user_prompt = f"**Email Goal:** {goal}\n\n**Data Context:**\n{context}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error drafting vendor email: {e}")
            return f"An error occurred while drafting the email: {e}"

class MedicalDeviceClassifier:
    """Classifies medical devices based on FDA regulations using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize Medical Device Classifier: {e}")

    @retry_with_backoff()
    def classify_device(self, device_description: str) -> Dict[str, str]:
        """Classifies a medical device, providing rationale, risks, and requirements."""
        if not self.client:
            return {"error": "AI client is not initialized."}

        system_prompt = """
        You are an expert consultant specializing in U.S. FDA medical device classification.
        Analyze the device description and determine its classification, referencing 21 CFR parts 862-892.
        Return a single, valid JSON object with the following exact keys:
        - "classification": The most likely FDA class (e.g., "Class I", "Class II"). State if exempt from 510(k).
        - "rationale": A detailed explanation for the classification, referencing the relevant regulation number (e.g., 21 CFR 880.2910).
        - "risks": A bulleted list of the primary risks to the patient or user.
        - "regulatory_requirements": A bulleted list of general regulatory controls required (e.g., General Controls, Special Controls).
        Return ONLY the valid JSON object.
        """
        user_prompt = f"**Device Description:**\n{device_description}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2500,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error classifying device: {e}")
            return {"error": f"Failed to classify the device due to an AI model error: {e}"}

class RiskAssessmentGenerator:
    """Generates risk assessments based on ISO 14971 using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize Risk Assessment Generator: {e}")

    @retry_with_backoff()
    def generate_assessment(self, product_name: str, sku: str, product_description: str, assessment_type: str) -> str:
        """Generates a risk assessment report."""
        if not self.client:
            return "Error: AI client for Risk Assessment is not initialized."

        system_prompt = """
        You are a certified risk management expert for medical devices (ISO 14971).
        Generate a formal risk assessment as a Markdown table.
        Columns: `Hazard`, `Foreseeable Sequence of Events`, `Hazardous Situation`, `Potential Harm`, `Severity (S)`, `Probability (P)`, `Risk Level`, and `Proposed Mitigation`.
        - Identify at least 5-7 relevant risks.
        - Use a 1-5 scale for Severity and Probability.
        - Determine Risk Level (Low, Medium, High).
        - Propose a concrete Mitigation for each risk.
        """
        user_prompt = f"""
        **Product Information:**
        - **Product Name:** {product_name}
        - **SKU:** {sku}
        - **Product Description & Intended Use:** {product_description}
        - **Assessment Standard(s):** {assessment_type}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3000,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating risk assessment: {e}")
            return f"An error occurred while generating the risk assessment: {e}"

class UseRelatedRiskAnalyzer:
    """Generates a Use-Related Risk Analysis (URRA) based on IEC 62366 using OpenAI."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize Use-Related Risk Analyzer: {e}")
    
    @retry_with_backoff()
    def generate_urra(self, product_name: str, product_description: str, intended_user: str, use_environment: str) -> str:
        """Generates a URRA report."""
        if not self.client:
            return "Error: AI client for Use-Related Risk Analysis is not initialized."

        system_prompt = """
        You are a human factors engineering expert (IEC 62366).
        Generate a formal Use-Related Risk Analysis (URRA) in a Markdown table.
        Columns: `Use Task`, `Potential Use Error`, `Foreseeable Consequences`, `Potential Harm`, `Severity (S)`, `Probability (P)`, `Risk Level`, and `Proposed Mitigation/Design Recommendation`.
        - Identify 5-7 critical use tasks.
        - For each, brainstorm use errors and consequences.
        - Assign Severity and Probability (1-5) and determine Risk Level.
        - Provide actionable design recommendations to mitigate the error.
        """
        user_prompt = f"""
        **Product Information:**
        - **Product Name:** {product_name}
        - **Product Description & Intended Use:** {product_description}
        - **Intended User Profile:** {intended_user}
        - **Intended Use Environment:** {use_environment}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=3000,
                temperature=0.4
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating URRA: {e}")
            return f"An error occurred while generating the URRA report: {e}"
