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
    st.caption("Aligned with ISO 13485 & Risk-Based CAPA Processes")
    
    # Init Data
    if 'capa_data' not in st.session_state:
        st.session_state.capa_data = {
            'capa_number': f"CAPA-{date.today().strftime('%Y%m%d')}-001",
            'date': date.today(),
            'status': 'Open'
        }
    data = st.session_state.capa_data

    # --- WORKFLOW NAVIGATION ---
    # Improved Navigation: Clearer steps
    steps = ["1. Intake", "2. Review (QRB)", "3. Investigation", "4. Actions", "5. Verification", "6. Closure"]
    
    if "capa_active_step" not in st.session_state:
        st.session_state.capa_active_step = steps[0]

    selected_step = st.segmented_control(
        "Workflow Stage",
        steps,
        selection_mode="single",
        default=st.session_state.capa_active_step,
        key="capa_step_control" 
    )
    
    if selected_step:
        st.session_state.capa_active_step = selected_step

    st.divider()

    # === STEP 1: INTAKE ===
    if st.session_state.capa_active_step == steps[0]:
        st.subheader("🚀 Incident Intake")
        st.info("Step 1: Describe the issue clearly. Use Voice-to-Text for speed.")
        
        # --- Voice to Text Integration ---
        with st.container(border=True):
            st.markdown("#### 🎙️ Voice Input")
            audio_val = st.audio_input("Record Issue Description")
            
            if audio_val is not None:
                # Check if we have already transcribed this specific audio to avoid loop
                if st.session_state.get("last_audio_id") != id(audio_val):
                    with st.status("Transcribing audio...", expanded=True) as status:
                        if st.session_state.api_key_missing:
                            status.update(label="AI Key Missing", state="error")
                            st.error("Cannot transcribe without API Key.")
                        else:
                            text = st.session_state.ai_capa_helper.transcribe_audio(audio_val)
                            st.session_state.capa_data['issue_description'] = text
                            st.session_state.last_audio_id = id(audio_val)
                            status.update(label="Transcription Complete!", state="complete")
                            st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            data['capa_number'] = st.text_input("CAPA ID", value=data.get('capa_number'))
            data['product_name'] = st.text_input("Product", value=data.get('product_name', st.session_state.product_info['sku']))
        with c2:
            data['date'] = st.date_input("Initiation Date", value=data.get('date'))
            source_opts = ['Customer Complaint', 'Internal Audit', 'Nonconforming Product', 'Trend Analysis', 'Management Review']
            data['source_of_issue'] = st.pills("Source", source_opts, selection_mode="single", default=data.get('source_of_issue', 'Customer Complaint'))

        st.markdown("#### Issue Details")
        ai_assist_field("Detailed Description", "issue_desc", "Details of the non-conformity...", height=150, field_key="issue_description")
        ai_assist_field("Immediate Actions (Containment)", "imm_actions", "How will we 'stop the bleeding'?", height=100, field_key="immediate_actions")

        if st.button("💾 Submit for Review", type="primary", use_container_width=True):
            data['status'] = 'Under Review'
            st.session_state.capa_active_step = steps[1] # Move to Review
            st.toast("Request submitted to QRB!", icon="✅")
            st.rerun()

    # === STEP 2: REVIEW (QRB) ===
    elif st.session_state.capa_active_step == steps[1]:
        st.subheader("⚖️ Quality Review Board (QRB) Assessment")
        st.info("Step 3 & 4: Review risk to determine if full investigation is warranted.")
        
        st.markdown(f"**Issue:** {data.get('issue_description', 'N/A')}")
        
        st.write("#### Initial Risk Assessment")
        col1, col2 = st.columns(2)
        with col1:
             st.markdown("**Severity (Impact)**")
             data['risk_severity'] = st.slider("1 (Insignificant) - 5 (Catastrophic)", 1, 5, value=data.get('risk_severity', 3), key="risk_s")
        with col2:
             st.markdown("**Probability (Likelihood)**")
             data['risk_probability'] = st.slider("1 (Remote) - 5 (Frequent)", 1, 5, value=data.get('risk_probability', 3), key="risk_p")
        
        risk_score = data.get('risk_severity', 3) * data.get('risk_probability', 3)
        risk_label = "High" if risk_score >= 12 else ("Medium" if risk_score >= 6 else "Low")
        
        st.metric("Calculated Risk Priority", f"{risk_score} ({risk_label})")

        c_accept, c_reject = st.columns(2)
        with c_accept:
            if st.button("✅ Accept & Initiate Investigation", type="primary", use_container_width=True):
                data['status'] = 'Investigation'
                st.session_state.capa_active_step = steps[2]
                st.toast("CAPA Initiated!", icon="🚀")
                st.rerun()
        with c_reject:
            if st.button("🚫 Reject Request", use_container_width=True):
                data['status'] = 'Rejected'
                data['closure_date'] = date.today()
                st.warning("CAPA Request Rejected.")
                st.session_state.capa_active_step = steps[5] # Jump to Closure
                st.rerun()

    # === STEP 3: INVESTIGATION ===
    elif st.session_state.capa_active_step == steps[2]:
        st.subheader("🔍 Investigation & Root Cause Analysis")
        st.info("Step 7 & 8: Determine root cause using 5 Whys or Fishbone tools.")
        
        with st.popover("Need help with RCA?"):
            st.markdown("Use the **Root Cause Tools** page for 5 Whys and Fishbone diagrams.")

        ai_assist_field("Root Cause Analysis Findings", "root_cause", "What is the underlying cause?", height=200, field_key="root_cause")

        if st.button("💾 Save & Proceed to Action Plan", type="primary", use_container_width=True):
            st.session_state.capa_active_step = steps[3]
            st.toast("Investigation saved!", icon="✅")
            st.rerun()

    # === STEP 4: ACTIONS ===
    elif st.session_state.capa_active_step == steps[3]:
        st.subheader("🛠️ Corrective & Preventive Action Plan")
        st.info("Step 9 & 10: Develop and implement an action plan.")
        
        with st.expander("Corrective Actions (Fix the Issue)", expanded=True):
            ai_assist_field("Action Description", "ca_desc", height=100, field_key="corrective_action")
            ai_assist_field("Implementation Plan (Who/When)", "ca_impl", height=100, field_key="implementation_of_corrective_actions")
        
        with st.expander("Preventive Actions (Prevent Recurrence)", expanded=True):
            ai_assist_field("Action Description", "pa_desc", height=100, field_key="preventive_action")
            ai_assist_field("Implementation Plan (Who/When)", "pa_impl", height=100, field_key="implementation_of_preventive_actions")

        if st.button("💾 Save & Proceed to Verification", type="primary", use_container_width=True):
            data['status'] = 'Actions Implementation'
            st.session_state.capa_active_step = steps[4]
            st.toast("Action plan saved!", icon="✅")
            st.rerun()

    # === STEP 5: VERIFICATION ===
    elif st.session_state.capa_active_step == steps[4]:
        st.subheader("✅ Effectiveness Verification")
        st.info("Step 13 & 14: Verify that the actions were effective.")
        
        ai_assist_field("Effectiveness Check Plan", "eff_plan", "How will we prove it worked?", height=100, field_key="effectiveness_verification_plan")
        ai_assist_field("Effectiveness Findings / Evidence", "eff_findings", "Results of the check...", height=150, field_key="effectiveness_check_findings")

        if st.button("💾 Save & Proceed to Closure", type="primary", use_container_width=True):
            data['status'] = 'Verification'
            st.session_state.capa_active_step = steps[5]
            st.toast("Verification saved!", icon="✅")
            st.rerun()

    # === STEP 6: CLOSURE ===
    elif st.session_state.capa_active_step == steps[5]:
        st.subheader("🔒 Final Closure")
        
        if data.get('status') == 'Rejected':
            st.warning("This CAPA request was REJECTED.")
            ai_assist_field("Rationale for Rejection", "reject_rationale", "Why was this rejected?", height=100, field_key="additional_comments")
        else:
            st.success("All steps complete. Ready for final approval.")
            # Feedback Widget
            st.write("Rate Effectiveness of this CAPA:")
            effectiveness_rating = st.feedback("thumbs", key="capa_effectiveness_rating")
            if effectiveness_rating is not None:
                rating_map = {0: "Ineffective", 1: "Effective"}
                data['effectiveness_rating'] = rating_map[effectiveness_rating]

        c1, c2 = st.columns(2)
        data['closed_by'] = c1.text_input("Closed By", value=data.get('closed_by', ''))
        data['closure_date'] = c2.date_input("Closure Date", value=data.get('closure_date', date.today()))
        
        # UI UX Improvement: Clearer distinction between Drafting and Closing
        st.markdown("### 📥 External Review")
        st.info("Before formally closing, export the document to Word for Google Docs/Sharepoint review.")
        
        col_export, col_close = st.columns(2)
        with col_export:
             if st.button("📄 Download Draft for Review (.docx)", use_container_width=True):
                 doc_buffer = st.session_state.doc_generator.generate_summary_docx(st.session_state, ["CAPA Form"])
                 st.download_button(
                    label="Click to Save DOCX",
                    data=doc_buffer,
                    file_name=f"{data.get('capa_number')}_DRAFT.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_capa_docx_draft"
                 )
        
        with col_close:
            if st.button("🔒 FORMALLY CLOSE CAPA", type="primary", use_container_width=True):
                is_valid, errors, _ = validate_capa_data(data)
                if data.get('status') != 'Rejected' and errors:
                    for e in errors: st.error(e)
                else:
                    data['status'] = 'Closed'
                    st.balloons()
                    st.toast("CAPA Closed Successfully!", icon="🎉")
