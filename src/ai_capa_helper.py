# src/tabs/capa.py

import streamlit as st
from datetime import date
import pandas as pd
from compliance import validate_capa_data

def ai_assist_field(label, key_suffix, help_text="", height=100, field_key=None):
    """
    Helper widget that renders a text area with an optional AI Refine button.
    """
    col_main, col_ai = st.columns([5, 1])
    
    # Retrieve current value
    current_val = st.session_state.capa_data.get(field_key, "")
    
    with col_main:
        user_input = st.text_area(
            label, 
            value=current_val, 
            height=height, 
            help=help_text, 
            key=f"input_{key_suffix}"
        )
        # Update session state immediately on change
        st.session_state.capa_data[field_key] = user_input

    with col_ai:
        st.write("") # Spacer
        st.write("") 
        if st.button("✨ Refine", key=f"btn_{key_suffix}", help="Use AI to polish this text"):
            if st.session_state.api_key_missing:
                st.error("No API Key")
            else:
                with st.spinner("Polishing..."):
                    refined = st.session_state.ai_capa_helper.refine_capa_input(
                        field_name=label,
                        rough_input=user_input,
                        product_context=st.session_state.product_info['name']
                    )
                    st.session_state.capa_data[field_key] = refined
                    st.rerun()

def display_capa_tab():
    st.header("⚡ CAPA LIFECYCLE HUB")
    
    # Ensure CAPA data init
    if 'capa_data' not in st.session_state:
        st.session_state.capa_data = {
            'capa_number': f"CAPA-{date.today().strftime('%Y%m%d')}-001",
            'date': date.today(),
            'status': 'Open'
        }
    data = st.session_state.capa_data

    # --- Status Header ---
    status_color = {
        'Open': 'red',
        'Investigation': 'orange',
        'Actions Implementation': 'yellow',
        'Verification': 'blue',
        'Closed': 'green'
    }.get(data.get('status', 'Open'), 'grey')
    
    st.markdown(f"""
    <div style="padding: 10px; border: 1px solid {status_color}; border-radius: 5px; background: rgba(0,0,0,0.3); display: flex; justify-content: space-between; align-items: center;">
        <div><strong>ACTIVE CAPA:</strong> <span style="font-family:'Fira Code'; color:var(--neon-cyan);">{data.get('capa_number')}</span></div>
        <div><strong>STATUS:</strong> <span style="color:{status_color}; font-weight:bold;">{data.get('status', 'Open').upper()}</span></div>
    </div>
    <br>
    """, unsafe_allow_html=True)

    # --- Workflow Tabs ---
    tabs = st.tabs(["1. INTAKE (Fast Track)", "2. INVESTIGATION", "3. ACTIONS", "4. VERIFICATION", "5. CLOSURE"])

    # === TAB 1: INTAKE ===
    with tabs[0]:
        st.caption("🚀 Optimized for quick entry by Product Developers.")
        
        c1, c2 = st.columns(2)
        with c1:
            data['capa_number'] = st.text_input("CAPA ID", value=data.get('capa_number'))
            data['product_name'] = st.text_input("Product/Asset", value=data.get('product_name', st.session_state.product_info['sku']))
        with c2:
            data['date'] = st.date_input("Initiation Date", value=data.get('date'))
            data['prepared_by'] = st.text_input("Reporter / Prepared By", value=data.get('prepared_by', ''))

        st.divider()
        
        source_opts = ['Internal Audit', 'Customer Complaint', 'Nonconforming Product', 'Trend Analysis', 'Other']
        data['source_of_issue'] = st.selectbox("Source of Issue", source_opts, index=source_opts.index(data.get('source_of_issue')) if data.get('source_of_issue') in source_opts else 1)
        
        ai_assist_field(
            "Issue Description", 
            "issue_desc", 
            "What was the issue identified? Include source details.", 
            height=150, 
            field_key="issue_description"
        )
        
        ai_assist_field(
            "Immediate Actions / Corrections", 
            "imm_actions", 
            "How will we 'stop the bleeding' immediately?", 
            height=100, 
            field_key="immediate_actions"
        )
        
        if st.button("💾 Save Intake & Advance", type="primary"):
            data['status'] = 'Investigation'
            st.success("Intake saved. Proceeding to Investigation.")

    # === TAB 2: INVESTIGATION (RCA) ===
    with tabs[1]:
        st.info("Perform Root Cause Analysis (Fishbone/5 Whys) before filling this section.")
        
        ai_assist_field(
            "Root Cause Analysis Findings", 
            "root_cause", 
            "What is the underlying cause? Attach findings.", 
            height=200, 
            field_key="root_cause"
        )
        
        col1, col2 = st.columns(2)
        with col1:
             st.markdown("**Risk Severity**")
             data['risk_severity'] = st.slider("Severity", 1, 5, value=data.get('risk_severity', 3))
        with col2:
             st.markdown("**Risk Probability**")
             data['risk_probability'] = st.slider("Probability", 1, 5, value=data.get('risk_probability', 3))

    # === TAB 3: ACTIONS ===
    with tabs[2]:
        st.subheader("Corrective & Preventive Action Plan")
        
        with st.expander("Corrective Actions (Fix the specific issue)", expanded=True):
            ai_assist_field("Corrective Action Description", "ca_desc", "How will we correct the issue?", height=100, field_key="corrective_action")
            ai_assist_field("Implementation Plan (CA)", "ca_impl", "Who will do what by when?", height=100, field_key="implementation_of_corrective_actions")
        
        with st.expander("Preventive Actions (Prevent recurrence)", expanded=True):
            ai_assist_field("Preventive Action Description", "pa_desc", "How will we prevent recurrence?", height=100, field_key="preventive_action")
            ai_assist_field("Implementation Plan (PA)", "pa_impl", "Who will do what by when?", height=100, field_key="implementation_of_preventive_actions")

    # === TAB 4: VERIFICATION ===
    with tabs[3]:
        st.subheader("Effectiveness Check")
        st.caption("Plan how you will verify the fix works.")
        
        ai_assist_field(
            "Effectiveness Check Plan", 
            "eff_plan", 
            "Criteria for success?", 
            height=100, 
            field_key="effectiveness_verification_plan"
        )
        
        st.divider()
        st.markdown("### Post-Implementation Findings")
        ai_assist_field(
            "Effectiveness Check Findings", 
            "eff_findings", 
            "Objective evidence that the action worked.", 
            height=150, 
            field_key="effectiveness_check_findings"
        )

    # === TAB 5: CLOSURE ===
    with tabs[4]:
        st.subheader("Final Review & Sign-off")
        
        if not data.get('effectiveness_check_findings'):
            st.warning("⚠️ Effectiveness findings are missing.")
        
        c1, c2 = st.columns(2)
        data['closed_by'] = c1.text_input("Closed By (Principal Investigator)", value=data.get('closed_by', ''))
        data['closure_date'] = c2.date_input("Closure Date", value=data.get('closure_date', date.today()))
        
        data['additional_comments'] = st.text_area("Additional Comments / Residual Risk", value=data.get('additional_comments', ''))

        st.divider()
        if st.button("🔒 FORMALLY CLOSE CAPA", type="primary", use_container_width=True):
            is_valid, errors, _ = validate_capa_data(data)
            if errors:
                for e in errors: st.error(e)
            else:
                data['status'] = 'Closed'
                st.balloons()
                st.success(f"CAPA {data['capa_number']} Closed Successfully.")
                # Log to audit trail
                st.session_state.audit_logger.log_action(
                    user="current_user", action="close_capa", entity="capa", details={"id": data['capa_number']}
                )
