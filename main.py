# main.py

import os
import sys
import streamlit as st
import yaml
from datetime import date, timedelta

# --- PATH SETUP ---
# Ensure the app can locate the 'src' directory relative to main.py
APP_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(APP_DIR, 'src')
sys.path.insert(0, APP_DIR)
sys.path.insert(0, SRC_DIR)

# --- IMPORTS ---
# Core logic imports from the src package
from src.ai_factory import AIHelperFactory
from src.audit_logger import AuditLogger
# Note: Ensure init_session_state is added to src/utils.py as per the refactor plan
from src.utils import init_session_state 

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ORION QMS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ASSETS & BRANDING ---
# Using native st.logo (v1.45+) for consistent branding across the sidebar and top bar
LOGO_PATH = os.path.join(APP_DIR, "logo.png") 
if os.path.exists(LOGO_PATH):
    st.logo(LOGO_PATH, icon_image=LOGO_PATH)
else:
    # Fallback/Placeholder if specific logo file is missing
    st.logo("https://placehold.co/200x80/0B0E14/00F3FF?text=ORION", link="https://streamlit.io")

# --- INITIALIZATION ---
# Initialize session state variables (user info, data, flags)
init_session_state()

# Load Configuration
try:
    with open("config.yaml", "r") as f:
        st.session_state.config = yaml.safe_load(f)
except FileNotFoundError:
    st.error("Configuration file (config.yaml) not found. Please ensure it exists in the root directory.")
    st.stop()

# Initialize AI & Core Components
# We check specifically for the API key in secrets
api_key = st.secrets.get("OPENAI_API_KEY")
st.session_state.api_key_missing = not bool(api_key)

# Initialize singleton components only once
if not st.session_state.get('components_initialized'):
    from src.data_processing import DataProcessor
    from src.document_generator import DocumentGenerator
    
    st.session_state.data_processor = DataProcessor()
    st.session_state.doc_generator = DocumentGenerator()
    st.session_state.audit_logger = AuditLogger()
    
    # Initialize AI helpers only if API key is present
    if api_key:
        AIHelperFactory.initialize_ai_helpers(api_key)
    
    st.session_state.components_initialized = True

# --- LOGIN LOGIC ---
# Mimics the structure of st.login() for future compatibility
if not st.session_state.get("logged_in", False):
    st.markdown("## ORION SYSTEM ACCESS")
    st.info("Please authenticate to access the Quality Management System.")
    
    with st.form("login_form"):
        password = st.text_input("Access Code", type="password")
        if st.form_submit_button("Initialize Link", type="primary"):
            # Check against secrets or fallback to default
            if password == st.secrets.get("APP_PASSWORD", "admin"):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.toast("Access Denied: Invalid Credentials", icon="🚫")
    # Stop execution here if not logged in
    st.stop()

# --- PAGE WRAPPERS ---
# These functions lazy-load the heavy tab modules only when the user navigates to them.

def page_dashboard():
    from src.tabs.dashboard import display_dashboard
    display_dashboard()

def page_capa():
    from src.tabs.capa import display_capa_workflow
    display_capa_workflow()

def page_rca():
    from src.tabs.rca import display_rca_tab
    display_rca_tab()

def page_risk():
    from src.tabs.risk_safety import display_risk_safety_tab
    display_risk_safety_tab()

def page_prod_dev():
    from src.tabs.product_development import display_product_development_tab
    display_product_development_tab()

def page_charter():
    from src.tabs.project_charter import display_project_charter_tab
    display_project_charter_tab()

def page_hf():
    from src.tabs.human_factors import display_human_factors_tab
    display_human_factors_tab()

def page_manual():
    from src.tabs.manual_writer import display_manual_writer_tab
    display_manual_writer_tab()

def page_exports():
    from src.tabs.exports import display_exports_tab
    display_exports_tab()

# --- NAVIGATION SETUP (Streamlit v1.46+) ---
# Defines the multi-page structure using the new native navigation
pages = {
    "Mission Control": [
        st.Page(page_dashboard, title="Dashboard", icon="📊", default=True),
        st.Page(page_exports, title="Data Exports", icon="💾"),
    ],
    "Quality Management": [
        st.Page(page_capa, title="CAPA Lifecycle", icon="⚡"),
        st.Page(page_rca, title="Root Cause Tools", icon="🔬"),
        st.Page(page_risk, title="Risk & Safety", icon="⚠️"),
        st.Page(page_hf, title="Human Factors", icon="👥"),
    ],
    "Product Development": [
        st.Page(page_charter, title="Project Charter", icon="📜"),
        st.Page(page_prod_dev, title="Design Controls", icon="🚀"),
        st.Page(page_manual, title="Manual Writer", icon="✍️"),
    ]
}

pg = st.navigation(pages)

# --- GLOBAL SIDEBAR CONTEXT ---
# Elements here persist across all pages
with st.sidebar:
    st.header("Active Asset")
    st.caption("Target System for Analysis")
    
    # Persistent inputs for the active product context
    st.session_state.product_info['sku'] = st.text_input(
        "SKU", st.session_state.product_info.get('sku', '')
    )
    st.session_state.product_info['name'] = st.text_input(
        "Name", st.session_state.product_info.get('name', '')
    )
    
    # Warning if AI is disabled
    if st.session_state.api_key_missing:
        st.divider()
        st.warning("⚠️ AI features disabled (No API Key)")

# --- APP EXECUTION ---
pg.run()
