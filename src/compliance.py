# src/compliance.py

from typing import Dict, List, Tuple, Optional
from datetime import datetime
import re

class ComplianceValidator:
    """Validates CAPA data for ISO 13485 and FDA compliance."""
    
    # ISO 13485 required fields for CAPA
    ISO_13485_REQUIRED_FIELDS = [
        'capa_number',
        'product',
        'sku',
        'prepared_by',
        'date',
        'issue_description',
        'root_cause',
        'corrective_action',
        'preventive_action'
    ]
    
    # FDA 21 CFR Part 820.100 requirements
    FDA_REQUIREMENTS = {
        'identification': ['capa_number', 'date', 'product'],
        'analysis': ['issue_description', 'root_cause'],
        'action': ['corrective_action', 'preventive_action'],
        'verification': ['effectiveness_check_plan'],
        'documentation': ['prepared_by', 'date']
    }
    
    @staticmethod
    def validate_field_lengths(capa_data: Dict) -> List[str]:
        """Validate that fields meet minimum length requirements."""
        warnings = []
        
        min_lengths = {
            'issue_description': 50,
            'root_cause': 30,
            'corrective_action': 30,
            'preventive_action': 30
        }
        
        for field, min_length in min_lengths.items():
            if field in capa_data:
                actual_length = len(str(capa_data[field]))
                if actual_length < min_length:
                    warnings.append(
                        f"{field.replace('_', ' ').title()} is brief ({actual_length} chars). "
                        f"Consider expanding to at least {min_length} characters for clarity."
                    )
        
        return warnings
    
    @staticmethod
    def validate_capa_number_format(capa_number: str) -> bool:
        """Validate CAPA number follows standard format."""
        # Expected format: CAPA-YYYYMMDD-XXX
        pattern = r'^CAPA-\d{8}-\d{3}$'
        return bool(re.match(pattern, capa_number))
    
    @staticmethod
    def assess_severity_appropriateness(capa_data: Dict, return_rate: Optional[float] = None) -> List[str]:
        """Assess if severity level is appropriate based on data."""
        warnings = []
        
        if return_rate is not None and 'severity' in capa_data:
            severity = capa_data['severity']
            
            # Severity guidelines based on return rate
            if return_rate > 10 and severity != 'Critical':
                warnings.append(
                    f"Return rate of {return_rate:.2f}% suggests 'Critical' severity, "
                    f"but '{severity}' was selected. Please verify."
                )
            elif 5 < return_rate <= 10 and severity not in ['Major', 'Critical']:
                warnings.append(
                    f"Return rate of {return_rate:.2f}% suggests 'Major' severity or higher, "
                    f"but '{severity}' was selected."
                )
        
        return warnings

