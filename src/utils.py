import streamlit as st
import time
import random
import functools
import logging
import os

# Import all service classes
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
    """Robustly loads API keys from Environment Variables or Secrets."""
    found_key = None
    
    # 1. Check Environment Variables
    env_vars = ["GOOGLE_API_KEY", "GEMINI_API_KEY", "API_KEY"]
    for var in env_vars:
        if os.environ.get(var):
            found_key = os.environ.get(var)
            break
            
    # 2. Check Streamlit Secrets
    if not found_key:
        try:
            secret_keys = ["GOOGLE_API_KEY", "GEMINI_API_KEY", "API_KEY", "OPENAI_API_KEY"]
            for key in secret_keys:
                if key in st.secrets:
                    found_key = st.secrets[key]
                    break
            
            if not found_key and "google" in st.secrets:
                 if "api_key" in st.secrets["google"]:
                     found_key = st.secrets["google"]["api_key"]
        except:
            pass

    # 3. Update Session State
    if found_key:
        st.session_state.api_key = found_key
        st.session_state.api_key_missing = False
    else:
        st.session_state.api_key_missing = True

def initialize_ai_services():
    """Instantiates all helper classes and stores them in session state."""
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
