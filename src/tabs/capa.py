import streamlit as st
from src.ai_services import get_ai_service
from datetime import date

def display_capa_workflow():
    st.header("⚡ CAPA Lifecycle Management")
    
    # Initialize draft state if not exists
    if 'capa_entry_draft' not in st.session_state:
        st.session_state.capa_entry_draft = {}

    ai = get_ai_service()

    # --- AI INTAKE TOOLS (Voice & Transcript) ---
    col_voice, col_text = st.columns(2)
    
    with col_voice:
        with st.expander("🎙️ Voice Intake (Dictation)", expanded=True):
            st.caption("Record audio to auto-generate Issue Description & Root Cause.")
            audio_val = st.audio_input("Record Quality Event")
            
            if audio_val:
                if st.button("Process Audio", type="primary", key="proc_audio"):
                    if ai:
                        with st.spinner("Transcribing with Gemini Server-Side..."):
                            audio_bytes = audio_val.read()
                            result = ai.transcribe_and_structure(audio_bytes)
                            if "error" not in result:
                                st.session_state.capa_entry_draft.update(result)
                                st.success("Audio Processed!")
                            else:
                                st.error("Processing Failed.")
                    else:
                        st.error("AI Service not active.")

    with col_text:
        with st.expander("📝 Meeting Transcript Import", expanded=True):
            st.caption("Paste meeting notes or a transcript to extract CAPA details.")
            transcript_text = st.text_area("Paste Notes Here", height=100)
            
            if st.button("Analyze Notes", key="proc_text"):
                if ai and transcript_text:
                    with st.spinner("Analyzing Transcript..."):
                        result = ai.analyze_meeting_transcript(transcript_text)
                        if "error" not in result:
                            st.session_state.capa_entry_draft.update(result)
                            st.success("Notes Analyzed!")
                        else:
                            st.error("Analysis Failed.")
                elif not transcript_text:
                    st.warning("Please paste text first.")

    # --- CAPA FORM ---
    st.divider()
    
    draft = st.session_state.get('capa_entry_draft', {})
    
    # Display the draft data JSON if available for transparency
    if draft:
        with st.expander("🔍 View AI Extracted Data", expanded=False):
            st.json(draft)
    
    st.subheader("CAPA Initiation Form")
    
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
        
        # Issue Description (Auto-filled from voice/text)
        issue_val = draft.get('issue_description', "")
        issue_desc = st.text_area("Issue Description", value=issue_val, height=150, help="What happened? Be specific.")
        
        # Root Cause (Auto-filled from voice/text)
        rc_val = draft.get('root_cause', "")
        root_cause = st.text_area("Root Cause (Preliminary)", value=rc_val, height=100)
        
        # Immediate Actions (Auto-filled from voice/text)
        act_val = draft.get('immediate_actions', "")
        actions = st.text_area("Immediate Corrections", value=act_val, height=100)

        submitted = st.form_submit_button("Initiate CAPA Record")
        if submitted:
            # Logic to save to session state list
            if 'capa_records' not in st.session_state:
                st.session_state.capa_records = []
            
            new_record = {
                "id": f"CAPA-{len(st.session_state.capa_records)+1:03d}",
                "issue": issue_desc,
                "root_cause": root_cause,
                "actions": actions,
                "date": str(date.today())
            }
            st.session_state.capa_records.append(new_record)
            st.success("CAPA Record Initiated Successfully (Saved to Session)")
