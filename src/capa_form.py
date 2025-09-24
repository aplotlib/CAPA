# src/capa_form.py

import streamlit as st
from datetime import date
from .compliance import validate_capa_data

def display_capa_form():
    """
    Displays an internationally compliant CAPA form, structured as a guided workflow,
    with AI assistance and a submission button that uses proper validation.
    """
    st.header("📝 Corrective and Preventive Action (CAPA) Workflow")
    st.info(
        "This guided workflow follows the risk-based CAPA process outlined in industry best practices. "
        "Complete each section to build a comprehensive and compliant CAPA record."
    )

    if 'capa_data' not in st.session_state:
        st.session_state.capa_data = {}
    data = st.session_state.capa_data

    # --- AI Assistance Button ---
    if not st.session_state.get('api_key_missing', True):
        if st.button("🤖 Get AI Suggestions for CAPA Form", help="Uses AI to fill in key fields based on the dashboard data."):
            if st.session_state.get('analysis_results'):
                with st.spinner("AI is generating CAPA suggestions..."):
                    return_summary = st.session_state.analysis_results.get('return_summary')
                    if return_summary is not None and not return_summary.empty:
                        issue_summary = f"High return rate of {return_summary.iloc[0]['return_rate']:.2f}% for SKU {st.session_state.target_sku}."
                        suggestions = st.session_state.ai_capa_helper.generate_capa_suggestions(
                            issue_summary,
                            st.session_state.analysis_results
                        )
                        st.session_state.capa_data.update(suggestions)
                        st.success("AI suggestions have been added to the form.")
                        st.rerun()
                    else:
                        st.warning("Analysis results are incomplete. Cannot generate suggestions.")
            else:
                st.warning("Please analyze some data on the dashboard first to provide context for the AI.")

    # --- Workflow Step 1: Initiation ---
    # FIX: Corrected expander labels to use emojis, not broken icon codes.
    with st.expander("📂 Step 1: CAPA Initiation & Problem Description", expanded=True):
        st.markdown("##### **1.1 Identification**")
        col1, col2 = st.columns(2)
        with col1:
            data['capa_number'] = st.text_input("CAPA Number", value=data.get('capa_number', ''), help="Unique identifier, e.g., CAPA-YYYYMMDD-001.")
            data['product_name'] = st.text_input("Product Name/Model", value=data.get('product_name', st.session_state.get('target_sku', '')), help="Name of the affected product.")
        with col2:
            data['date'] = st.date_input("Initiation Date", value=data.get('date', date.today()))
            data['prepared_by'] = st.text_input("Prepared By", value=data.get('prepared_by', ''), help="Name/title of the person initiating the CAPA.")

        data['source_of_issue'] = st.selectbox("Source of Issue", ["Internal Audit", "Customer Complaint", "Non-conforming Product", "Management Review", "Trend Analysis", "Other"])

        st.markdown("##### **1.2 Problem Description**")
        data['issue_description'] = st.text_area("Detailed Description of Non-conformity", height=150, value=data.get('issue_description', ''))

        st.markdown("##### **1.3 Immediate Actions & Containment**")
        data['immediate_containment_actions'] = st.text_area("Immediate Actions/Containment", height=100, value=data.get('immediate_containment_actions', ''))

    # --- Workflow Step 2: Investigation ---
    with st.expander("🔍 Step 2: Investigation & Root Cause Analysis"):
        st.markdown("##### **2.1 Risk Assessment**")
        r_col1, r_col2 = st.columns(2)
        data['risk_severity'] = r_col1.slider("Severity of Potential Harm", 1, 5, value=data.get('risk_severity', 3))
        data['risk_probability'] = r_col2.slider("Probability of Occurrence", 1, 5, value=data.get('risk_probability', 3))
        st.metric("Calculated Risk Priority", f"{data.get('risk_severity', 3) * data.get('risk_probability', 3)}")

        st.markdown("##### **2.2 Root Cause Analysis (RCA)**")
        data['root_cause'] = st.text_area("Root Cause Analysis Findings", height=200, value=data.get('root_cause', ''))

    # --- Workflow Step 3: Action Plan ---
    with st.expander("🛠️ Step 3: Corrective & Preventive Action Plan"):
        st.markdown("##### **3.1 Corrective Action Plan**")
        data['corrective_action'] = st.text_area("Corrective Action(s)", height=150, value=data.get('corrective_action', ''))
        st.markdown("##### **3.2 Preventive Action Plan**")
        data['preventive_action'] = st.text_area("Preventive Action(s)", height=150, value=data.get('preventive_action', ''))

    # --- Workflow Step 4: Verification & Closure ---
    with st.expander("✅ Step 4: Verification of Effectiveness & Closure"):
        st.markdown("##### **4.1 Verification of Effectiveness**")
        data['effectiveness_verification_plan'] = st.text_area("Verification Plan", height=150, value=data.get('effectiveness_verification_plan', ''))
        st.markdown("##### **4.2 CAPA Closure**")
        c_col1, c_col2 = st.columns(2)
        data['closed_by'] = c_col1.text_input("Closed By", value=data.get('closed_by', ''))
        data['closure_date'] = c_col2.date_input("Closure Date", value=data.get('closure_date', date.today()))

    st.session_state.capa_data = data
    data['sku'] = st.session_state.target_sku
    data['product'] = data.get('product_name')

    # --- Submission Button ---
    st.markdown("---")
    if st.button("🚀 Validate & Submit CAPA Report", type="primary"):
        is_valid, errors, warnings = validate_capa_data(st.session_state.capa_data)

        if warnings:
            for warning in warnings:
                st.warning(f"**Suggestion:** {warning}")
        
        if not is_valid:
            st.error("**Validation Error:** Please fix the following issues before submitting:")
            for error in errors:
                st.error(f"- {error}")
        else:
            st.success("🎉 CAPA report submitted successfully! All required fields are complete.")
            st.balloons()
