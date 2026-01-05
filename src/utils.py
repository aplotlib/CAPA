import streamlit as st
import time
import random
import functools
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    """
    Decorator to retry a function with exponential backoff.
    
    Args:
        retries (int): Maximum number of retries.
        backoff_in_seconds (int): Initial backoff time in seconds.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        logger.error(f"Function {func.__name__} failed after {retries} retries. Error: {e}")
                        raise e
                    
                    sleep_time = (backoff_in_seconds * 2 ** x + random.uniform(0, 1))
                    logger.warning(f"Error in {func.__name__}: {e}. Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    x += 1
        return wrapper
    return decorator

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "logged_in": False,
        "api_key": None,
        "product_info": {},
        "capa_records": [],
        "components_initialized": False,
        "capa_entry_draft": {},
        "recall_report": None,
        "analysis_results": None,
        "fmea_rows": [],
        "ai_helpers_initialized": False,
        "capa_data": {},
        "project_charter_data": {},
        "api_key_missing": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    _load_api_keys()

def _load_api_keys():
    """
    Loads API keys from Environment Variables or Streamlit secrets.
    Prioritizes 'GOOGLE_API_KEY' from the environment (Standard for Python/Containers).
    """
    # 1. Check Environment Variables (Best practice for Containers/Cloud)
    google_key = os.environ.get("GOOGLE_API_KEY")
    
    if not google_key:
        google_key = os.environ.get("GEMINI_API_KEY")
        
    if not google_key:
        google_key = os.environ.get("API_KEY")

    # 2. Fallback to Streamlit Secrets (Local Dev)
    if not google_key:
        try:
            google_key = st.secrets.get("GOOGLE_API_KEY")
            if not google_key:
                google_key = st.secrets.get("OPENAI_API_KEY") # Check legacy key name
            if not google_key:
                google_key = st.secrets.get("API_KEY")
        except FileNotFoundError:
            pass # No secrets file found

    if google_key:
        st.session_state.api_key = google_key
        st.session_state.api_key_missing = False
    else:
        st.session_state.api_key_missing = True
        logger.warning("No API Key found in Environment Variables or Secrets.")
