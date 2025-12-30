<file_content_fetcher>
<file>
<metadata>
{"name": "metadata.json", "description": "Metadata for the file structure", "permissions": "read-write"}
</metadata>
{
  "project_name": "Orion QMS",
  "version": "2.0.0",
  "files": [
    "requirements.txt",
    "main.py",
    "src/ai_services.py",
    "src/services/session_manager.py",
    "src/tabs/global_recalls.py",
    "src/tabs/capa.py",
    "src/utils.py"
  ]
}
</file>

<file>
<metadata>
{"name": "requirements.txt", "description": "Updated dependencies for Google GenAI SDK", "permissions": "read-write"}
</metadata>
streamlit>=1.52.0
google-genai
pyyaml
pandas
plotly
fpdf
openpyxl
</file>

<file>
<metadata>
{"name": "src/ai_services.py", "description": "Refactored AI services using modern google-genai SDK", "permissions": "read-write"}
</metadata>
# src/ai_services.py
import os
import streamlit as st
from google import genai
from google.genai import types
from typing import Optional, Dict, Any, List

class AIService:
    def __init__(self, api_key: str):
        # Initialize the modern GenAI client
        self.client = genai.Client(api_key=api_key)
        # Models defined in your persona
        self.fast_model = "gemini-2.0-flash-exp" # Multimodal capable
        self.reasoning_model = "gemini-2.0-flash-thinking-exp"

    def analyze_text(self, prompt: str, system_instruction: str = None) -> str:
        """Generic text analysis using the fast model."""
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            st.error(f"AI Error: {str(e)}")
            return "Analysis failed due to AI service error."

    def transcribe_and_structure(self, audio_bytes: bytes, context: str = "") -> Dict[str, str]:
        """
        Transcribes audio and extracts structured CAPA data.
        """
        prompt = f"""
        You are a Quality Assurance Assistant. 
        Listen to this dictation regarding a potential Quality Event or CAPA.
        
        CONTEXT: {context}
        
        TASK:
        1. Transcribe the audio accurately.
        2. Extract the following fields if present:
           - Issue Description (The core problem)
           - Root Cause (If mentioned)
           - Immediate Actions (Corrections taken)
        
        OUTPUT FORMAT (JSON):
        {{
            "transcription": "Full text...",
            "issue_description": "...",
            "root_cause": "...",
            "immediate_actions": "..."
        }}
        """
        
        try:
            # Create a Part object for the audio
            # Note: streamlit returns bytes, we pass raw bytes to the client if supported
            # or wrap it in the types.Part.from_bytes if required by the SDK version.
            # Assuming standard google-genai behavior for PIL/Bytes.
            
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            import json
            return json.loads(response.text)
        except Exception as e:
            st.error(f"Transcription Error: {str(e)}")
            return {"error": str(e)}

    def screen_recalls(self, product_description: str) -> str:
        """
        Screens a product against known regulatory databases via AI knowledge.
        """
        system_prompt = """
        You are a Global Regulatory Affairs Expert (ISO 13485/MDR).
        Your task is to screen a medical device against known recall patterns and hazard alerts 
        from FDA (USA), EUDAMED (EU), TGA (Australia), Health Canada, and MHRA (UK).
        """
        
        user_prompt = f"""
        Analyze the following device for potential regulatory alerts:
        DEVICE: {product_description}
        
        1. Identify the likely classification and product code (FDA/GMDN).
        2. Summarize COMMON recall reasons for this specific type of device in the last 5 years.
        3. List any specific HIGH PROFILE alerts for this technology category.
        4. Provide a "Watchlist" of keywords to search for in the official databases.
        
        Format as a professional Markdown risk report.
        """
        
        return self.analyze_text(user_prompt, system_instruction=system_prompt)

# Singleton management
def get_ai_service():
    if 'ai_service' not in st.session_state and st.session_state.get('api_key'):
        st.session_state.ai_service = AIService(st.session_state.api_key)
    return st.session_state.get('ai_service')
</file>

<file>
<metadata>
{"name": "src/services/session_manager.py", "description": "Handles JSON persistence of session state", "permissions": "read-write"}
</metadata>
# src/services/session_manager.py
import streamlit as st
import json
import io
from datetime import datetime

