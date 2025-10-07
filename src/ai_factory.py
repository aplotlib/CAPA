# src/ai_factory.py

import streamlit as st

from ai_capa_helper import (
    AICAPAHelper, AIEmailDrafter, MedicalDeviceClassifier,
    RiskAssessmentGenerator, UseRelatedRiskAnalyzer, AIHumanFactorsHelper,
    AIDesignControlsTriager, ProductManualWriter, AIProjectCharterHelper
)
from fmea import FMEA
from rca_tools import RootCauseAnalyzer
from parsers import AIFileParser
from pre_mortem import PreMortem
from ai_context_helper import AIContextHelper

HELPER_CONFIG = {
    'capa': ('ai_capa_helper', AICAPAHelper),
    'fmea': ('fmea_generator', FMEA),
    'email': ('ai_email_drafter', AIEmailDrafter),
    'rca': ('rca_helper', RootCauseAnalyzer),
    'design_controls': ('ai_design_controls_triager', AIDesignControlsTriager),
    'parser': ('parser', AIFileParser),
    'medical_device_classifier': ('medical_device_classifier', MedicalDeviceClassifier),
    'risk_assessment': ('risk_assessment_generator', RiskAssessmentGenerator),
    'urra': ('urra_generator', UseRelatedRiskAnalyzer),
    'hf_helper': ('ai_hf_helper', AIHumanFactorsHelper),
    'manual_writer': ('manual_writer', ProductManualWriter),
    'pre_mortem': ('pre_mortem_generator', PreMortem),
    'context': ('ai_context_helper', AIContextHelper),
    'charter': ('ai_charter_helper', AIProjectCharterHelper),
}

class AIHelperFactory:
    """Factory to initialize all AI helper classes."""

    @staticmethod
    def initialize_ai_helpers(api_key: str):
        """
        Creates and caches all AI helper instances in the session state.
        This is now called only once from main.py if an API key is present.
        """
        if st.session_state.get('ai_helpers_initialized', False):
            return

        for helper_type, (key, helper_class) in HELPER_CONFIG.items():
            if key not in st.session_state:
                try:
                    st.session_state[key] = helper_class(api_key=api_key)
                except Exception as e:
                    st.error(f"Failed to initialize AI helper '{key}': {e}")
        
        st.session_state.ai_helpers_initialized = True
