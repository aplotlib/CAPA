# src/tabs/capa.py

import streamlit as st
from datetime import date
from src.compliance import validate_capa_data
import time

def ai_assist_field(label, key_suffix, help_text="", height=100, field_key=None):
    """
    Renders a text area with a 'Refine' button that uses the Fast AI model.
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
        if st.button("✨ Refine", key=f"btn_{key_suffix}", help="Click to have AI polish your grammar and tone."):
            if st.session_state.api_key_missing:
                st.toast("AI API Key Missing", icon="⚠️")
            else:
                with st.status("Polishing text...", expanded=False) as status:
                    refined = st.session_state.ai_capa_helper.refine_capa_input(
                        field_name=label,
                        rough_input=user_input,
                        product_context=st.session_state.product_info['name']
                    )
                    st.session_state.capa_data[field_key] = refined
                    status.update(label="Done!", state="complete")
                    time.sleep(0.5) 
                    st.rerun()

def display_capa_workflow():
    st.title("⚡ CAPA Lifecycle Hub")
    
    if 'capa_data' not in st.session_state:
        st.session_state.capa_data = {}
    
    defaults = {
        'capa_number': f"CAPA-{date.today().strftime('%Y%m%d')}-001",
        'date': date.today(),
        'status': 'Draft',
        'issue_description': '',
        'root_cause': '',
        'risk_severity': 3,
        'risk_probability': 3,
        'source_of_issue': 'Customer Complaint',
        'product_name': st.session_state.product_info.get('sku', '')
    }
    
    for k, v in defaults.items():
        if k not in st.session_state.capa_data:
            st.session_state.capa_data[k] = v

    data = st.session_state.capa_data

    # --- PROGRESS INDICATOR ---
    phases = ["Draft", "Investigation", "Implementation", "Verification", "Closed"]
    phase_icons = ["📝", "🔍", "🛠️", "✅", "🔒"]
    
    try:
        current_phase_idx = phases.index(data.get('status', 'Draft'))
    except ValueError:
        current_phase_idx = 0

    st.write("")
    progress_cols = st.columns(len(phases))
    for i, phase in enumerate(phases):
        icon = phase_icons[i]
        if i < current_phase_idx:
            progress_cols[i].markdown(f"**{icon} {phase}**")
            progress_cols[i].progress(100)
        elif i == current_phase_idx:
            progress_cols[i].markdown(f":blue[**{icon} {phase}**]")
            progress_cols[i].progress(50)
        else:
            progress_cols[i].markdown(f":grey[{icon} {phase}]")
            progress_cols[i].progress(0)
            
    st.divider()

    tab_intake, tab_investigation, tab_action, tab_closure = st.tabs([
        "1. Intake & Definition", 
        "2. Root Cause Analysis", 
        "3. Action Plan", 
        "4. Effectiveness & Closure"
    ])

    # === TAB 1: INTAKE ===
    with tab_intake:
        st.subheader("📝 Incident Definition")
        
        with st.expander("🎙️ Voice Quick-Entry", expanded=False):
            audio_val = st.audio_input("Record Issue Description")
            if audio_val:
                if st.session_state.get("last_audio_id") != id(audio_val):
                    with st.status("Transcribing and processing...", expanded=True) as status:
                        if st.session_state.api_key_missing:
                            status.update(label="API Key Missing - Cannot Transcribe", state="error")
                            st.error("Please provide an OpenAI API Key to use voice features.")
                        else:
                            text = st.session_state.ai_capa_helper.transcribe_audio(audio_val)
                            st.session_state.capa_data['issue_description'] = text
                            st.session_state.last_audio_id = id(audio_val)
                            status.update(label="Transcription Complete", state="complete")
                            st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            data['capa_number'] = st.text_input("CAPA ID", value=data.get('capa_number'), help="Unique identifier for this corrective action.")
            data['product_name'] = st.text_input("Product", value=data.get('product_name', st.session_state.product_info['sku']), help="SKU or Name of the affected product.")
        with c2:
            data['date'] = st.date_input("Initiation Date", value=data.get('date'), help="Date the issue was identified.")
            source_opts = ['Customer Complaint', 'Internal Audit', 'Nonconforming Product', 'Trend Analysis']
            current_source = data.get('source_of_issue')
            idx = source_opts.index(current_source) if current_source in source_opts else 0
            data['source_of_issue'] = st.selectbox("Source", source_opts, index=idx, help="Where did this issue originate?")

        ai_assist_field(
            "Detailed Description", 
            "issue_desc", 
            "Describe the non-conformance. Include 'What, Where, When, and How Much'.", 
            height=150, 
            field_key="issue_description"
        )
        
        if data['status'] == 'Draft':
            st.write("")
            if st.button("🚀 Advance to Investigation", type="primary", use_container_width=True):
                if not data.get('issue_description'):
                    st.error("Please provide an issue description before proceeding.")
                else:
                    data['status'] = 'Investigation'
                    st.toast("Status updated: Investigation", icon="🔍")
                    st.rerun()

    # === TAB 2: INVESTIGATION ===
    with tab_investigation:
        st.subheader("🔍 Investigation & Risk")
        
        c1, c2 = st.columns(2)
        with c1:
             st.info("Risk Assessment")
             data['risk_severity'] = st.slider("Severity", 1, 5, value=data.get('risk_severity', 3), help="1=Minor, 5=Critical/Hazardous")
             data['risk_probability'] = st.slider("Probability", 1, 5, value=data.get('risk_probability', 3), help="1=Rare, 5=Frequent")
             st.caption(f"Risk Score: {data['risk_severity'] * data['risk_probability']}")

        with c2:
            st.info("Tools")
            st.markdown("Use the **Root Cause Tools** page in the sidebar for 5 Whys / Fishbone, then paste findings below.")

        ai_assist_field(
            "Root Cause Analysis Findings", 
            "root_cause", 
            "What is the fundamental reason the problem occurred? (e.g., 'Operator error' is usually not a root cause).", 
            height=200, 
            field_key="root_cause"
        )
        
        if data['status'] == 'Investigation':
            st.write("")
            if st.button("🚀 Advance to Implementation", type="primary", use_container_width=True):
                if data.get('root_cause'):
                    data['status'] = 'Implementation'
                    st.toast("Status updated: Implementation", icon="🛠️")
                    st.rerun()
                else:
                    st.error("Please define a Root Cause before proceeding.")

    # === TAB 3: ACTION PLAN ===
    with tab_action:
        st.subheader("🛠️ Corrective & Preventive Actions")
        
        if st.button("🤖 Auto-Draft Actions from Root Cause", help="AI will suggest actions based on your root cause."):
            if not data.get('root_cause'):
                st.error("Root Cause required.")
            elif st.session_state.api_key_missing:
                st.error("AI API Key is missing.")
            else:
                with st.status("AI is analyzing root cause and drafting actions...", expanded=True) as status:
                    mock_analysis = st.session_state.get('analysis_results', {'return_summary': None})
                    suggestions = st.session_state.ai_capa_helper.generate_capa_suggestions(data['root_cause'], mock_analysis)
                    
                    if suggestions:
                        data['corrective_action'] = suggestions.get('corrective_action', '')
                        data['preventive_action'] = suggestions.get('preventive_action', '')
                        data['effectiveness_verification_plan'] = suggestions.get('effectiveness_verification_plan', '')
                        status.update(label="Drafting Complete!", state="complete")
                        st.rerun()

        ai_assist_field("Corrective Action (Fix)", "ca_desc", "Immediate action to fix the specific problem.", height=100, field_key="corrective_action")
        ai_assist_field("Preventive Action (Prevent)", "pa_desc", "Long-term action to prevent recurrence.", height=100, field_key="preventive_action")
        ai_assist_field("Implementation Plan (Who/When)", "impl_plan", "Details on responsibilities and timeline.", height=100, field_key="implementation_of_corrective_actions")

        if data['status'] == 'Implementation':
            st.write("")
            if st.button("🚀 Advance to Verification", type="primary", use_container_width=True):
                data['status'] = 'Verification'
                st.toast("Status updated: Verification", icon="✅")
                st.rerun()

    # === TAB 4: CLOSURE ===
    with tab_closure:
        st.subheader("🔒 Effectiveness & Closure")
        
        ai_assist_field("Effectiveness Check Plan", "eff_plan", "How will you prove the fix worked?", height=100, field_key="effectiveness_verification_plan")
        ai_assist_field("Effectiveness Findings / Evidence", "eff_findings", "Results of the check (e.g., 'Retested 50 units, 0 failures').", height=150, field_key="effectiveness_check_findings")

        st.divider()
        c1, c2 = st.columns(2)
        data['closed_by'] = c1.text_input("Closed By", value=data.get('closed_by', ''), help="Name of the Quality Manager closing the file.")
        data['closure_date'] = c2.date_input("Closure Date", value=data.get('closure_date', date.today()))

        if data['status'] != 'Closed':
            st.write("")
            if st.button("🔒 Verify & Close CAPA", type="primary", use_container_width=True):
                is_valid, errors, _ = validate_capa_data(data)
                if errors:
                    for e in errors: st.error(e)
                else:
                    data['status'] = 'Closed'
                    st.balloons()
                    st.success("CAPA Formally Closed.")
                    st.rerun()
        else:
            st.success("This CAPA is CLOSED.")
            if st.button("Re-open CAPA"):
                data['status'] = 'Verification'
                st.rerun()
