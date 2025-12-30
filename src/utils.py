import streamlit as st

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "logged_in": False,
        "api_key": None,
        "product_info": {},
        "capa_records": [],
        "components_initialized": False,
        "capa_entry_draft": {},
        "recall_report": None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    _load_api_keys()

def _load_api_keys():
    """
    Loads API keys from Streamlit secrets.
    Prioritizes 'GOOGLE_API_KEY'. 
    Falls back to 'OPENAI_API_KEY' if that's where you pasted the Gemini key.
    """
    # 1. Check for the proper name first
    google_key = st.secrets.get("GOOGLE_API_KEY")
    
    # 2. Fallback: Check other common names if the user stored it there
    if not google_key:
        google_key = st.secrets.get("OPENAI_API_KEY")
    
    if not google_key:
        google_key = st.secrets.get("API_KEY")

    if google_key:
        st.session_state.api_key = google_key
    # Note: We don't warn here to avoid UI clutter; warning happens on AI usage if key is missing.
