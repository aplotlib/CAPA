# src/tabs/capa.py

import streamlit as st
from datetime import date
from compliance import validate_capa_data

def display_capa_tab():
    """
    Displays an internationally compliant CAPA form, structured as a guided workflow.
    """
    st.header("Corrective and Preventive Action (CAPA) Workflow")
    st.info("This guided workflow follows a risk-based CAPA process. Use the AI suggestions for a head start.")

    if 'capa_data' not in st.session_state:
        st.session_state.capa_data = {}
    data = st.session_state.capa_data

    # --- AI Suggestions Button ---
    if not st.session_state.get('api_key_missing', True):
        if not st.session_state.get('analysis_results'):
            st.warning("Run an analysis on the Dashboard tab to enable AI-powered suggestions.")
        else:
            if st.button("🤖 Get AI Suggestions for CAPA Form", help="Click here to use AI to populate the fields below based on the analysis results.", use_container_width=True, type="primary"):
                with st.spinner("AI is generating CAPA suggestions..."):
                    issue_summary = st.session_state.analysis_results.get('insights', 'No summary available.')
                    suggestions = st.session_state.ai_capa_helper.generate_capa_suggestions(
                        issue_summary, st.session_state.analysis_results
                    )
                    if suggestions and "error" not in suggestions:
                        # More robust update that handles all suggested fields
                        for key, value in suggestions.items():
                            data[key] = value
                        st.success("✅ AI suggestions have been populated in the form below.")
                        st.rerun() # Rerun to show new values in fields
                    else:
                        st.error("Could not retrieve AI suggestions. Please try again.")

    # --- CAPA Form Sections as Tabs for cleaner look ---
    tab1, tab2, tab3, tab4 = st.tabs(["**Step 1: Initiation**", "**Step 2: Investigation**", "**Step 3: Action Plan**", "**Step 4: Verification**"])

    with tab1:
        st.subheader("Initiation & Problem Description")
        col1, col2 = st.columns(2)
        data['capa_number'] = col1.text_input("CAPA Number", value=data.get('capa_number', f"CAPA-{date.today().strftime('%Y%m%d')}-001"))
        data['product_name'] = col1.text_input("Product Name/Model", value=st.session_state.product_info.get('name', ''))
        data['date'] = col2.date_input("Initiation Date", value=data.get('date', date.today()))
        data['prepared_by'] = col2.text_input("Prepared By", value=data.get('prepared_by', ''))

        source_options = ['Internal Audit', 'Customer Complaint', 'Nonconforming Product', 'Management Review', 'Trend Analysis', 'Other']
        data['source_of_issue'] = st.selectbox("Source of Issue", source_options, index=source_options.index(data.get('source_of_issue', 'Customer Complaint')))
        data['issue_description'] = st.text_area("Detailed Description of Non-conformity", value=data.get('issue_description', ''), height=150)

    with tab2:
        st.subheader("Investigation & Root Cause Analysis")
        data['immediate_actions'] = st.text_area("Immediate Actions/Corrections", value=data.get('immediate_actions', ''), height=100, help="How will we correct the issue at hand? How will we 'stop the bleeding?'")
        
        st.markdown("**Risk Assessment**")
        r_col1, r_col2 = st.columns(2)
        data['risk_severity'] = r_col1.slider("Severity (Impact of failure)", 1, 5, value=data.get('risk_severity', 3), help="1: Insignificant, 5: Catastrophic")
        data['risk_probability'] = r_col2.slider("Probability (Likelihood of occurrence)", 1, 5, value=data.get('risk_probability', 3), help="1: Remote, 5: Frequent")

        data['root_cause'] = st.text_area("Root Cause(s) Identified (e.g., using 5 Whys, Fishbone)", value=data.get('root_cause', ''), height=150)

    with tab3:
        st.subheader("Corrective & Preventive Action Plan")
        data['corrective_action'] = st.text_area("Corrective Action(s) to eliminate the root cause", value=data.get('corrective_action', ''), height=150)
        data['implementation_of_corrective_actions'] = st.text_area("Implementation of Corrective Actions", value=data.get('implementation_of_corrective_actions', ''), height=100, help="Who will do what by when? Include responsibilities and due dates.")
        
        st.divider()
        
        data['preventive_action'] = st.text_area("Preventive Action(s) to prevent recurrence", value=data.get('preventive_action', ''), height=150)
        data['implementation_of_preventive_actions'] = st.text_area("Implementation of Preventive Actions", value=data.get('implementation_of_preventive_actions', ''), height=100, help="How will we determine all actions taken were effective?")

    with tab4:
        st.subheader("Verification & Closure Plan")
        data['effectiveness_verification_plan'] = st.text_area("Effectiveness Check Plan", value=data.get('effectiveness_verification_plan', ''), height=150, help="How will we determine all actions taken were effective?")
        st.info("The remaining closure fields are completed in the **CAPA Closure** tab after actions are implemented.")


    # --- Validation and Next Steps ---
    st.divider()
    c1, c2 = st.columns([1, 2])
    
    with c1:
        if st.button("✔️ Validate CAPA Data", use_container_width=True):
            is_valid, errors, warnings = validate_capa_data(st.session_state.capa_data)
            if errors:
                for error in errors:
                    st.error(f"**Missing Field:** {error}")
            else:
                st.success("✅ **Validation Successful!** All required fields are present.")
            if warnings:
                for warning in warnings:
                    st.warning(f"**Suggestion:** {warning}")
    
    with c2:
        if st.button("🚀 Proceed to Effectiveness Check", type="primary", use_container_width=True, help="Load this CAPA's data into the CAPA Closure tab to track effectiveness."):
            is_valid, errors, _ = validate_capa_data(st.session_state.capa_data)
            if not is_valid:
                st.error("Please ensure all required CAPA fields are filled before proceeding.")
            elif not st.session_state.get('analysis_results'):
                st.error("Please process data on the sidebar to get initial metrics before proceeding.")
            else:
                st.session_state.capa_closure_data = {
                    'original_capa': st.session_state.capa_data.copy(),
                    'original_metrics': st.session_state.analysis_results.copy()
                }
                st.success("✅ CAPA data loaded! Navigate to the 'CAPA Closure' tab to continue.")
                st.balloons()
