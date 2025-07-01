# src/compliance.py

"""
Module for validating CAPA data against ISO 13485 compliance requirements.
"""

from typing import Dict, List, Tuple

def validate_capa_data(capa_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validates CAPA data for ISO 13485 compliance.

    Args:
        capa_data: A dictionary containing the CAPA form data.

    Returns:
        A tuple containing:
        - bool: True if the data is valid, False otherwise.
        - List[str]: A list of compliance issues found.
    """
    issues = []

    # --- Check for presence of required fields ---
    required_fields = {
        'capa_number': 'CAPA Number',
        'product': 'Product Name',
        'sku': 'Primary SKU',
        'issue_description': 'Issue Description',
        'root_cause': 'Root Cause Analysis',
        'corrective_action': 'Corrective Actions',
        'preventive_action': 'Preventive Actions',
        'severity': 'Severity Assessment',
        'prepared_by': 'Prepared By',
        'date': 'Date'
    }

    for field, label in required_fields.items():
        if not capa_data.get(field):
            issues.append(f"Missing required field: {label} is mandatory.")

    # --- Validate content quality and specific requirements ---
    issue_desc = capa_data.get('issue_description', '')
    if len(issue_desc) < 50:
        issues.append("Issue Description is too brief. Please provide a detailed problem statement including scope and impact.")

    root_cause = capa_data.get('root_cause', '')
    if len(root_cause) < 50:
        issues.append("Root Cause Analysis is insufficient. Describe the investigation methodology (e.g., 5 Whys, Fishbone) and findings.")

    # Check for evidence of a timeline in corrective actions
    corrective_action = capa_data.get('corrective_action', '')
    if not any(keyword in corrective_action.lower() for keyword in ['timeline', 'date', 'within', 'by', 'immediate']):
        issues.append("Corrective Actions must include an implementation timeline or specific dates.")

    # Check for evidence of a monitoring plan in preventive actions
    preventive_action = capa_data.get('preventive_action', '')
    if not any(keyword in preventive_action.lower() for keyword in ['monitor', 'verify', 'review', 'check', 'schedule']):
        issues.append("Preventive Actions must include a plan for monitoring or verifying effectiveness.")

    # Validate the severity classification against allowed values
    severity = capa_data.get('severity')
    if severity and severity not in ["Critical", "Major", "Minor"]:
        issues.append(f"Severity must be classified as 'Critical', 'Major', or 'Minor', but was '{severity}'.")

    return not issues, issues
