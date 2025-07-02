# src/__init__.py

"""
Medical Device CAPA Tool - Quality Management System
AI-powered analysis for sales and returns data to generate CAPA reports.
"""

from .parsers import AIFileParser
from .data_processing import DataProcessor
from .analysis import run_full_analysis, MetricsCalculator
from .compliance import validate_capa_data, generate_compliance_checklist, get_regulatory_guidelines
from .document_generator import CapaDocumentGenerator

__version__ = "2.0.0"
__author__ = "Quality Management Team"

__all__ = [
    'AIFileParser',
    'DataProcessor',
    'run_full_analysis',
    'MetricsCalculator',
    'validate_capa_data',
    'generate_compliance_checklist',
    'get_regulatory_guidelines',
    'CapaDocumentGenerator'
]