class SessionManager:
    @staticmethod
    def export_session() -> bytes:
        """Exports relevant session state to a JSON byte string."""
        data = {}
        exclude_keys = {
            'ai_service', 'api_key', 'config', 'components_initialized', 
            'data_processor', 'doc_generator', 'audit_logger', 'medical_device_classifier',
            'pre_mortem_generator' # Exclude objects/services
        }
        
        for key, value in st.session_state.items():
            if key not in exclude_keys:
                # Basic type check to ensure serializability
                try:
                    json.dumps({key: value})
                    data[key] = value
                except (TypeError, OverflowError):
                    continue
        
        # Add metadata
        data['export_date'] = datetime.now().isoformat()
        data['app_version'] = "2.0.0"
        
        return json.dumps(data, indent=2).encode('utf-8')

    @staticmethod
    def load_session(uploaded_file):
        """Loads a JSON file into session state."""
        try:
            content = json.load(uploaded_file)
            for key, value in content.items():
                if key not in ['export_date', 'app_version']:
                    st.session_state[key] = value
            return True, "Session loaded successfully."
        except Exception as e:
            return False, f"Failed to load session: {str(e)}"
</file>

<file>
<metadata>
{"name": "src/tabs/global_recalls.py", "description": "New module for FDA/Global recall screening", "permissions": "read-write"}
</metadata>
# src/tabs/global_recalls.py
import streamlit as st
from src.ai_services import get_ai_service

def display_recalls_tab():
    st.header("🌍 Global Regulatory Intelligence & Recalls")
    st.caption("Screen your device against FDA, EUDAMED, MHRA, TGA, and Health Canada alerts.")

    ai = get_ai_service()
    if not ai:
        st.warning("⚠️ AI Service not initialized. Please check API Key.")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🛡️ Product Screening")
        
        # Use SKU/Name from global sidebar if available
        default_desc = ""
        if 'product_info' in st.session_state:
            default_desc = f"{st.session_state.product_info.get('name', '')} {st.session_state.product_info.get('sku', '')}"
            
        device_query = st.text_area(
            "Device Description for Analysis", 
            value=default_desc,
            placeholder="e.g., Class II Infusion Pump with wifi connectivity...",
            height=150
        )
        
        if st.button("Run Global Hazard Screen", type="primary", icon="🔍"):
            if not device_query.strip():
                st.error("Please enter a device description.")
            else:
                with st.spinner("Consulting Global Regulatory Databases (Simulated via AI)..."):
                    report = ai.screen_recalls(device_query)
                    st.session_state.recall_report = report

        if 'recall_report' in st.session_state:
            st.markdown("### 📋 Screening Report")
            st.markdown(st.session_state.recall_report)
            
            # Export Report
            st.download_button(
                "Download Report",
                st.session_state.recall_report,
                file_name="regulatory_screen.md"
            )

    with col2:
        st.subheader("🔗 Official Verification Sources")
        st.info("The AI provides intelligence, but you must verify against official databases.")
        
        sources = [
            {
                "region": "🇺🇸 USA (FDA)", 
                "name": "Recalls, Market Withdrawals & Safety Alerts", 
                "url": "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts"
            },
            {
                "region": "🇪🇺 EU (EUDAMED)", 
                "name": "Vigilance & Post-Market Surveillance", 
                "url": "https://ec.europa.eu/tools/eudamed"
            },
            {
                "region": "🇬🇧 UK (MHRA)", 
                "name": "Drug and Device Alerts", 
                "url": "https://www.gov.uk/drug-device-alerts"
            },
            {
                "region": "🇦🇺 Australia (TGA)", 
                "name": "Database of Recalls (SARA/DRAC)", 
                "url": "https://apps.tga.gov.au/PROD/DRAC/arn-entry.aspx"
            },
            {
                "region": "🇨🇦 Canada (Health Canada)", 
                "name": "Recalls and Safety Alerts", 
                "url": "https://recalls-rappels.canada.ca/en"
            },
            {
                "region": "🇯🇵 Japan (PMDA)", 
                "name": "Medical Safety Information", 
                "url": "https://www.pmda.go.jp/english/safety/info-services/safety-information/0001.html"
            }
        ]
        
        for source in sources:
            with st.expander(f"{source['region']} - {source['name']}"):
                st.markdown(f"**Direct Link:** [{source['url']}]({source['url']})")
                st.caption(f"Search this database for: *{device_query if device_query else 'Your Device'}*")

</file>

