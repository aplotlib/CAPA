# src/tabs/risk_safety.py

import streamlit as st
import pandas as pd

def display_risk_safety_tab():
    st.header("Risk & Safety Analysis Hub")
    if st.session_state.api_key_missing:
        st.error("AI features are disabled. Please configure your API key.")
        return

    # Initialize session state keys for FMEA if they don't exist
    if 'fmea_rows' not in st.session_state:
        st.session_state.fmea_rows = []

    # --- Tool 1: FMEA (NEW & IMPROVED UI) ---
    with st.container(border=True):
        st.subheader("Failure Mode and Effects Analysis (FMEA)")
        with st.expander("What is an FMEA?", expanded=False):
            st.markdown("""
            An FMEA is a proactive method to evaluate a process for potential failures. Use this tool to identify and prioritize risks.
            - **Severity (S):** Impact of the failure (1=Low, 10=High).
            - **Occurrence (O):** Likelihood of the failure (1=Low, 10=High).
            - **Detection (D):** How likely you are to detect the failure (1=High, 10=Low).
            **RPN = S × O × D**. Higher RPNs are higher priorities.
            """)

        st.markdown("##### Step 1: Manually Enter 1-3 Initial Failure Modes")
        with st.form("manual_fmea_form"):
            failure_mode = st.text_input("Potential Failure Mode")
            effect = st.text_area("Potential Effect(s)", height=100)
            cause = st.text_area("Potential Cause(s)", height=100)
            if st.form_submit_button("Add Failure Mode", use_container_width=True):
                if failure_mode:
                    st.session_state.fmea_rows.append({
                        "Potential Failure Mode": failure_mode,
                        "Potential Effect(s)": effect,
                        "Potential Cause(s)": cause,
                        "Severity": 5, "Occurrence": 5, "Detection": 5, "RPN": 125
                    })
                    st.rerun()
                else:
                    st.warning("Potential Failure Mode is a required field.")

        if st.session_state.fmea_rows:
            st.markdown("---")
            st.markdown("##### Current FMEA Entries")
            for i, row in enumerate(st.session_state.fmea_rows):
                with st.container(border=True):
                    c1, c2, c3 = st.columns(3)
                    row["Potential Failure Mode"] = c1.text_input("Failure Mode", value=row["Potential Failure Mode"], key=f"fm_{i}")
                    row["Potential Effect(s)"] = c2.text_area("Effect(s)", value=row["Potential Effect(s)"], key=f"eff_{i}", height=150)
                    row["Potential Cause(s)"] = c3.text_area("Cause(s)", value=row["Potential Cause(s)"], key=f"cause_{i}", height=150)
                    
                    sc1, sc2, sc3 = st.columns(3)
                    row["Severity"] = sc1.slider("Severity", 1, 10, int(row["Severity"]), key=f"s_{i}")
                    row["Occurrence"] = sc2.slider("Occurrence", 1, 10, int(row["Occurrence"]), key=f"o_{i}")
                    row["Detection"] = sc3.slider("Detection", 1, 10, int(row["Detection"]), key=f"d_{i}")
                    row["RPN"] = row["Severity"] * row["Occurrence"] * row["Detection"]
                    st.metric("Risk Priority Number (RPN)", row["RPN"])
            
            st.markdown("---")
            st.markdown("##### Step 2: Use AI to Expand Your Analysis")
            if st.button("🤖 Suggest Additional Failure Modes with AI", use_container_width=True, type="primary"):
                if st.session_state.get('analysis_results'):
                    with st.spinner("AI is brainstorming other risks..."):
                        insights = st.session_state.analysis_results.get('insights', 'High return rate observed.')
                        # FIX: Call the correct, existing method name
                        suggestions = st.session_state.fmea_generator.suggest_failure_modes(
                            insights, 
                            st.session_state.analysis_results, 
                            st.session_state.fmea_rows
                        )
                        for suggestion in suggestions:
                            suggestion.update({"Severity": 5, "Occurrence": 5, "Detection": 5, "RPN": 125})
                            st.session_state.fmea_rows.append(suggestion)
                        st.success("AI has added new failure modes for your review.")
                        st.rerun()
                else:
                    st.warning("Run an analysis on the dashboard first.")
        
        # Update fmea_data for export
        if st.session_state.fmea_rows:
            st.session_state.fmea_data = pd.DataFrame(st.session_state.fmea_rows)
    
    st.write("") 
    
    # --- Tool 2: Use-Related Risk Analysis (URRA) ---
    with st.container(border=True):
        st.subheader("Use-Related Risk Analysis (URRA) Generator")
        with st.form("urra_form"):
            st.info("Generates a URRA based on IEC 62366 to identify risks associated with product usability.")
            urra_product_name = st.text_input("Product Name", st.session_state.product_info['name'], key="urra_name")
            urra_product_desc = st.text_area("Product Description & Intended Use", value=st.session_state.product_info['ifu'], height=100, key="urra_desc")
            urra_user = st.text_input("Intended User Profile", placeholder="e.g., Elderly individuals with limited dexterity")
            
            use_environments = ["Home Healthcare Setting", "Hospital/Clinical Setting", "Long-Term Care Facility", "Outpatient Clinic", "Public Spaces/Transport", "Other (Specify)"]
            urra_env_selection = st.selectbox("Intended Use Environment", use_environments)

            if urra_env_selection == "Other (Specify)":
                urra_env = st.text_input("Please specify the use environment:", key="urra_env_other")
            else:
                urra_env = urra_env_selection

            if st.form_submit_button("Generate URRA", type="primary", use_container_width=True):
                if all([urra_product_name, urra_product_desc, urra_user, urra_env]):
                    with st.spinner("AI is generating the URRA..."):
                        st.session_state.urra = st.session_state.urra_generator.generate_urra(urra_product_name, urra_product_desc, urra_user, urra_env)
                else:
                    st.warning("Please fill in all fields to generate the URRA.")

        if st.session_state.get('urra'):
            st.markdown(st.session_state.urra)
