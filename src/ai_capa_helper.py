# src/ai_capa_helper.py

import json
from typing import Dict, Optional
import anthropic

class AICAPAHelper:
    """AI assistant for generating CAPA form suggestions."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Anthropic API key."""
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize AI helper: {e}")

    def generate_capa_suggestions(self,
                                issue_summary: str,
                                analysis_results: Dict) -> Dict[str, str]:
        """Generate AI suggestions for CAPA form fields."""
        if not self.client: return {}

        summary = analysis_results.get('return_summary', {}).iloc[0] if not analysis_results.get('return_summary', {}).empty else {}
        context = f"""
        Issue Summary: {issue_summary}
        SKU: {summary.get('sku', 'N/A')}
        Return Rate: {summary.get('return_rate', 0):.2f}%
        Total Returns: {int(summary.get('total_returned', 0))}
        """

        prompt = f"""
        You are a medical device quality expert helping to complete a CAPA form based on the following context:
        {context}

        Generate content for each CAPA field following ISO 13485 standards.
        Return ONLY a valid JSON object with keys: "issue_description", "root_cause", "corrective_action", "preventive_action".
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return json.loads(response)
        except Exception as e:
            print(f"Error generating CAPA suggestions: {e}")
            return {}

class AIEmailDrafter:
    """AI assistant for drafting vendor communications."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize AI Email Drafter: {e}")

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
        
        # Tailor the instructions based on English ability
        if english_ability <= 2:
            language_instruction = "IMPORTANT: The recipient has limited English proficiency. Use very simple words, short sentences, and basic grammar. Avoid jargon, idioms, and complex phrasing. The goal is clarity for easy translation."
        elif english_ability == 3:
            language_instruction = "Use clear and professional language, but avoid overly complex terminology."
        else:
            language_instruction = "Use standard professional business English."


        prompt = f"""
        You are a quality assurance manager writing an email to a valued manufacturing partner, {vendor_name}.
        Your tone must be super reasonable, conservative, and collaborative, NOT demanding or accusatory.
        The goal is to start a productive, data-driven conversation to solve a problem together.

        **Email Goal:** {goal}

        **Data Context:**
        {context}

        **Recipient's English Ability:** {english_ability}/5. {language_instruction}

        Based on all the above, draft a professional email to {contact_name}.
        - Start with a polite and friendly opening.
        - Present the key data points clearly and concisely.
        - Frame the issue as a mutual challenge to overcome for mutual benefit.
        - Explicitly ask for their perspective and suggestions for a joint investigation.
        - Do not suggest stopping production, assigning blame, or demanding specific actions.
        - End with a collaborative closing statement that reinforces the partnership.

        Return only the full email text, ready to be sent.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return response
        except Exception as e:
            print(f"Error drafting vendor email: {e}")
            return f"An error occurred while drafting the email: {e}"

class MedicalDeviceClassifier:
    """Classifies medical devices based on FDA regulations using an AI model."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize Medical Device Classifier: {e}")

    def classify_device(self, device_description: str) -> Dict[str, str]:
        """
        Classifies a medical device based on its description, providing rationale,
        risks, and regulatory requirements.
        """
        if not self.client:
            return {"error": "AI client is not initialized. Please check API key configuration."}

        prompt = f"""
        You are an expert consultant specializing in U.S. FDA medical device classification.
        Your task is to analyze the provided device description and determine its classification
        with a high degree of accuracy, referencing 21 CFR parts 862-892.

        **Device Description:**
        {device_description}

        Based on the description, provide a detailed analysis. Return a single, valid JSON object with the following exact keys:
        - "classification": The most likely FDA class (e.g., "Class I", "Class II", "Class III"). State if it is exempt from 510(k) if applicable.
        - "rationale": A detailed, step-by-step explanation for the classification. Reference the relevant regulation number (e.g., 21 CFR 880.2910 for a thermometer) and explain why the device fits this classification based on its intended use and level of risk.
        - "risks": A bulleted list of the primary risks to the patient or user associated with this type of device.
        - "regulatory_requirements": A bulleted list of the general regulatory controls required for this device class (e.g., General Controls, Special Controls, Premarket Approval (PMA)).

        Example of a good rationale: "The device is classified as Class II under 21 CFR 880.2910 (Clinical electronic thermometer). This is because it is intended for measuring body temperature, and its accuracy is crucial for medical diagnosis, posing a moderate risk. It requires adherence to special controls, such as performance standards, to ensure accuracy and safety."

        Return ONLY the valid JSON object.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                temperature=0.2, # Lower temperature for higher accuracy and consistency
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            
            # Find the JSON block in the response
            json_match = response[response.find('{'):response.rfind('}')+1]
            return json.loads(json_match)
        except Exception as e:
            print(f"Error classifying device: {e}")
            return {"error": f"Failed to classify the device due to an AI model error: {e}"}

class RiskAssessmentGenerator:
    """Generates risk assessments based on ISO 14971 and IEC 62366 standards."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize Risk Assessment Generator: {e}")

    def generate_assessment(self, product_name: str, sku: str, product_description: str, assessment_type: str) -> str:
        """Generates a risk assessment report using an AI model."""
        if not self.client:
            return "Error: AI client for Risk Assessment is not initialized. Please check API key."

        prompt = f"""
        You are a certified risk management expert specializing in medical devices, compliant with ISO 14971 and IEC 62366.
        Your task is to generate a formal risk assessment report based on the provided product information.

        **Product Information:**
        - **Product Name:** {product_name}
        - **SKU:** {sku}
        - **Product Description & Intended Use:** {product_description}
        - **Assessment Standard(s):** {assessment_type}

        **Instructions:**
        1.  Generate a comprehensive risk assessment structured as a Markdown table.
        2.  The table columns should be: `Hazard`, `Foreseeable Sequence of Events`, `Hazardous Situation`, `Potential Harm`, `Severity (S)`, `Probability (P)`, `Risk Level`, and `Proposed Mitigation`.
        3.  Identify at least 5-7 relevant risks based on the product description.
        4.  For `Severity` and `Probability`, use a 1-5 scale (1=Low, 5=High).
        5.  Determine `Risk Level` (Low, Medium, High) based on S and P.
        6.  Propose a concrete `Proposed Mitigation` for each identified risk.
        7.  Start the report with a brief summary header.

        **Example Row:**
        | Hazard | Foreseeable Sequence of Events | Hazardous Situation | Potential Harm | Severity (S) | Probability (P) | Risk Level | Proposed Mitigation |
        |---|---|---|---|---|---|---|---|
        | Inaccurate Temperature Reading | Device provides a lower-than-actual temperature reading for a febrile infant. | Parent fails to seek medical attention due to false normal reading. | Delayed diagnosis of a serious illness (e.g., sepsis). | 5 | 2 | Medium | Implement redundant sensors and self-calibration checks upon device startup. |

        Generate the full report now.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return response
        except Exception as e:
            print(f"Error generating risk assessment: {e}")
            return f"An error occurred while generating the risk assessment: {e}"

class UseRelatedRiskAnalyzer:
    """Generates a Use-Related Risk Analysis (URRA) based on IEC 62366."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize Use-Related Risk Analyzer: {e}")

    def generate_urra(self, product_name: str, product_description: str, intended_user: str, use_environment: str) -> str:
        """Generates a URRA report using an AI model."""
        if not self.client:
            return "Error: AI client for Use-Related Risk Analysis is not initialized. Please check API key."

        prompt = f"""
        You are a human factors engineering expert specializing in medical device usability under IEC 62366.
        Generate a formal Use-Related Risk Analysis (URRA) based on the provided product details.

        **Product Information:**
        - **Product Name:** {product_name}
        - **Product Description & Intended Use:** {product_description}
        - **Intended User Profile:** {intended_user}
        - **Intended Use Environment:** {use_environment}

        **Instructions:**
        1.  Create a URRA in a Markdown table format.
        2.  The table columns should be: `Use Task`, `Potential Use Error`, `Foreseeable Consequences`, `Potential Harm`, `Severity (S)`, `Probability (P)`, `Risk Level`, and `Proposed Mitigation/Design Recommendation`.
        3.  Identify 5-7 critical or frequent use tasks associated with the device.
        4.  For each task, brainstorm potential use errors.
        5.  Analyze the consequences and potential harm of each error.
        6.  Assign `Severity` and `Probability` on a 1-5 scale.
        7.  Determine the `Risk Level`.
        8.  Provide actionable design recommendations or mitigations to prevent the use error.
        9.  Begin with a summary header for the report.

        **Example Row:**
        | Use Task | Potential Use Error | Foreseeable Consequences | Potential Harm | Severity (S) | Probability (P) | Risk Level | Proposed Mitigation/Design Recommendation |
        |---|---|---|---|---|---|---|---|
        | Turning on the device | User fails to press the power button long enough to activate the device. | User believes the device is broken or battery is dead, leading to non-use. | Failure to monitor temperature. | 4 | 3 | Medium | Provide clear visual (e.g., screen lights up) and haptic (e.g., vibration) feedback upon successful power-on. |

        Generate the full URRA report now.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return response
        except Exception as e:
            print(f"Error generating URRA: {e}")
            return f"An error occurred while generating the URRA report: {e}"