<file>
<metadata>
{"name": "src/tabs/capa.py", "description": "Updated CAPA tab with Voice Dictation", "permissions": "read-write"}
</metadata>
# src/tabs/capa.py
import streamlit as st
from src.ai_services import get_ai_service
from datetime import date

def display_capa_workflow():
    st.header("⚡ CAPA Lifecycle Management")
    
    # --- VOICE DICTATION MODULE ---
    with st.expander("🎙️ AI Voice Dictation (Fast Entry)", expanded=True):
        st.caption("Record a voice note to auto-generate the Issue Description and Root Cause.")
        
        # Uses st.audio_input (Streamlit 1.40+)
        audio_val = st.audio_input("Record Quality Event Details")
        
        if audio_val:
            if st.button("Transcribe & Process Audio", type="primary"):
                ai = get_ai_service()
                if ai:
                    with st.spinner("Listening and Analyzing..."):
                        # Read bytes from the UploadedFile object
                        audio_bytes = audio_val.read()
                        result = ai.transcribe_and_structure(audio_bytes)
                        
                        if "error" not in result:
                            # Update Session State with extracted data
                            st.session_state.capa_entry_draft = result
                            st.success("Audio processed! Data ready to apply below.")
                            st.json(result, expanded=False)
                        else:
                            st.error("Failed to process audio.")

    # --- CAPA FORM ---
    st.divider()
    
    # Pre-fill data if dictation exists
    draft = st.session_state.get('capa_entry_draft', {})
    
    with st.form("capa_initiation"):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("CAPA ID", value="CAPA-2025-001")
            st.date_input("Date Opened", value=date.today())
            st.selectbox("Risk Level", ["Low", "Medium", "High", "Critical"])
            
        with col2:
            st.text_input("Product/Process", value=st.session_state.product_info.get('name', ''))
            st.text_input("Department", placeholder="e.g. Manufacturing")
            st.selectbox("Source", ["Audit", "Customer Complaint", "Internal", "Supplier"])

        st.subheader("Event Details")
        
        # Issue Description (Auto-filled from voice)
        issue_val = draft.get('issue_description', "")
        issue_desc = st.text_area("Issue Description", value=issue_val, height=150, help="What happened? Be specific.")
        
        # Root Cause (Auto-filled from voice)
        rc_val = draft.get('root_cause', "")
        root_cause = st.text_area("Root Cause (Preliminary)", value=rc_val, height=100)
        
        # Immediate Actions (Auto-filled from voice)
        act_val = draft.get('immediate_actions', "")
        actions = st.text_area("Immediate Corrections", value=act_val, height=100)

        submitted = st.form_submit_button("Initiate CAPA Record")
        if submitted:
            st.success("CAPA Record Initiated Successfully (Session Local)")
            # In a real app, this would append to a list in session_state
            if 'capa_records' not in st.session_state:
                st.session_state.capa_records = []
            st.session_state.capa_records.append({
                "issue": issue_desc,
                "root_cause": root_cause,
                "date": str(date.today())
            })
</file>

<file>
<metadata>
{"name": "main.py", "description": "Main entry point with updated Navigation and Persistence", "permissions": "read-write"}
</metadata>
# main.py

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
from src.services.session_manager import SessionManager # New

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ORION QMS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INITIALIZATION ---
init_session_state()

# Initialize API Key in Session State if in secrets
if "OPENAI_API_KEY" in st.secrets:
    # We map OPENAI_API_KEY to 'api_key' for compatibility, 
    # but strictly we should use GOOGLE_API_KEY for the new code.
    # The user prompt implies Gemini usage, so we look for that.
    st.session_state.api_key = st.secrets.get("GOOGLE_API_KEY", st.secrets.get("OPENAI_API_KEY"))

# Load Configuration
try:
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r") as f:
            st.session_state.config = yaml.safe_load(f)
except Exception:
    pass

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
        st.Page(page_recalls, title="Global Recall Screen", icon="🌍"), # New
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
    st.image("https://placehold.co/200x60/0B0E14/00F3FF?text=ORION", use_container_width=True)
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
</file>

<file>
<metadata>
{"name": "src/utils.py", "description": "Utilities including session initialization", "permissions": "read-write"}
</metadata>
# src/utils.py
import streamlit as st

def init_session_state():
    defaults = {
        "logged_in": False,
        "api_key": None,
        "product_info": {},
        "capa_records": [],
        "components_initialized": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

</file>
</file_content_fetcher>
