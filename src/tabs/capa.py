# src/tabs/capa.py

import streamlit as st
from datetime import date
from compliance import validate_capa_data

def display_capa_tab():
    """
    Displays an internationally compliant CAPA form, structured as a guided workflow.
    This version includes UI fixes and better state management.
    """
    st.header("📝 Corrective and Preventive Action (CAPA) Workflow")
    st.info(
        "This guided workflow follows a risk-based CAPA process aligned with industry best practices."
    )

    # Initialize capa_data in session state if it doesn't exist
    if 'capa_data' not in st.session_state:
        st.session_state.capa_data = {}
    data = st.session_state.capa_data

    # --- AI Suggestions Button ---
    if not st.session_state.get('api_key_missing', True):
        if not st.session_state.get('analysis_results'):
            st.warning("Run an analysis on the Dashboard tab to enable AI-powered suggestions.")
        else:
            if st.button("🤖 Get AI Suggestions for CAPA Form", help="Click here to use AI to populate the fields below based on the analysis results."):
                with st.spinner("AI is generating CAPA suggestions..."):
                    issue_summary = st.session_state.analysis_results.get('insights', 'No summary available.')
                    suggestions = st.session_state.ai_capa_helper.generate_capa_suggestions(
                        issue_summary, st.session_state.analysis_results
                    )
                    # Populate fields with suggestions, preserving existing data if a suggestion is empty
                    if suggestions and "error" not in suggestions:
                        data['issue_description'] = suggestions.get('issue_description', data.get('issue_description', ''))
                        data['root_cause'] = suggestions.get('root_cause_analysis', data.get('root_cause', ''))
                        data['corrective_action'] = suggestions.get('corrective_action', data.get('corrective_action', ''))
                        data['preventive_action'] = suggestions.get('preventive_action', data.get('preventive_action', ''))
                        data['effectiveness_verification_plan'] = suggestions.get('effectiveness_verification_plan', data.get('effectiveness_verification_plan', ''))
                        st.success("✅ AI suggestions have been populated in the form below.")
                    else:
                        st.error("Could not retrieve AI suggestions. Please try again.")

    # --- CAPA Form Sections ---
    with st.expander("📂 Step 1: Initiation & Problem Description", expanded=True):
        st.markdown("##### **1.1 Identification**")
        col1, col2 = st.columns(2)
        data['capa_number'] = col1.text_input("CAPA Number", value=data.get('capa_number', f"CAPA-{date.today().strftime('%Y%m%d')}-001"))
        # Pre-fill product name from session state if available
        product_name_default = st.session_state.product_info.get('sku', '') # Correctly get sku
        data['product_name'] = col1.text_input("Product Name/Model", value=data.get('product_name', product_name_default))
        data['date'] = col2.date_input("Initiation Date", value=data.get('date', date.today()))
        data['prepared_by'] = col2.text_input("Prepared By", value=data.get('prepared_by', ''))

        st.markdown("##### **1.2 Problem Description**")
        # Ensure source_of_issue has a default value to prevent errors
        source_options = ['Internal Audit', 'Customer Complaint', 'Nonconforming Product', 'Management Review', 'Trend Analysis', 'Other']
        current_source_index = source_options.index(data.get('source_of_issue', 'Customer Complaint'))
        data['source_of_issue'] = st.selectbox("Source of Issue", source_options, index=current_source_index)
        data['issue_description'] = st.text_area("Detailed Description of Non-conformity", value=data.get('issue_description', ''), height=150)

    with st.expander("🔍 Step 2: Investigation & Root Cause Analysis"):
        st.markdown("##### **2.1 Immediate Actions**")
        data['immediate_actions'] = st.text_area("Immediate Actions/Corrections", value=data.get('immediate_actions', ''), height=100, help="How will we correct the issue at hand? How will we 'stop the bleeding?'")

        st.markdown("##### **2.2 Risk Assessment**")
        r_col1, r_col2 = st.columns(2)
        data['risk_severity'] = r_col1.slider("Severity (Impact of failure)", 1, 5, value=data.get('risk_severity', 3), help="1: Insignificant, 5: Catastrophic")
        data['risk_probability'] = r_col2.slider("Probability (Likelihood of occurrence)", 1, 5, value=data.get('risk_probability', 3), help="1: Remote, 5: Frequent")
        
        # Add a place to store uploaded evidence files
        data['evidence_files'] = st.file_uploader("Upload Evidence (Images, PDFs, Reports)", accept_multiple_files=True)


    with st.expander("🛠️ Step 3: Corrective & Preventive Action Plan"):
        data['corrective_action'] = st.text_area("Corrective Action(s) to eliminate the root cause", value=data.get('corrective_action', ''), height=150)
        data['preventive_action'] = st.text_area("Preventive Action(s) to prevent recurrence", value=data.get('preventive_action', ''), height=150)

    with st.expander("✅ Step 4: Verification & Closure Plan"):
        data['effectiveness_verification_plan'] = st.text_area("Effectiveness Check Plan", value=data.get('effectiveness_verification_plan', ''), height=150, help="How will we determine if the actions taken were effective?")

    st.divider()
    if st.button("🚀 Proceed to Effectiveness Check", type="primary", use_container_width=True):
        is_valid, errors, warnings = validate_capa_data(st.session_state.capa_data)
        if errors:
            for error in errors:
                st.error(f"**Missing Field:** {error}")
        else:
            # Store the current data for the closure tab
            st.session_state.capa_closure_data['original_capa'] = st.session_state.capa_data.copy()
            st.session_state.capa_closure_data['original_metrics'] = st.session_state.analysis_results
            st.success("CAPA form is valid. Please proceed to the 'CAPA Closure' tab.")
            # Optionally, you could switch tabs programmatically if Streamlit adds support

        if warnings:
            for warning in warnings:
                st.warning(f"**Suggestion:** {warning}")