def validate_capa_data(capa_data: Dict, analysis_results: Optional[Dict] = None) -> Tuple[bool, List[str], List[str]]:
    """
    Validate CAPA data for completeness and compliance.
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    validator = ComplianceValidator()
    
    # Check required fields
    for field in validator.ISO_13485_REQUIRED_FIELDS:
        if not capa_data.get(field):
            errors.append(f"Missing required field: {field.replace('_', ' ').title()}")
    
    # Validate CAPA number format
    if capa_data.get('capa_number'):
        if not validator.validate_capa_number_format(capa_data['capa_number']):
            warnings.append(
                "CAPA number format should be: CAPA-YYYYMMDD-XXX "
                "(e.g., CAPA-20240702-001)"
            )
    
    # Validate field lengths
    length_warnings = validator.validate_field_lengths(capa_data)
    warnings.extend(length_warnings)
    
    # Check severity appropriateness if analysis results available
    if analysis_results and 'return_summary' in analysis_results:
        if not analysis_results['return_summary'].empty:
            return_rate = analysis_results['return_summary'].iloc[0]['return_rate']
            severity_warnings = validator.assess_severity_appropriateness(capa_data, return_rate)
            warnings.extend(severity_warnings)
    
    # FDA compliance checks
    fda_missing = []
    for category, fields in validator.FDA_REQUIREMENTS.items():
        missing = [f for f in fields if not capa_data.get(f)]
        if missing and category == 'verification':
            warnings.append(f"FDA 21 CFR 820.100 recommends including: {', '.join(missing)}")
        elif missing:
            fda_missing.extend(missing)
    
    if fda_missing:
        unique_missing = list(set(fda_missing))
        warnings.append(f"Consider adding for FDA compliance: {', '.join(unique_missing)}")
    
    # Additional quality checks
    if capa_data.get('root_cause'):
        root_cause = capa_data['root_cause'].lower()
        if any(vague in root_cause for vague in ['unknown', 'tbd', 'to be determined', 'unclear']):
            warnings.append(
                "Root cause appears incomplete. A thorough root cause analysis is required "
                "for effective corrective action."
            )
    
    # Check for action measurability
    for action_field in ['corrective_action', 'preventive_action']:
        if capa_data.get(action_field):
            action_text = capa_data[action_field].lower()
            if not any(measurable in action_text for measurable in 
                      ['will', 'implement', 'review', 'update', 'train', 'modify', 'change']):
                warnings.append(
                    f"{action_field.replace('_', ' ').title()} should include specific, "
                    "measurable actions with clear deliverables."
                )
    
    # Date validation
    if capa_data.get('date'):
        try:
            date_obj = datetime.strptime(capa_data['date'], '%Y-%m-%d')
            if date_obj > datetime.now():
                errors.append("CAPA date cannot be in the future")
        except ValueError:
            errors.append("Invalid date format. Use YYYY-MM-DD")
    
    is_valid = len(errors) == 0
    
    return is_valid, errors, warnings

def generate_compliance_checklist(capa_data: Dict) -> Dict[str, List[Dict[str, any]]]:
    """Generate a compliance checklist for the CAPA."""
    
    checklist = {
        'iso_13485_requirements': [
            {
                'requirement': 'Nonconformity identification',
                'reference': 'ISO 13485:2016 Section 8.3',
                'status': 'Complete' if capa_data.get('issue_description') else 'Incomplete',
                'evidence': capa_data.get('issue_description', 'Not provided')[:100] + '...' if capa_data.get('issue_description') else 'Not provided'
            },
            {
                'requirement': 'Root cause analysis',
                'reference': 'ISO 13485:2016 Section 8.5.2',
                'status': 'Complete' if capa_data.get('root_cause') else 'Incomplete',
                'evidence': capa_data.get('root_cause', 'Not provided')[:100] + '...' if capa_data.get('root_cause') else 'Not provided'
            },
            {
                'requirement': 'Corrective action plan',
                'reference': 'ISO 13485:2016 Section 8.5.2',
                'status': 'Complete' if capa_data.get('corrective_action') else 'Incomplete',
                'evidence': capa_data.get('corrective_action', 'Not provided')[:100] + '...' if capa_data.get('corrective_action') else 'Not provided'
            },
            {
                'requirement': 'Preventive action plan',
                'reference': 'ISO 13485:2016 Section 8.5.3',
                'status': 'Complete' if capa_data.get('preventive_action') else 'Incomplete',
                'evidence': capa_data.get('preventive_action', 'Not provided')[:100] + '...' if capa_data.get('preventive_action') else 'Not provided'
            }
        ],
        'fda_requirements': [
            {
                'requirement': 'CAPA procedure documentation',
                'reference': '21 CFR 820.100(a)',
                'status': 'Complete' if all(capa_data.get(f) for f in ['capa_number', 'date', 'prepared_by']) else 'Incomplete',
                'evidence': f"CAPA {capa_data.get('capa_number', 'N/A')}"
            },
            {
                'requirement': 'Data analysis for quality problems',
                'reference': '21 CFR 820.100(a)(1)',
                'status': 'Complete' if capa_data.get('issue_description') and capa_data.get('root_cause') else 'Incomplete',
                'evidence': 'Root cause analysis provided' if capa_data.get('root_cause') else 'Not provided'
            },
            {
                'requirement': 'Investigation of nonconformity cause',
                'reference': '21 CFR 820.100(a)(2)',
                'status': 'Complete' if capa_data.get('root_cause') else 'Incomplete',
                'evidence': 'Investigation documented' if capa_data.get('root_cause') else 'Not documented'
            },
            {
                'requirement': 'Action to correct and prevent recurrence',
                'reference': '21 CFR 820.100(a)(3)',
                'status': 'Complete' if capa_data.get('corrective_action') and capa_data.get('preventive_action') else 'Incomplete',
                'evidence': 'Actions defined' if capa_data.get('corrective_action') else 'Not defined'
            }
        ],
        'mdsap_requirements': [
            {
                'requirement': 'Management review input',
                'reference': 'MDSAP Chapter 5',
                'status': 'Pending',
                'evidence': 'To be included in next management review'
            },
            {
                'requirement': 'Effectiveness verification',
                'reference': 'MDSAP Chapter 7',
                'status': 'Planned' if capa_data.get('effectiveness_check_plan') else 'Not planned',
                'evidence': capa_data.get('effectiveness_check_plan', 'Not provided')[:100] + '...' if capa_data.get('effectiveness_check_plan') else 'Not provided'
            }
        ]
    }
    
    # Calculate overall compliance score
    total_items = sum(len(reqs) for reqs in checklist.values())
    complete_items = sum(1 for reqs in checklist.values() for req in reqs if req['status'] in ['Complete', 'Planned'])
    compliance_score = (complete_items / total_items * 100) if total_items > 0 else 0
    
    checklist['compliance_score'] = round(compliance_score, 1)
    checklist['compliance_summary'] = {
        'total_requirements': total_items,
        'completed': complete_items,
        'pending': total_items - complete_items,
        'score_interpretation': 'Good' if compliance_score >= 80 else 'Needs Improvement'
    }
    
    return checklist

def get_regulatory_guidelines(severity: str, return_rate: float) -> Dict[str, str]:
    """Get regulatory guidelines based on severity and metrics."""
    
    guidelines = {
        'reporting_requirements': [],
        'timeline_requirements': {},
        'documentation_requirements': [],
        'additional_considerations': []
    }
    
    # Determine reporting requirements
    if severity == 'Critical' or return_rate > 15:
        guidelines['reporting_requirements'].extend([
            'May require FDA notification if product poses serious health risk',
            'Consider Medical Device Report (MDR) requirements under 21 CFR 803',
            'Evaluate need for Field Safety Notice (FSN) per ISO 13485'
        ])
        guidelines['timeline_requirements']['investigation'] = '5 business days'
        guidelines['timeline_requirements']['initial_action'] = 'Immediate'
        guidelines['timeline_requirements']['completion'] = '30 days'
        
    elif severity == 'Major' or return_rate > 5:
        guidelines['reporting_requirements'].append(
            'Document in quality system, monitor for trends'
        )
        guidelines['timeline_requirements']['investigation'] = '10 business days'
        guidelines['timeline_requirements']['initial_action'] = '3 business days'
        guidelines['timeline_requirements']['completion'] = '60 days'
        
    else:
        guidelines['reporting_requirements'].append(
            'Standard CAPA documentation required'
        )
        guidelines['timeline_requirements']['investigation'] = '15 business days'
        guidelines['timeline_requirements']['initial_action'] = '5 business days'
        guidelines['timeline_requirements']['completion'] = '90 days'
    
    # Documentation requirements (always required)
    guidelines['documentation_requirements'] = [
        'Complete CAPA form with all required fields',
        'Root cause analysis documentation (5 Whys, Fishbone, etc.)',
        'Effectiveness verification plan and results',
        'Management review documentation',
        'Training records if applicable'
    ]
    
    # Additional considerations
    if return_rate > 10:
        guidelines['additional_considerations'].extend([
            'Consider product recall evaluation',
            'Review similar products for systemic issues',
            'Evaluate supplier quality if applicable',
            'Consider customer notification'
        ])
    
    return guidelines
