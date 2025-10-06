# src/ai_factory.py

import streamlit as st

class AIHelperFactory:
    """Factory pattern for creating AI helpers on-demand."""

    @staticmethod
    def create_helper(helper_type: str, api_key: str):
        """
        Creates and returns an instance of the specified AI helper.
        Caches the instances in the session state to avoid re-initialization.
        """
        instance_key = f"{helper_type}_instance"
        if instance_key not in st.session_state:
            if helper_type == 'capa':
                from .ai_capa_helper import AICAPAHelper
                st.session_state[instance_key] = AICAPAHelper(api_key)
            elif helper_type == 'fmea':
                from .fmea import FMEA
                st.session_state[instance_key] = FMEA(api_key)
            elif helper_type == 'email':
                from .ai_capa_helper import AIEmailDrafter
                st.session_state[instance_key] = AIEmailDrafter(api_key)
            elif helper_type == 'rca':
                from .rca_tools import RootCauseAnalyzer
                st.session_state[instance_key] = RootCauseAnalyzer(api_key)
            # Add other helpers as needed
        return st.session_state[instance_key]
