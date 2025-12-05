import openai
import json
import pandas as pd
from src.utils import retry_with_backoff

class BaseAIProcessor:
    def __init__(self, api_key, model="gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key) if api_key else None
        self.model = model

class DesignControlsTriager(BaseAIProcessor):
    @retry_with_backoff()
    def generate_design_controls(self, product_name, ifu, needs, reqs, risks):
        if not self.client: return {"error": "API Key missing"}
        prompt = f"""
        Generate a Design Control draft (ISO 13485) for '{product_name}'.
        Context: {ifu}
        User Needs: {needs}
        Tech Reqs: {reqs}
        Risks: {risks}
        
        Return JSON with keys: 'traceability_matrix', 'inputs', 'outputs', 'verification', 'validation', 'plan'.
        Content should be Markdown formatted strings.
        """
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "You are a QA Regulatory expert."}, 
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e: return {"error": str(e)}

class UrraGenerator(BaseAIProcessor):
    @retry_with_backoff()
    def generate_urra(self, name, desc, user, env):
        if not self.client: return {"error": "API Key missing"}
        
        system_prompt = """
        You are a Risk Management expert for medical devices (ISO 14971 / IEC 62366).
        Generate a Use-Related Risk Analysis (URRA) table.
        
        Return a JSON object with a single key 'urra_rows', which contains a list of objects.
        Each object MUST have the following keys:
        - "Task": The user task being performed.
        - "Hazard": The potential hazard.
        - "Hazardous Situation": The sequence of events leading to harm.
        - "Harm": The potential injury or damage.
        - "Severity": Integer (1-5).
        - "Probability": Integer (1-5).
        - "Risk Level": String (e.g., "Low", "Medium", "High").
        - "Mitigation": Proposed risk control measure.
        """
        
        user_prompt = f"Product: {name}\nDescription: {desc}\nUser: {user}\nEnvironment: {env}\n\nGenerate 5-7 key use-related risks."
        
        try:
            res = self.client.chat.completions.create(
                model=self.model, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}

class ManualWriter(BaseAIProcessor):
    @retry_with_backoff()
    def generate_manual_section(self, section_title, product_name, product_ifu, user_inputs, target_language):
        if not self.client: return "API Key missing"
        prompt = f"Write the '{section_title}' section for a user manual for {product_name} in {target_language}. Data: {json.dumps(user_inputs)}"
        res = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content

class ProjectCharterHelper(BaseAIProcessor):
    @retry_with_backoff()
    def generate_charter_draft(self, name, problem, user):
        if not self.client: return {"error": "API Key missing"}
        prompt = f"Generate a Project Charter for med-device '{name}'. Problem: {problem}. User: {user}. Return JSON with keys: project_name, problem_statement, project_goal, scope, stakeholders, device_classification."
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "Return JSON only."}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e: return {"error": str(e)}

class VendorEmailDrafter(BaseAIProcessor):
    def draft_vendor_email(self, goal, analysis, sku, vendor, contact, english_level):
        if not self.client: return "API Key missing"
        prompt = f"Draft a professional email to {vendor} (Contact: {contact}). Goal: {goal}. SKU: {sku}. Recipient English Level: {english_level}/5."
        res = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}])
        return res.choices[0].message.content

class HumanFactorsHelper(BaseAIProcessor):
    def generate_hf_report_from_answers(self, name, ifu, answers):
        if not self.client: return {"error": "API Key missing"}
        prompt = f"Generate HFE Report sections for {name} based on answers: {json.dumps(answers)}. Return JSON with keys: conclusion_statement, descriptions, device_interface, known_problems, hazards_analysis, preliminary_analyses, critical_tasks, validation_testing."
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "Return JSON only."}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e: return {"error": str(e)}

class MedicalDeviceClassifier(BaseAIProcessor):
    def classify_device(self, desc):
        if not self.client: return {"error": "API Key missing"}
        prompt = f"Classify this medical device (FDA/EU) and provide rationale: {desc}. Return JSON with keys: classification, rationale."
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "Return JSON only."}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e: return {"error": str(e)}
