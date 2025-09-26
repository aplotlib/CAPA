# src/tabs/risk_safety.py

import streamlit as st
import pandas as pd

def display_risk_safety_tab():
    st.header("Risk & Safety Analysis Hub")
    if st.session_state.api_key_missing:
        st.error("AI features are disabled. Please configure your API key.")
        return

    # --- Tool 1: FMEA ---
    with st.container(border=True):
        st.subheader("Failure Mode and Effects Analysis (FMEA)")
        with st.expander("What is an FMEA?"):
            st.markdown("""
            An FMEA is a proactive method to evaluate a process for potential failures and their impacts. Use this tool to identify and prioritize risks based on Severity, Occurrence, and Detection.
            - **Severity (S):** Impact of the failure (1=Low, 5=High).
            - **Occurrence (O):** Likelihood of the failure (1=Low, 5=High).
            - **Detection (D):** How likely you are to detect the failure (1=High, 5=Low).
            **RPN = S × O × D**. Higher RPNs are higher priorities.
            """)

        c1, c2 = st.columns(2)
        if c1.button("Suggest Failure Modes with AI", width='stretch', key="fmea_ai"):
            if st.session_state.analysis_results:
                with st.spinner("AI is suggesting failure modes..."):
                    insights = st.session_state.analysis_results.get('insights', 'High return rate observed.')
                    suggestions = st.session_state.fmea_generator.suggest_failure_modes(insights, st.session_state.analysis_results)
                    df = pd.DataFrame(suggestions)
                    # Ensure score columns exist with default values
                    for col in ['Severity', 'Occurrence', 'Detection']:
                        if col not in df.columns:
                            df[col] = 1
                    st.session_state.fmea_data = df
            else:
                st.warning("Run an analysis on the dashboard first.")
        
        if c2.button("Add Manual FMEA Row", width='stretch', key="fmea_add"):
            new_row = pd.DataFrame([{"Potential Failure Mode": "", "Potential Effect(s)": "", "Severity": 1, "Potential Cause(s)": "", "Occurrence": 1, "Current Controls": "", "Detection": 1, "RPN": 1}])
            st.session_state.fmea_data = pd.concat([st.session_state.fmea_data, new_row], ignore_index=True)

        if 'fmea_data' in st.session_state and not st.session_state.fmea_data.empty:
            edited_df = st.data_editor(st.session_state.fmea_data, column_config={
                    "Severity": st.column_config.SelectboxColumn("S", options=list(range(1, 6)), required=True),
                    "Occurrence": st.column_config.SelectboxColumn("O", options=list(range(1, 6)), required=True),
                    "Detection": st.column_config.SelectboxColumn("D", options=list(range(1, 6)), required=True),
                }, num_rows="dynamic", key="fmea_editor")
            
            edited_df['RPN'] = (
                pd.to_numeric(edited_df['Severity'], errors='coerce').fillna(1) *
                pd.to_numeric(edited_df['Occurrence'], errors='coerce').fillna(1) *
                pd.to_numeric(edited_df['Detection'], errors='coerce').fillna(1)
            ).astype(int)
            st.session_state.fmea_data = edited_df
    
    st.write("") 
    
    # --- Tool 2: ISO 14971 Risk Assessment ---
    with st.container(border=True):
        st.subheader("ISO 14971 Risk Assessment Generator")
        with st.form("risk_assessment_form"):
            st.info("Generates a formal risk assessment for a medical device according to ISO 14971.")
            ra_product_name = st.text_input("Product Name", st.session_state.target_sku)
            ra_product_desc = st.text_area("Product Description & Intended Use", height=100)
            if st.form_submit_button("Generate Risk Assessment", type="primary", width='stretch'):
                if ra_product_name and ra_product_desc:
                    with st.spinner("AI is generating the ISO 14971 assessment..."):
                        st.session_state.risk_assessment = st.session_state.risk_assessment_generator.generate_assessment(ra_product_name, st.session_state.target_sku, ra_product_desc)
                else:
                    st.warning("Please provide a product name and description.")
        
        if st.session_state.get('risk_assessment'):
            st.markdown(st.session_state.risk_assessment)

    st.write("") 

    # --- Tool 3: Use-Related Risk Analysis (URRA) ---
    with st.container(border=True):
        st.subheader("Use-Related Risk Analysis (URRA) Generator")
        with st.form("urra_form"):
            st.info("Generates a URRA based on IEC 62366 to identify risks associated with product usability.")
            urra_product_name = st.text_input("Product Name", st.session_state.target_sku, key="urra_name")
            urra_product_desc = st.text_area("Product Description & Intended Use", height=100, key="urra_desc")
            urra_user = st.text_input("Intended User Profile", placeholder="e.g., Elderly individuals with limited dexterity")
            urra_env = st.text_input("Intended Use Environment", placeholder="e.g., Home healthcare setting")
            if st.form_submit_button("Generate URRA", type="primary", width='stretch'):
                if urra_product_name and urra_product_desc and urra_user and urra_env:
                    with st.spinner("AI is generating the URRA..."):
                        st.session_state.urra = st.session_state.urra_generator.generate_urra(urra_product_name, urra_product_desc, urra_user, urra_env)
                else:
                    st.warning("Please fill in all fields to generate the URRA.")

        if st.session_state.get('urra'):
            st.markdown(st.session_state.urra)
