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
        "api_key_missing": True
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    _load_api_keys()

def _load_api_keys():
    """
    Robustly loads API keys from Environment Variables OR Streamlit secrets.
    Prioritizes checking both sources to support local Streamlit dev and Cloud deployment.
    """
    found_key = None
    
    # 1. Check Environment Variables (System/Container)
    env_vars = ["GOOGLE_API_KEY", "GEMINI_API_KEY", "API_KEY"]
    for var in env_vars:
        if os.environ.get(var):
            found_key = os.environ.get(var)
            logger.info(f"API Key found in environment variable: {var}")
            break
            
    # 2. Check Streamlit Secrets (Local .streamlit/secrets.toml or Cloud Secrets)
    if not found_key:
        try:
            # Check for direct keys
            secret_keys = ["GOOGLE_API_KEY", "GEMINI_API_KEY", "API_KEY", "OPENAI_API_KEY"]
            for key in secret_keys:
                if key in st.secrets:
                    found_key = st.secrets[key]
                    logger.info(f"API Key found in st.secrets: {key}")
                    break
            
            # Check for nested keys (e.g., [google] api_key = "...")
            if not found_key and "google" in st.secrets:
                 if "api_key" in st.secrets["google"]:
                     found_key = st.secrets["google"]["api_key"]
                     logger.info("API Key found in st.secrets['google']['api_key']")

        except FileNotFoundError:
            logger.warning("No secrets.toml found.")
        except Exception as e:
            logger.warning(f"Error reading secrets: {e}")

    # 3. Update Session State
    if found_key:
        st.session_state.api_key = found_key
        st.session_state.api_key_missing = False
    else:
        st.session_state.api_key = None
        st.session_state.api_key_missing = True
        logger.error("No API Key found in Environment or Secrets.")
