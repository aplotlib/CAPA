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
    """Decorator to retry a function with exponential backoff."""
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
    """Initialize basic data structures in session state."""
    defaults = {
        "logged_in": False,
        "api_key": None,
        "provider": "openai", # Default to openai, will update in _load_api_keys
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
        "api_key_missing": True,
        "audit_log": []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    _load_api_keys()

def _load_api_keys():
    """Robustly loads API keys and determines the provider."""
    found_key = None
    provider = "openai" # Default

    # Helper to check sources
    def check_key(name):
        # 1. Env Var
        if os.environ.get(name): return os.environ.get(name)
        # 2. Streamlit Secrets
        if name in st.secrets: return st.secrets[name]
        return None

    # 1. Try OpenAI First
    openai_key = check_key("OPENAI_API_KEY")
    if openai_key:
        found_key = openai_key
        provider = "openai"
    
    # 2. Try Google/Gemini Second (if no OpenAI key)
    if not found_key:
        google_key = check_key("GOOGLE_API_KEY") or check_key("GEMINI_API_KEY")
        if google_key:
            found_key = google_key
            provider = "google"
            
    # 3. Generic Fallback
    if not found_key:
        generic_key = check_key("API_KEY")
        if generic_key:
            found_key = generic_key
            # Guess provider based on key format if possible, otherwise default to openai
            if generic_key.startswith("AIza"): 
                provider = "google"
            else:
                provider = "openai"

    # 4. Update Session State
    if found_key:
        st.session_state.api_key = found_key
        st.session_state.provider = provider
        st.session_state.api_key_missing = False
    else:
        st.session_state.api_key_missing = True

def initialize_ai_services():
    """Instantiates all helper classes and stores them in session state."""
    
    # --- MOVED IMPORTS HERE TO PREVENT CIRCULAR DEPENDENCY ---
    from src.ai_services import (
        AIService, DesignControlsTriager, UrraGenerator, ManualWriter, 
        ProjectCharterHelper, VendorEmailDrafter, HumanFactorsHelper, 
        MedicalDeviceClassifier
    )
    from src.ai_capa_helper import AICAPAHelper
    from src.fmea import FMEA
    from src.pre_mortem import PreMortem
    from src.rca_tools import RootCauseAnalyzer
    from src.ai_context_helper import AIContextHelper
    from src.audit_logger import AuditLogger
    from src.document_generator import DocumentGenerator
    from src.data_processing import DataProcessor
    # --------------------------------------------------------

    if st.session_state.get('services_initialized'):
        return

    api_key = st.session_state.get('api_key')
    
    # Initialize services even if key is missing (classes handle None gracefully)
    st.session_state.ai_service = AIService(api_key)
    st.session_state.ai_capa_helper = AICAPAHelper(api_key)
    st.session_state.fmea_generator = FMEA(api_key)
    st.session_state.pre_mortem_generator = PreMortem(api_key)
    st.session_state.rca_helper = RootCauseAnalyzer(api_key)
    st.session_state.ai_design_controls_triager = DesignControlsTriager(api_key)
    st.session_state.urra_generator = UrraGenerator(api_key)
    st.session_state.manual_writer = ManualWriter(api_key)
    st.session_state.ai_charter_helper = ProjectCharterHelper(api_key)
    st.session_state.ai_email_drafter = VendorEmailDrafter(api_key)
    st.session_state.ai_hf_helper = HumanFactorsHelper(api_key)
    st.session_state.medical_device_classifier = MedicalDeviceClassifier(api_key)
    st.session_state.ai_context_helper = AIContextHelper(api_key)
    
    # Non-AI Services
    st.session_state.audit_logger = AuditLogger()
    st.session_state.doc_generator = DocumentGenerator()
    st.session_state.data_processor = DataProcessor(api_key)
    
    st.session_state.services_initialized = True
    logger.info("All services initialized.")
