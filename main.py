import streamlit as st
import os
import sys

# Ensure src is in pythonpath
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ui.recalls_tab import display_recalls_tab
from src.services.document_service import DocumentGenerator
from src.services.ai_service import AIService

# --- Config & Setup ---
st.set_page_config(
    page_title="CAPA Manager Pro",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if 'init' not in st.session_state:
    st.session_state.init = True
    
    # User Profile / Context Mock
    st.session_state.product_info = {
        "name": "Infusion Pump", 
        "manufacturer": "Acme MedCorp", 
        "model": "X-500"
    }
    
    # Services
    # Note: In production, API Key should be in secrets or env
    api_key = os.environ.get("GEMINI_API_KEY", "") 
    st.session_state.ai_service = AIService(api_key=api_key)
    st.session_state.doc_generator = DocumentGenerator()
    
    # Data Stores
    st.session_state.recall_hits = None
    st.session_state.recall_log = {}

# --- CSS Styling (Tailwind-ish look for Streamlit) ---
st.markdown("""
<style>
    .reportview-container {
        background: #fcfcfc;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
    div[data-testid="stExpander"] details summary {
        font-weight: 600;
        color: #1e293b;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Main Layout ---
def main():
    st.sidebar.title("🛡️ QA Command")
    st.sidebar.caption("ISO 13485:2016 Compliant")
    
    menu = st.sidebar.radio("Modules", ["Dashboard", "Regulatory Intelligence", "CAPA Actions", "Risk Management"])
    
    if menu == "Regulatory Intelligence":
        display_recalls_tab()
    elif menu == "Dashboard":
        st.title("Executive Dashboard")
        st.info("Select 'Regulatory Intelligence' to access the Global Recalls engine.")
    else:
        st.title(f"{menu}")
        st.warning("Module under construction.")

if __name__ == "__main__":
    main()
