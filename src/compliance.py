# src/compliance.py

"""
Module for validating CAPA data against ISO 13485 compliance requirements.
Now separates critical errors from non-critical warnings.
"""

from typing import Dict, List, Tuple

def validate_capa_data(capa_data: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Validates CAPA data, distinguishing between errors and warnings.

    Args:
        capa_data: A dictionary containing the CAPA form data.

    Returns:
        A tuple containing:
        - bool: True if the data has no blocking errors, False otherwise.
        - List[str]: A list of blocking errors found.
        - List[str]: A list of non-blocking warnings/suggestions.
    """
    errors = []
    warnings = []

    # --- CRITICAL ERRORS: Check for presence of absolutely required fields ---
    # These fields are essential for record-keeping and will block saving.
    required_fields = {
        'capa_number': 'CAPA Number',
        'product': 'Product Name',
        'sku': 'Primary SKU',
        'prepared_by': 'Prepared By',
        'date': 'Date'
    }
    for field, label in required_fields.items():
        if not capa_data.get(field):
            errors.append(f"Missing required field: {label} cannot be empty.")

    # --- WARNINGS: Check for content quality and best practices ---
    # These are suggestions and will not block saving.
    issue_desc = capa_data.get('issue_description', '')
    if len(issue_desc) > 0 and len(issue_desc) < 25: # Relaxed from 50
        warnings.append("Suggestion: The 'Issue Description' is very brief. Consider providing more detail about the problem.")

    root_cause = capa_data.get('root_cause', '')
    if len(root_cause) > 0 and len(root_cause) < 25: # Relaxed from 50
        warnings.append("Suggestion: The 'Root Cause Analysis' is very brief. A more detailed analysis is recommended.")

    corrective_action = capa_data.get('corrective_action', '')
    if corrective_action and not any(keyword in corrective_action.lower() for keyword in ['timeline', 'date', 'within', 'by', 'immediate', 'complete']):
        warnings.append("Suggestion: For 'Corrective Actions', consider adding an implementation timeline or target completion dates.")

    preventive_action = capa_data.get('preventive_action', '')
    if preventive_action and not any(keyword in preventive_action.lower() for keyword in ['monitor', 'verify', 'review', 'check', 'audit', 'schedule']):
        warnings.append("Suggestion: For 'Preventive Actions', consider including a plan for monitoring or verifying its effectiveness.")
    
    # The first element of the tuple is True if there are no blocking errors.
    is_valid = not errors
    
    return is_valid, errors, warnings
