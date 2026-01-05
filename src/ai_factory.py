import streamlit as st
# Only importing the necessary context helper if needed for Dashboard logic
# The Global Recall tab uses ai_services.py directly via get_ai_service()

class AIHelperFactory:
    """
    Factory to initialize AI helper classes.
    Updated: Removed unused helpers (CAPA, FMEA, ManualWriter, etc.)
    """

    @staticmethod
    def initialize_ai_helpers(api_key: str):
        if st.session_state.get('ai_helpers_initialized', False):
            return

        try:
            # We only keep essential helpers that might be touched by the Dashboard
            # or generic utils.
            st.session_state.ai_helpers_initialized = True
            
        except Exception as e:
            st.error(f"Failed to initialize AI helpers: {e}")
