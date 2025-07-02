# src/compliance.py
from typing import Dict, List, Tuple
def validate_capa_data(capa_data: Dict) -> Tuple[bool, List[str], List[str]]:
    errors, warnings = [], []
    required_fields = ['capa_number', 'product', 'sku', 'prepared_by', 'date']
    for field in required_fields:
        if not capa_data.get(field):
            errors.append(f"Missing required field: {field.replace('_', ' ').title()}")
    if len(capa_data.get('issue_description', '')) < 10:
        warnings.append("Suggestion: The issue description is very brief.")
    return not errors, errors, warnings
