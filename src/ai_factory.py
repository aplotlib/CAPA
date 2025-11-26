# src/ai_factory.py

import streamlit as st

# Import helpers
from ai_capa_helper import AICAPAHelper
from ai_context_helper import AIContextHelper
# (Keep other imports as they were, e.g., FMEA, parsers, etc. assuming they exist in your repo)
# For brevity in this response, I am focusing on the factory logic:

class AIHelperFactory:
    """Factory to initialize all AI helper classes with specific model configs."""

    @staticmethod
    def initialize_ai_helpers(api_key: str, config: dict):
        """
        Creates and caches all AI helper instances in the session state.
        Now passes model configurations (fast vs reasoning).
        """
        if st.session_state.get('ai_helpers_initialized', False):
            return

        models = config.get('ai_models', {'fast': 'gpt-4o-mini', 'reasoning': 'gpt-4o'})

        # Initialize Helpers with Model Configs
        try:
            # CAPA Helper needs both models (Fast for editing, Reasoning for analysis)
            st.session_state.ai_capa_helper = AICAPAHelper(api_key=api_key, models=models)
            
            # Context Helper usually needs reasoning
            st.session_state.ai_context_helper = AIContextHelper(api_key=api_key) # You can update this class similarly if needed

            # Add other initializations here as needed...
            
            st.session_state.ai_helpers_initialized = True
            
        except Exception as e:
            st.error(f"Failed to initialize AI helpers: {e}")
