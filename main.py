import os
import sys
import streamlit as st
import yaml
from datetime import date

# --- PATH SETUP ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(APP_DIR, 'src')
sys.path.insert(0, APP_DIR)
sys.path.insert(0, SRC_DIR)

# --- IMPORTS ---
from src.ai_factory import AIHelperFactory
from src.audit_logger import AuditLogger
from src.utils import init_session_state
from src.services.session_manager import SessionManager

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ORION QMS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INITIALIZATION ---
init_session_state()

# Load Configuration
try:
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r") as f:
            st.session_state.config = yaml.safe_load(f)
except Exception:
    pass

# Initialize AI Components if API Key exists
if st.session_state.get('api_key') and not st.session_state.get('components_initialized'):
    # Initialize core logic
    from src.data_processing import DataProcessor
    from src.document_generator import DocumentGenerator
    
    st.session_state.data_processor = DataProcessor()
    st.session_state.doc_generator = DocumentGenerator()
    st.session_state.audit_logger = AuditLogger()
    
    # Initialize AI Factory
    AIHelperFactory.initialize_ai_helpers(st.session_state.api_key)
    st.session_state.components_initialized = True

# --- PAGE WRAPPERS ---
def page_dashboard():
    from src.tabs.dashboard import display_dashboard
    display_dashboard()

def page_capa():
    from src.tabs.capa import display_capa_workflow
    display_capa_workflow()

def page_recalls():
    from src.tabs.global_recalls import display_recalls_tab
    display_recalls_tab()

def page_exports():
    from src.tabs.exports import display_exports_tab
    display_exports_tab()

def page_instructions():
    from src.tabs.instructions import display_instructions_tab
    display_instructions_tab()

# --- NAVIGATION ---
pages = {
    "Mission Control": [
        st.Page(page_dashboard, title="Dashboard", icon="📊", default=True),
        st.Page(page_exports, title="Data Exports", icon="💾"),
    ],
    "Regulatory & Compliance": [
        st.Page(page_recalls, title="Global Recall Screen", icon="🌍"),
    ],
    "Quality Management": [
        st.Page(page_capa, title="CAPA Lifecycle", icon="⚡"),
    ],
    "Help": [
        st.Page(page_instructions, title="Guide", icon="📘"),
    ]
}

pg = st.navigation(pages)

# --- SIDEBAR UTILITIES ---
with st.sidebar:
    # Fix: Replaced use_container_width=True with width="stretch"
    st.image("https://placehold.co/200x60/0B0E14/00F3FF?text=ORION", width="stretch")
    st.header("Active Asset")
    
    if 'product_info' not in st.session_state:
        st.session_state.product_info = {}

    st.session_state.product_info['sku'] = st.text_input(
        "SKU", st.session_state.product_info.get('sku', '')
    )
    st.session_state.product_info['name'] = st.text_input(
        "Name", st.session_state.product_info.get('name', '')
    )
    
    st.divider()
    st.subheader("💾 Session Persistence")
    st.caption("Save your workspace to pick up later.")
    
    # Save
    if st.button("Save Session State"):
        json_bytes = SessionManager.export_session()
        st.download_button(
            label="Download .capa File",
            data=json_bytes,
            file_name=f"orion_session_{date.today()}.json",
            mime="application/json"
        )
    
    # Load
    uploaded_session = st.file_uploader("Load Session", type=["json"], label_visibility="collapsed")
    if uploaded_session:
        success, msg = SessionManager.load_session(uploaded_session)
        if success:
            st.success("Session Restored!")
            st.rerun()
        else:
            st.error(msg)

# --- EXECUTION ---
pg.run()
