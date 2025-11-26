# src/tabs/capa.py

import streamlit as st
from datetime import date
from src.compliance import validate_capa_data
import time

def ai_assist_field(label, key_suffix, help_text="", height=100, field_key=None):
    """
    Renders a text area with an AI Refine button.
    Uses st.rerun() explicitly to ensure UI updates after refinement.
    """
    col_main, col_ai = st.columns([5, 1], vertical_alignment="bottom")
    
    # Ensure key exists in data
    if field_key not in st.session_state.capa_data:
        st.session_state.capa_data[field_key] = ""

    current_val = st.session_state.capa_data[field_key]
    
    with col_main:
        user_input = st.text_area(
            label, 
            value=current_val, 
            height=height, 
            help=help_text, 
            key=f"input_{key_suffix}"
        )
        # Sync input back to session state
        st.session_state.capa_data[field_key] = user_input

    with col_ai:
        if st.button("✨ Refine", key=f"btn_{key_suffix}", help="AI Polish"):
            if st.session_state.api_key_missing:
                st.toast("AI API Key Missing", icon="⚠️")
            else:
                with st.spinner("Polishing..."):
                    refined = st.session_state.ai_capa_helper.refine_capa_input(
                        field_name=label,
                        rough_input=user_input,
                        product_context=st.session_state.product_info['name']
                    )
                    st.session_state.capa_data[field_key] = refined
                    st.toast("Text refined!", icon="✨")
                    time.sleep(0.5) # Brief pause for UX
                    st.rerun()

