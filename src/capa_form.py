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

    if not st.session_state.get('api_key_missing', True):
        if st.button("🤖 Get AI Suggestions for CAPA Form"):
            # AI suggestion logic here
            pass

    # FIX: Corrected expander labels to use emojis, not broken icon codes.
    with st.expander("📂 Step 1: Initiation & Problem Description", expanded=True):
        st.markdown("##### **1.1 Identification**")
        col1, col2 = st.columns(2)
        data['capa_number'] = col1.text_input("CAPA Number", data.get('capa_number', ''))
        data['product_name'] = col1.text_input("Product Name/Model", data.get('product_name', st.session_state.get('target_sku', '')))
        data['date'] = col2.date_input("Initiation Date", data.get('date', date.today()))
        data['prepared_by'] = col2.text_input("Prepared By", data.get('prepared_by', ''))

    with st.expander("🔍 Step 2: Investigation & Root Cause Analysis"):
        st.markdown("##### **2.1 Risk Assessment**")
        r_col1, r_col2 = st.columns(2)
        data['risk_severity'] = r_col1.slider("Severity", 1, 5, data.get('risk_severity', 3))
        data['risk_probability'] = r_col2.slider("Probability", 1, 5, data.get('risk_probability', 3))

    with st.expander("🛠️ Step 3: Corrective & Preventive Action Plan"):
        data['corrective_action'] = st.text_area("Corrective Action(s)", data.get('corrective_action', ''))
        data['preventive_action'] = st.text_area("Preventive Action(s)", data.get('preventive_action', ''))

    with st.expander("✅ Step 4: Verification & Closure"):
        data['effectiveness_verification_plan'] = st.text_area("Verification Plan", data.get('effectiveness_verification_plan', ''))
        c_col1, c_col2 = st.columns(2)
        data['closed_by'] = c_col1.text_input("Closed By", data.get('closed_by', ''))
        data['closure_date'] = c_col2.date_input("Closure Date", data.get('closure_date', date.today()))

    st.session_state.capa_data = data
