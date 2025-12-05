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
from src.utils import init_session_state 

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ORION QMS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ASSETS & BRANDING ---
LOGO_PATH = os.path.join(APP_DIR, "logo.png") 
if os.path.exists(LOGO_PATH):
    st.logo(LOGO_PATH, icon_image=LOGO_PATH)
else:
    st.logo("https://placehold.co/200x80/0B0E14/00F3FF?text=ORION", link="https://streamlit.io")

# --- INITIALIZATION ---
init_session_state()

# Load Configuration
try:
    with open("config.yaml", "r") as f:
        st.session_state.config = yaml.safe_load(f)
except FileNotFoundError:
    st.error("Configuration file (config.yaml) not found.")
    st.stop()

# Initialize AI & Core Components
api_key = st.secrets.get("OPENAI_API_KEY")
st.session_state.api_key_missing = not bool(api_key)

if not st.session_state.get('components_initialized'):
    from src.data_processing import DataProcessor
    from src.document_generator import DocumentGenerator
    
    st.session_state.data_processor = DataProcessor()
    st.session_state.doc_generator = DocumentGenerator()
    st.session_state.audit_logger = AuditLogger()
    
    if api_key:
        AIHelperFactory.initialize_ai_helpers(api_key)
    
    st.session_state.components_initialized = True

# --- LOGIN LOGIC ---
if not st.session_state.get("logged_in", False):
    st.markdown("## ORION SYSTEM ACCESS")
    st.info("Please authenticate to access the Quality Management System.")
    
    with st.form("login_form"):
        password = st.text_input("Access Code", type="password")
        if st.form_submit_button("Initialize Link", type="primary"):
            if password == st.secrets.get("APP_PASSWORD", "admin"):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.toast("Access Denied: Invalid Credentials", icon="🚫")
    st.stop()

# --- PAGE WRAPPERS ---
def page_instructions():
    from src.tabs.instructions import display_instructions_tab
    display_instructions_tab()

def page_chat_support():
    from src.tabs.chat_support import display_chat_support_tab
    display_chat_support_tab()

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
    
def page_qmsr():
    from src.tabs.qmsr_transition import display_qmsr_transition_tab
    display_qmsr_transition_tab()

    

# --- NAVIGATION SETUP ---
pages = {
    "Help & Guide": [
        st.Page(page_instructions, title="Start Here", icon="📘"),
        st.Page(page_chat_support, title="AI Assistant", icon="💬"),
    ],
    "Compliance & Strategy": [  # <--- NEW CATEGORY
        st.Page(page_qmsr, title="QMSR Transition Portal", icon="🌐"), 
    ],
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

# --- GLOBAL SIDEBAR ---
with st.sidebar:
    st.header("Active Asset")
    st.caption("Target System for Analysis")
    
    st.session_state.product_info['sku'] = st.text_input(
        "SKU", st.session_state.product_info.get('sku', '')
    )
    st.session_state.product_info['name'] = st.text_input(
        "Name", st.session_state.product_info.get('name', '')
    )
    
    if st.session_state.api_key_missing:
        st.divider()
        st.warning("⚠️ AI features disabled (No API Key)")

# --- APP EXECUTION ---
pg.run()