def display_capa_workflow():
    st.title("⚡ CAPA Lifecycle Hub")
    
    # Init Data
    if 'capa_data' not in st.session_state:
        st.session_state.capa_data = {
            'capa_number': f"CAPA-{date.today().strftime('%Y%m%d')}-001",
            'date': date.today(),
            'status': 'Open'
        }
    data = st.session_state.capa_data

    # --- WORKFLOW NAVIGATION (st.segmented_control v1.51) ---
    steps = ["1. Intake", "2. Investigation", "3. Actions", "4. Verification", "5. Closure"]
    
    # Initialize step if not present
    if "capa_active_step" not in st.session_state:
        st.session_state.capa_active_step = steps[0]

    selected_step = st.segmented_control(
        "Workflow Stage",
        steps,
        selection_mode="single",
        default=st.session_state.capa_active_step,
        key="capa_step_control" # We monitor this key
    )
    
    # Sync segmented control with session state if user clicks directly
    if selected_step:
        st.session_state.capa_active_step = selected_step

    st.divider()

    # === STEP 1: INTAKE ===
    if st.session_state.capa_active_step == steps[0]:
        st.subheader("🚀 Incident Intake")
        
        c1, c2 = st.columns(2)
        with c1:
            data['capa_number'] = st.text_input("CAPA ID", value=data.get('capa_number'))
            data['product_name'] = st.text_input("Product", value=data.get('product_name', st.session_state.product_info['sku']))
        with c2:
            data['date'] = st.date_input("Initiation Date", value=data.get('date'))
            
            # Use st.pills for Source (v1.50+)
            source_opts = ['Customer Complaint', 'Internal Audit', 'Nonconforming Product', 'Trend Analysis']
            data['source_of_issue'] = st.pills("Source", source_opts, selection_mode="single", default=data.get('source_of_issue', 'Customer Complaint'))

        st.markdown("#### Issue Description")
        
        # New: Audio Input for Voice-to-Text (v1.45+)
        audio_val = st.audio_input("Record Issue Description")
        if audio_val:
            st.info("🎤 Audio captured. (Transcription placeholder: 'User reported device overheating...')")
            # In real app: send audio_val to OpenAI Whisper API here
        
        ai_assist_field("Detailed Description", "issue_desc", "Details...", height=150, field_key="issue_description")
        ai_assist_field("Immediate Actions", "imm_actions", "Containment...", height=100, field_key="immediate_actions")

        if st.button("💾 Save & Proceed to Investigation", type="primary", use_container_width=True):
            data['status'] = 'Investigation'
            st.session_state.capa_active_step = steps[1] # Move to next step
            st.toast("Intake saved!", icon="✅")
            st.rerun()

    # === STEP 2: INVESTIGATION ===
    elif st.session_state.capa_active_step == steps[1]:
        st.subheader("🔍 Investigation & RCA")
        
        # Popover for Context/Help
        with st.popover("Need help with RCA?"):
            st.markdown("Use the **Root Cause Tools** page for 5 Whys and Fishbone diagrams, then paste the summary here.")

        ai_assist_field("Root Cause Analysis", "root_cause", "Underlying cause...", height=200, field_key="root_cause")
        
        st.write("#### Risk Assessment")
        col1, col2 = st.columns(2)
        with col1:
             st.markdown("Severity")
             data['risk_severity'] = st.slider("S", 1, 5, value=data.get('risk_severity', 3), key="risk_s")
        with col2:
             st.markdown("Probability")
             data['risk_probability'] = st.slider("P", 1, 5, value=data.get('risk_probability', 3), key="risk_p")

        if st.button("💾 Save & Proceed to Actions", type="primary", use_container_width=True):
            st.session_state.capa_active_step = steps[2]
            st.toast("Investigation saved!", icon="✅")
            st.rerun()

    # === STEP 3: ACTIONS ===
    elif st.session_state.capa_active_step == steps[2]:
        st.subheader("🛠️ Action Plan")
        
        with st.expander("Corrective Actions (Fix)", expanded=True):
            ai_assist_field("Action Description", "ca_desc", height=100, field_key="corrective_action")
            ai_assist_field("Implementation Plan", "ca_impl", height=100, field_key="implementation_of_corrective_actions")
        
        with st.expander("Preventive Actions (Prevent)", expanded=True):
            ai_assist_field("Action Description", "pa_desc", height=100, field_key="preventive_action")
            ai_assist_field("Implementation Plan", "pa_impl", height=100, field_key="implementation_of_preventive_actions")

        if st.button("💾 Save & Proceed to Verification", type="primary", use_container_width=True):
            data['status'] = 'Actions Implementation'
            st.session_state.capa_active_step = steps[3]
            st.toast("Actions saved!", icon="✅")
            st.rerun()

    # === STEP 4: VERIFICATION ===
    elif st.session_state.capa_active_step == steps[3]:
        st.subheader("✅ Verification")
        ai_assist_field("Effectiveness Check Plan", "eff_plan", "Criteria...", height=100, field_key="effectiveness_verification_plan")
        ai_assist_field("Findings / Evidence", "eff_findings", "Results...", height=150, field_key="effectiveness_check_findings")

        if st.button("💾 Save & Proceed to Closure", type="primary", use_container_width=True):
            data['status'] = 'Verification'
            st.session_state.capa_active_step = steps[4]
            st.toast("Verification saved!", icon="✅")
            st.rerun()

    # === STEP 5: CLOSURE ===
    elif st.session_state.capa_active_step == steps[4]:
        st.subheader("🔒 Final Closure")
        
        # New: Feedback Widget for Effectiveness Rating (v1.51)
        st.write("Rate Effectiveness of this CAPA:")
        effectiveness_rating = st.feedback("thumbs", key="capa_effectiveness_rating")
        if effectiveness_rating is not None:
            rating_map = {0: "Ineffective", 1: "Effective"}
            data['effectiveness_rating'] = rating_map[effectiveness_rating]

        c1, c2 = st.columns(2)
        data['closed_by'] = c1.text_input("Closed By", value=data.get('closed_by', ''))
        data['closure_date'] = c2.date_input("Closure Date", value=data.get('closure_date', date.today()))
        
        if st.button("🔒 FORMALLY CLOSE CAPA", type="primary", use_container_width=True):
            is_valid, errors, _ = validate_capa_data(data)
            if errors:
                for e in errors: st.error(e)
            else:
                data['status'] = 'Closed'
                st.balloons()
                st.toast("CAPA Closed Successfully!", icon="🎉")

    # === EXPORT & PREVIEW (Sidebar or Bottom) ===
    st.markdown("---")
    with st.expander("📄 Document Actions", expanded=True):
        col_exp1, col_exp2 = st.columns([1,1])
        with col_exp1:
             # Simulating PDF Preview (v1.49+)
             if st.button("👁️ Generate Preview"):
                 # In a real app, generate the bytes. Here we mock.
                 st.info("Previewing generated document...")
                 # st.pdf(pdf_bytes) # Use this if you have actual bytes
        
        with col_exp2:
             if st.button("📥 Export CAPA (.docx)"):
                 doc_buffer = st.session_state.doc_generator.generate_summary_docx(st.session_state, ["CAPA Form"])
                 st.download_button(
                    label="Download DOCX",
                    data=doc_buffer,
                    file_name=f"{data.get('capa_number')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_capa_docx"
                 )
