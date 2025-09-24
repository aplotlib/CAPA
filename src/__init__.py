"""
Product Lifecycle & Quality Management Tool
"""

from .parsers import AIFileParser
from .data_processing import DataProcessor
from .analysis import run_full_analysis
from .compliance import validate_capa_data
from .document_generator import CapaDocumentGenerator
from .ai_capa_helper import AICAPAHelper, AIEmailDrafter, MedicalDeviceClassifier, RiskAssessmentGenerator, UseRelatedRiskAnalyzer
from .fmea import FMEA
from .pre_mortem import PreMortem
from .fba_returns_processor import ReturnsProcessor
from .ai_context_helper import AIContextHelper


__version__ = "3.0.0"
__author__ = "Quality Management Team"

__all__ = [
    'AIFileParser',
    'DataProcessor',
    'run_full_analysis',
    'validate_capa_data',
    'CapaDocumentGenerator',
    'AICAPAHelper',
    'AIEmailDrafter',
    'MedicalDeviceClassifier',
    'RiskAssessmentGenerator',
    'UseRelatedRiskAnalyzer',
    'FMEA',
    'PreMortem',
    'ReturnsProcessor', # This was missing
    'AIContextHelper'
]
