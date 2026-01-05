import streamlit as st
import sys
import os

# 1. Setup Python Path to include the 'src' directory
# This ensures Python can find your modules regardless of where the script is run
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- CORRECTED IMPORTS ---
# Based on your file structure:
from src.tabs.global_recalls import display_recalls_tab  # Located in src/tabs/
from src.document_generator import DocumentGenerator     # Located in src/
try:
    from src.ai_services import get_ai_service           # Located in src/
except ImportError:
    # Fallback in case the function is named differently in your version
    from src.ai_services import AIService as get_ai_service

# Import other tabs as needed (uncomment as you build them)
# from src.tabs.capa import display_capa_tab
# from src.tabs.risk_safety import display_risk_tab

def main():
    # --- PAGE CONFIGURATION ---
    st.set_page_config(
        page_title="CAPA Agent & Regulatory Intel",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # --- SESSION STATE INITIALIZATION ---
    if 'ai_service' not in st.session_state:
        try:
            st.session_state.ai_service = get_ai_service()
        except Exception as e:
            st.warning(f"AI Service could not be initialized: {e}")
            st.session_state.ai_service = None

    if 'product_info' not in st.session_state:
        st.session_state.product_info = {
            "name": "General Device",
            "manufacturer": "MyCompany",
            "model": "Model-X"
        }

    # --- SIDEBAR SETTINGS ---
    with st.sidebar:
        st.title("⚙️ Settings")
        st.subheader("Context")
        
        # User inputs to guide the Agent
        p_name = st.text_input("Product Name", value=st.session_state.product_info['name'])
        p_mfg = st.text_input("Manufacturer", value=st.session_state.product_info['manufacturer'])
        p_model = st.text_input("Model Number", value=st.session_state.product_info['model'])
        
        # Update session state on change
        if p_name != st.session_state.product_info['name']:
            st.session_state.product_info['name'] = p_name
        if p_mfg != st.session_state.product_info['manufacturer']:
            st.session_state.product_info['manufacturer'] = p_mfg
        if p_model != st.session_state.product_info['model']:
            st.session_state.product_info['model'] = p_model
            
        st.divider()
        st.info("System Status: Online 🟢")

    # --- MAIN CONTENT ---
    st.title("🛡️ Quality & Regulatory Command Center")
    st.markdown("Autonomous surveillance, risk detection, and CAPA management.")

    # Create the main navigation tabs
    # You can add more tabs here as you develop them (e.g., "CAPA Workflow", "Risk Management")
    tab_intel, tab_docs, tab_admin = st.tabs([
        "🌍 Regulatory Intelligence", 
        "📄 Document Generation", 
        "🔧 Admin"
    ])

    # --- TAB 1: GLOBAL RECALLS & INTELLIGENCE ---
    with tab_intel:
        # This calls the updated function with Agentic capabilities
        display_recalls_tab()

    # --- TAB 2: DOCUMENT GENERATION ---
    with tab_docs:
        st.header("Document Generator")
        st.caption("Generate Standard Operating Procedures (SOPs) and Forms.")
        
        doc_gen = DocumentGenerator()
        
        doc_type = st.selectbox("Select Document Type", ["SOP", "Work Instruction", "Form"])
        topic = st.text_input("Document Topic", placeholder="e.g. Non-Conformance Handling")
        
        if st.button("Generate Draft"):
            if not topic:
                st.error("Please enter a topic.")
            else:
                with st.spinner("Drafting document..."):
                    # specific method depends on your DocumentGenerator implementation
                    # Assuming a generic 'generate' method exists:
                    try:
                        draft = doc_gen.generate_sop(topic) # or similar method
                        st.text_area("Draft Content", value=draft, height=400)
                    except AttributeError:
                        st.warning("Document Generator method not found. Please check src/document_generator.py")

    # --- TAB 3: ADMIN ---
    with tab_admin:
        st.write("System Logs and Configuration")
        if st.checkbox("Show Session State"):
            st.json(st.session_state)

if __name__ == "__main__":
    main()
