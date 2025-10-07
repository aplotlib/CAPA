# src/ai_factory.py

import streamlit as st

# FIX: Import all AI helper classes at the top level for clarity and structure
from ai_capa_helper import (
    AICAPAHelper, AIEmailDrafter, MedicalDeviceClassifier,
    RiskAssessmentGenerator, UseRelatedRiskAnalyzer, AIHumanFactorsHelper,
    AIDesignControlsTriager, ProductManualWriter
)
from fmea import FMEA
from rca_tools import RootCauseAnalyzer
from parsers import AIFileParser
from pre_mortem import PreMortem
from ai_context_helper import AIContextHelper

# FIX: Create a centralized configuration for all AI helpers
# This maps a simple name to the session state key and the class to instantiate.
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

        # Iterate through the config and initialize each helper
        for helper_type, (key, helper_class) in HELPER_CONFIG.items():
            if key not in st.session_state:
                try:
                    st.session_state[key] = helper_class(api_key=api_key)
                except Exception as e:
                    # Provide a more specific error if a helper fails to load
                    st.error(f"Failed to initialize AI helper '{key}': {e}")
        
        st.session_state.ai_helpers_initialized = True
