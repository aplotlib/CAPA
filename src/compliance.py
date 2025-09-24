# src/compliance.py

from typing import Dict, List, Tuple
import re

def validate_capa_data(capa_data: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Validates CAPA data for completeness and compliance, checking against fields
    from the CAPA form.
    """
    errors = []
    warnings = []
    
    # These fields MUST match the keys used in capa_form.py
    required_fields = [
        'capa_number', 'product_name', 'prepared_by', 'date',
        'issue_description', 'root_cause', 'corrective_action', 'preventive_action'
    ]
    
    for field in required_fields:
        if not capa_data.get(field):
            # Replace underscores and title case for user-friendly error messages
            errors.append(f"Missing required field: {field.replace('_', ' ').title()}")
            
    if capa_data.get('capa_number'):
        # Allow a more flexible format like CAPA-YYYYMMDD-XXX
        pattern = r'^CAPA-\d{8}-\d+$'
        if not re.match(pattern, capa_data['capa_number']):
            warnings.append("CAPA number format should ideally be: CAPA-YYYYMMDD-XXX (e.g., CAPA-20250924-001)")

    # Check for meaningful content length
    min_lengths = {
        'issue_description': 50,
        'root_cause': 30,
        'corrective_action': 30,
        'preventive_action': 30
    }
    for field, min_len in min_lengths.items():
        content = capa_data.get(field, "")
        if content and len(str(content)) < min_len:
            warnings.append(f"'{field.replace('_', ' ').title()}' is very brief. Consider adding more detail for a robust record.")
            
    is_valid = not errors
    return is_valid, errors, warnings
