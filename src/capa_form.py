# src/capa_form.py

import streamlit as st
from datetime import date

def display_capa_form():
    """
    Displays an internationally compliant CAPA form, structured as a guided workflow,
    with AI assistance and a submission button.
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
            if st.session_state.analysis_results:
                with st.spinner("AI is generating CAPA suggestions..."):
                    issue_summary = f"High return rate of {st.session_state.analysis_results['return_summary'].iloc[0]['return_rate']:.2f}% for SKU {st.session_state.target_sku}."
                    suggestions = st.session_state.ai_capa_helper.generate_capa_suggestions(
                        issue_summary,
                        st.session_state.analysis_results
                    )
                    # Update the session state with the suggestions
                    for key, value in suggestions.items():
                        if key in data:
                            data[key] = value
                    st.success("AI suggestions have been added to the form.")
            else:
                st.warning("Please analyze some data on the dashboard first to provide context for the AI.")

    # --- Workflow Step 1: Initiation ---
    with st.expander("📂 Step 1: CAPA Initiation & Problem Description", expanded=True):
        st.markdown("##### **1.1 Identification**")
        col1, col2 = st.columns(2)
        with col1:
            data['capa_number'] = st.text_input("CAPA Number", value=data.get('capa_number', ''), help="Unique identifier for this CAPA (e.g., CAPA-YYYY-NNN).")
            data['product_name'] = st.text_input("Product Name/Model", value=data.get('product_name', st.session_state.get('target_sku', '')), help="Name of the affected product.")
        with col2:
            data['initiation_date'] = st.date_input("Initiation Date", value=data.get('initiation_date', date.today()))
            data['source_of_issue'] = st.selectbox(
                "Source of Issue (CAPA Input)",
                ["Internal Audit", "Customer Complaint", "Non-conforming Product", "Management Review", "Trend Analysis", "Other"],
                help="Where was the issue first identified?"
            )

        st.markdown("##### **1.2 Problem Description**")
        data['issue_description'] = st.text_area(
            "Detailed Description of Non-conformity",
            height=150,
            value=data.get('issue_description', ''),
            help="Provide a clear, detailed description of the issue. Include what happened, where it happened, when, and its impact."
        )

        st.markdown("##### **1.3 Immediate Actions & Containment**")
        data['immediate_containment_actions'] = st.text_area(
            "Immediate Actions/Containment",
            height=100,
            value=data.get('immediate_containment_actions', ''),
            help="Describe actions taken to immediately contain the issue (e.g., quarantining stock, issuing a notice)."
        )

    # --- Workflow Step 2: Investigation ---
    with st.expander("🔍 Step 2: Investigation & Root Cause Analysis"):
        st.markdown("##### **2.1 Risk Assessment**")
        st.markdown("Assess the risk associated with the issue *before* corrective action, as per ISO 14971.")
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            data['risk_severity'] = st.slider("Severity of Potential Harm", 1, 5, value=data.get('risk_severity', 3), help="1=Negligible, 5=Catastrophic")
        with r_col2:
            data['risk_probability'] = st.slider("Probability of Occurrence", 1, 5, value=data.get('risk_probability', 3), help="1=Improbable, 5=Frequent")
        risk_level = data.get('risk_severity', 3) * data.get('risk_probability', 3)
        st.metric("Calculated Risk Priority", f"{risk_level}", help="Risk = Severity x Probability. This determines the urgency and depth of the investigation.")

        st.markdown("##### **2.2 Root Cause Analysis (RCA)**")
        data['root_cause_analysis'] = st.text_area(
            "Root Cause Analysis Findings",
            height=200,
            value=data.get('root_cause_analysis', ''),
            help="Detail the investigation and the identified root cause(s). Common tools include 5 Whys or a Fishbone (Ishikawa) Diagram."
        )

    # --- Workflow Step 3: Action Plan ---
    with st.expander("🛠️ Step 3: Corrective & Preventive Action Plan"):
        st.markdown("##### **3.1 Corrective Action Plan**")
        data['corrective_action'] = st.text_area(
            "Corrective Action(s) to Eliminate Root Cause",
            height=150,
            value=data.get('corrective_action', ''),
            help="Describe the actions that will be taken to fix the root cause of the problem."
        )
        data['corrective_action_implementation'] = st.text_area(
            "Implementation Plan for Corrective Action",
            height=150,
            value=data.get('corrective_action_implementation', ''),
            help="Who will do what by when? List specific tasks, responsible persons, and deadlines."
        )

        st.markdown("##### **3.2 Preventive Action Plan**")
        data['preventive_action'] = st.text_area(
            "Preventive Action(s) to Prevent Recurrence",
            height=150,
            value=data.get('preventive_action', ''),
            help="Describe actions to prevent this or similar issues from happening again across other products or processes."
        )
        data['preventive_action_implementation'] = st.text_area(
            "Implementation Plan for Preventive Action",
            height=150,
            value=data.get('preventive_action_implementation', ''),
            help="Who will do what by when? List specific tasks, responsible persons, and deadlines."
        )

    # --- Workflow Step 4: Verification & Closure ---
    with st.expander("✅ Step 4: Verification of Effectiveness & Closure"):
        st.markdown("##### **4.1 Verification of Effectiveness**")
        data['effectiveness_verification_plan'] = st.text_area(
            "Verification Plan",
            height=150,
            value=data.get('effectiveness_verification_plan', ''),
            help="How will you confirm that the actions taken were effective and did not introduce new risks? Define success criteria, data to be collected, and timeframe."
        )
        data['effectiveness_verification_results'] = st.text_area(
            "Verification Results & Evidence",
            height=150,
            value=data.get('effectiveness_verification_results', ''),
            help="Document the results of the verification activities and attach or reference objective evidence."
        )

        st.markdown("##### **4.2 CAPA Closure**")
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            data['closed_by'] = st.text_input("Closed By (Name/Title)", value=data.get('closed_by', ''))
        with c_col2:
            data['closure_date'] = st.date_input("Closure Date", value=data.get('closure_date', date.today()))

    st.session_state.capa_data = data

    # --- Submission Button ---
    st.markdown("---")
    if st.button("🚀 Submit CAPA Report", type="primary"):
        # Basic validation
        required_fields = [
            'capa_number', 'product_name', 'issue_description',
            'root_cause_analysis', 'corrective_action',
            'effectiveness_verification_plan'
        ]
        missing_fields = [field.replace('_', ' ').title() for field in required_fields if not data.get(field)]

        if not missing_fields:
            st.success("🎉 CAPA report submitted successfully! All required fields are complete.")
            st.balloons()
        else:
            st.error(f"**Validation Error:** Please complete the following required fields before submitting: {', '.join(missing_fields)}.")
