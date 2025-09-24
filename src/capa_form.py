# src/capa_form.py

import streamlit as st
from datetime import date

def display_capa_form():
    """
    Displays an internationally compliant CAPA form and captures user input.
    """
    st.header("📝 Corrective and Preventive Action (CAPA) Form")
    st.info(
        "This form is designed to comply with FDA (21 CFR 820.100), EU MDR, and common LATAM regulations. "
        "Fill out all fields to ensure a complete and compliant CAPA record."
    )

    if 'capa_data' not in st.session_state:
        st.session_state.capa_data = {}

    data = st.session_state.capa_data

    # --- Section 1: Identification ---
    st.subheader("1. Identification")
    col1, col2 = st.columns(2)
    with col1:
        data['capa_number'] = st.text_input("CAPA Number", value=data.get('capa_number', ''), help="Unique identifier for this CAPA (e.g., CAPA-YYYY-NNN).")
        data['product_name'] = st.text_input("Product Name/Model", value=data.get('product_name', st.session_state.target_sku), help="Name of the affected product.")
    with col2:
        data['initiation_date'] = st.date_input("Initiation Date", value=data.get('initiation_date', date.today()))
        data['source_of_issue'] = st.selectbox(
            "Source of Issue",
            ["Internal Audit", "Customer Complaint", "Non-conforming Product", "Management Review", "Trend Analysis", "Other"],
            index=0,
            help="Where was the issue first identified?"
        )

    # --- Section 2: Issue Description ---
    st.subheader("2. Problem Description")
    data['issue_description'] = st.text_area(
        "Detailed Description of Non-conformity",
        height=150,
        value=data.get('issue_description', ''),
        help="Provide a clear, detailed description of the issue. Include what happened, where it happened, when, and its impact."
    )
    data['immediate_containment_actions'] = st.text_area(
        "Immediate Actions/Containment",
        height=100,
        value=data.get('immediate_containment_actions', ''),
        help="Describe actions taken to immediately contain the issue and prevent it from worsening (e.g., quarantining stock)."
    )

    # --- Section 3: Risk Assessment ---
    st.subheader("3. Risk Assessment")
    st.markdown("**Assess the risk associated with the issue *before* corrective action.** (as per ISO 14971)")
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        data['risk_severity'] = st.slider("Severity of Potential Harm", 1, 5, value=data.get('risk_severity', 3), help="1=Negligible, 5=Catastrophic")
    with r_col2:
        data['risk_probability'] = st.slider("Probability of Occurrence", 1, 5, value=data.get('risk_probability', 3), help="1=Improbable, 5=Frequent")
    risk_level = data['risk_severity'] * data['risk_probability']
    st.metric("Calculated Risk Priority", f"{risk_level}", help="Risk = Severity x Probability. This determines the urgency and depth of the investigation.")

    # --- Section 4: Root Cause Analysis ---
    st.subheader("4. Root Cause Analysis (RCA)")
    data['root_cause_analysis'] = st.text_area(
        "Root Cause Analysis Findings",
        height=200,
        value=data.get('root_cause_analysis', ''),
        help="Detail the investigation and the identified root cause(s). Attach or reference any RCA tools used (e.g., 5 Whys, Fishbone Diagram)."
    )

    # --- Section 5: Corrective Action ---
    st.subheader("5. Corrective Action Plan")
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

    # --- Section 6: Preventive Action ---
    st.subheader("6. Preventive Action Plan")
    data['preventive_action'] = st.text_area(
        "Preventive Action(s) to Prevent Recurrence",
        height=150,
        value=data.get('preventive_action', ''),
        help="Describe actions to prevent this or similar issues from happening again on other products or processes."
    )
    data['preventive_action_implementation'] = st.text_area(
        "Implementation Plan for Preventive Action",
        height=150,
        value=data.get('preventive_action_implementation', ''),
        help="Who will do what by when? List specific tasks, responsible persons, and deadlines."
    )

    # --- Section 7: Verification of Effectiveness ---
    st.subheader("7. Verification of Effectiveness")
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
        help="Document the results of the verification activities and attach objective evidence."
    )

    # --- Section 8: Closure ---
    st.subheader("8. CAPA Closure")
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        data['closed_by'] = st.text_input("Closed By", value=data.get('closed_by', ''))
    with c_col2:
        data['closure_date'] = st.date_input("Closure Date", value=data.get('closure_date', date.today()))

    st.session_state.capa_data = data
