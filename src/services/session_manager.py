import streamlit as st
import json
from datetime import datetime

class SessionManager:
    @staticmethod
    def export_session() -> bytes:
        """Exports relevant session state to a JSON byte string."""
        data = {}
        # Keys to exclude from serialization (objects, API keys, large binary data)
        exclude_keys = {
            'ai_service', 'api_key', 'config', 'components_initialized', 
            'data_processor', 'doc_generator', 'audit_logger', 
            'medical_device_classifier', 'pre_mortem_generator',
            'rca_helper', 'fmea_generator', 'ai_design_controls_triager',
            'urra_generator', 'manual_writer', 'ai_charter_helper',
            'ai_email_drafter', 'ai_hf_helper', 'ai_capa_helper', 'ai_context_helper'
        }
        
        for key, value in st.session_state.items():
            if key not in exclude_keys:
                try:
                    # Verify serializability
                    json.dumps({key: value})
                    data[key] = value
                except (TypeError, OverflowError):
                    continue
        
        # Add metadata
        data['export_date'] = datetime.now().isoformat()
        data['app_version'] = "2.0.0"
        
        return json.dumps(data, indent=2).encode('utf-8')

    @staticmethod
    def load_session(uploaded_file):
        """Loads a JSON file into session state."""
        try:
            content = json.load(uploaded_file)
            for key, value in content.items():
                if key not in ['export_date', 'app_version']:
                    st.session_state[key] = value
            return True, "Session loaded successfully."
        except Exception as e:
            return False, f"Failed to load session: {str(e)}"
