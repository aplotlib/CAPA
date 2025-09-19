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

        prompt = f"""
        You are a quality assurance manager writing an email to a valued manufacturing partner, {vendor_name}.
        Your tone must be super reasonable, conservative, and collaborative, NOT demanding or accusatory.
        The goal is to start a productive conversation.

        **Email Goal:** {goal}

        **Data Context:**
        {context}

        **Recipient's English Ability:** {english_ability}/5

        Based on the goal, data, and the recipient's English ability, draft a professional email to {contact_name}.
        - Start with a polite opening.
        - Present the key data points clearly and concisely.
        - Frame the issue as a mutual challenge to overcome.
        - Ask for their perspective and suggestions for a joint investigation.
        - Do not suggest stopping production or assign blame.
        - End with a collaborative closing statement.
        - If the English ability is low, use simpler language and shorter sentences.

        Return only the full email text.
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
    """Classifies medical devices based on FDA regulations."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize Medical Device Classifier: {e}")

    def classify_device(self, device_description: str) -> Dict[str, str]:
        """Classifies a medical device based on a description."""
        if not self.client:
            return {"error": "AI client not initialized."}

        prompt = f"""
        You are an expert in FDA medical device classification.
        Based on the following device description, classify the device and provide a rationale.

        **Device Description:**
        {device_description}

        Return a JSON object with the following keys:
        - "classification": The FDA class (Class I, Class II, or Class III).
        - "rationale": A detailed explanation for the classification.
        - "risks": The primary risks associated with the device.
        - "regulatory_requirements": The regulatory requirements for this class of device.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return json.loads(response)
        except Exception as e:
            print(f"Error classifying device: {e}")
            return {"error": "Failed to classify the device."}
