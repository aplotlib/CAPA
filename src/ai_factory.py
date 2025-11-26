import streamlit as st
from src.ai_capa_helper import AICAPAHelper
from src.ai_context_helper import AIContextHelper
from src.fmea import FMEA
from src.pre_mortem import PreMortem
from src.rca_tools import RootCauseAnalyzer
# Import our new consolidated services
from src.ai_services import (
    DesignControlsTriager, UrraGenerator, ManualWriter, 
    ProjectCharterHelper, VendorEmailDrafter, HumanFactorsHelper, 
    MedicalDeviceClassifier
)

class AIHelperFactory:
    """Factory to initialize all AI helper classes."""

    @staticmethod
    def initialize_ai_helpers(api_key: str):
        if st.session_state.get('ai_helpers_initialized', False):
            return

        try:
            # Core Helpers
            st.session_state.ai_capa_helper = AICAPAHelper(api_key=api_key)
            st.session_state.ai_context_helper = AIContextHelper(api_key=api_key)
            
            # Tool Specific Helpers
            st.session_state.rca_helper = RootCauseAnalyzer(api_key=api_key)
            st.session_state.fmea_generator = FMEA(api_key=api_key)
            st.session_state.pre_mortem_generator = PreMortem(api_key=api_key)
            
            # Services from ai_services.py
            st.session_state.ai_design_controls_triager = DesignControlsTriager(api_key)
            st.session_state.urra_generator = UrraGenerator(api_key)
            st.session_state.manual_writer = ManualWriter(api_key)
            st.session_state.ai_charter_helper = ProjectCharterHelper(api_key)
            st.session_state.ai_email_drafter = VendorEmailDrafter(api_key)
            st.session_state.ai_hf_helper = HumanFactorsHelper(api_key)
            st.session_state.medical_device_classifier = MedicalDeviceClassifier(api_key)
            
            st.session_state.ai_helpers_initialized = True
            
        except Exception as e:
            st.error(f"Failed to initialize AI helpers: {e}")
