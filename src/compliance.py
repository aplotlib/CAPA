# src/compliance.py

from typing import Dict, List, Tuple
import re

def validate_capa_data(capa_data: Dict) -> Tuple[bool, List[str], List[str]]:
    """Validate CAPA data for completeness and compliance."""
    errors = []
    warnings = []
    
    required_fields = [
        'capa_number', 'product', 'sku', 'prepared_by', 'date',
        'issue_description', 'root_cause', 'corrective_action', 'preventive_action'
    ]
    
    for field in required_fields:
        if not capa_data.get(field):
            errors.append(f"Missing required field: {field.replace('_', ' ').title()}")
            
    if capa_data.get('capa_number'):
        pattern = r'^CAPA-\d{8}-\d{3}$'
        if not re.match(pattern, capa_data['capa_number']):
            warnings.append("CAPA number format should be: CAPA-YYYYMMDD-XXX")

    min_lengths = {
        'issue_description': 50, 'root_cause': 30,
        'corrective_action': 30, 'preventive_action': 30
    }
    for field, min_len in min_lengths.items():
        if field in capa_data and len(str(capa_data[field])) < min_len:
            warnings.append(f"{field.replace('_', ' ').title()} is very brief. Consider adding more detail.")
            
    is_valid = not errors
    return is_valid, errors, warnings
