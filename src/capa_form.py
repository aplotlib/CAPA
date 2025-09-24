# src/capa_form.py

import streamlit as st
from datetime import date
from .compliance import validate_capa_data

def display_capa_form():
    """
    Displays an internationally compliant CAPA form, structured as a guided workflow.
    """
    st.header("📝 Corrective and Preventive Action (CAPA) Workflow")
    st.info(
        "This guided workflow follows the risk-based CAPA process outlined in industry best practices."
    )

    if 'capa_data' not in st.session_state:
        st.session_state.capa_data = {}
    data = st.session_state.capa_data

    # AI Suggestions Button
    if not st.session_state.get('api_key_missing', True):
        if not st.session_state.get('analysis_results'):
            st.warning("Run an analysis on the Dashboard to enable AI suggestions.")
        else:
            if st.button("🤖 Get AI Suggestions for CAPA Form", use_container_width=True):
                with st.spinner("AI is generating CAPA suggestions..."):
                    issue_summary = st.session_state.analysis_results.get('insights', 'No summary available.')
                    suggestions = st.session_state.ai_capa_helper.generate_capa_suggestions(
                        issue_summary, st.session_state.analysis_results
                    )
                    # Populate fields with suggestions, preserving existing data if suggestion is empty
                    data['issue_description'] = suggestions.get('issue_description', data.get('issue_description', ''))
                    data['root_cause'] = suggestions.get('root_cause_analysis', data.get('root_cause', ''))
                    data['corrective_action'] = suggestions.get('corrective_action', data.get('corrective_action', ''))
                    data['preventive_action'] = suggestions.get('preventive_action', data.get('preventive_action', ''))
                    data['effectiveness_verification_plan'] = suggestions.get('effectiveness_verification_plan', data.get('effectiveness_verification_plan', ''))
                    st.success("AI suggestions have been populated in the form.")


    # FIX: Replaced broken icon text with emojis for a clean UI.
    with st.expander("📂 Step 1: Initiation & Problem Description", expanded=True):
        st.markdown("##### **1.1 Identification**")
        col1, col2 = st.columns(2)
        data['capa_number'] = col1.text_input("CAPA Number", data.get('capa_number', ''))
        data['product_name'] = col1.text_input("Product Name/Model", data.get('product_name', st.session_state.get('target_sku', '')))
        data['date'] = col2.date_input("Initiation Date", data.get('date', date.today()))
        data['prepared_by'] = col2.text_input("Prepared By", data.get('prepared_by', ''))
        
        st.markdown("##### **1.2 Problem Description**")
        data['source_of_issue'] = st.selectbox("Source of Issue", 
            ['Internal Audit', 'Customer Complaint', 'Nonconforming Product', 'Management Review', 'Trend Analysis', 'Other'], 
            index=1)
        data['issue_description'] = st.text_area("Detailed Description of Non-conformity", data.get('issue_description', ''), height=150)


    with st.expander("🔍 Step 2: Investigation & Root Cause Analysis"):
        st.markdown("##### **2.1 Immediate Actions**")
        data['immediate_containment_actions'] = st.text_area("Immediate Containment Actions Taken", data.get('immediate_containment_actions', ''), height=100)
        
        st.markdown("##### **2.2 Risk Assessment**")
        r_col1, r_col2 = st.columns(2)
        data['risk_severity'] = r_col1.slider("Severity (Impact of failure)", 1, 5, data.get('risk_severity', 3), help="1: Insignificant, 5: Catastrophic")
        data['risk_probability'] = r_col2.slider("Probability (Likelihood of occurrence)", 1, 5, data.get('risk_probability', 3), help="1: Remote, 5: Frequent")
        
        st.markdown("##### **2.3 Root Cause Analysis**")
        data['root_cause'] = st.text_area("Root Cause(s) Identified (e.g., using 5 Whys, Fishbone)", data.get('root_cause', ''), height=150)

    with st.expander("🛠️ Step 3: Corrective & Preventive Action Plan"):
        data['corrective_action'] = st.text_area("Corrective Action(s) to eliminate the root cause", data.get('corrective_action', ''), height=150)
        data['preventive_action'] = st.text_area("Preventive Action(s) to prevent recurrence", data.get('preventive_action', ''), height=150)

    with st.expander("✅ Step 4: Verification & Closure"):
        data['effectiveness_verification_plan'] = st.text_area("Plan to Verify Effectiveness of Actions", data.get('effectiveness_verification_plan', ''), height=150)
        c_col1, c_col2 = st.columns(2)
        data['closed_by'] = c_col1.text_input("Closed By", data.get('closed_by', ''))
        # Allow date to be optional for closure
        data['closure_date'] = c_col2.date_input("Closure Date", value=None, key='closure_date_picker')

    # Update session state
    st.session_state.capa_data = data
    
    # Validation check at the end
    st.divider()
    if st.button("Validate CAPA Data", use_container_width=True):
        is_valid, errors, warnings = validate_capa_data(st.session_state.capa_data)
        if errors:
            for error in errors:
                st.error(error)
        else:
            st.success("Validation successful! All required fields are present.")
        
        if warnings:
            for warning in warnings:
                st.warning(warning)
