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
        if f"{helper_type}_instance" not in st.session_state:
            if helper_type == 'capa':
                from .ai_capa_helper import AICAPAHelper
                st.session_state[f"{helper_type}_instance"] = AICAPAHelper(api_key)
            elif helper_type == 'fmea':
                from .fmea import FMEA
                st.session_state[f"{helper_type}_instance"] = FMEA(api_key)
            elif helper_type == 'email':
                from .ai_capa_helper import AIEmailDrafter
                st.session_state[f"{helper_type}_instance"] = AIEmailDrafter(api_key)
            # Add other helpers as needed
        return st.session_state[f"{helper_type}_instance"]
