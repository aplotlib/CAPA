# src/tabs/risk_safety.py

import streamlit as st
import pandas as pd

def display_risk_safety_tab():
    """
    Displays the Risk & Safety Analysis Hub, including FMEA and URRA tools.
    """
    st.header("⚠️ Risk & Safety Analysis Hub")
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
            An FMEA is a proactive method to evaluate a process for potential problems before they happen. Use this tool to identify and prioritize risks.
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
                    row["Severity"] = sc1.slider("Severity", 1, 10, int(row.get("Severity", 5)), key=f"s_{i}")
                    row["Occurrence"] = sc2.slider("Occurrence", 1, 10, int(row.get("Occurrence", 5)), key=f"o_{i}")
                    row["Detection"] = sc3.slider("Detection", 1, 10, int(row.get("Detection", 5)), key=f"d_{i}")
                    row["RPN"] = row["Severity"] * row["Occurrence"] * row["Detection"]
                    st.metric("Risk Priority Number (RPN)", row["RPN"])
            
            st.markdown("---")
            st.markdown("##### Step 2: Use AI to Expand Your Analysis")
            if st.button("🤖 Suggest Additional Failure Modes with AI", use_container_width=True, type="primary"):
                if 'fmea_generator' in st.session_state:
                    with st.spinner("AI is brainstorming other risks..."):
                        insights = st.session_state.get('analysis_results', {}).get('insights', 'High return rate observed.')
                        suggestions = st.session_state.fmea_generator.suggest_failure_modes(
                            st.session_state.product_info.get('ifu', insights), 
                            st.session_state.get('analysis_results'), 
                            st.session_state.fmea_rows
                        )
                        for suggestion in suggestions:
                            suggestion.update({"Severity": 5, "Occurrence": 5, "Detection": 5, "RPN": 125})
                            st.session_state.fmea_rows.append(suggestion)
                        st.success("AI has added new failure modes for your review.")
                        st.rerun()
                else:
                    st.warning("AI features are not available. Check your API key.")
        
        # Update fmea_data for export
        if st.session_state.fmea_rows:
            st.session_state.fmea_data = pd.DataFrame(st.session_state.fmea_rows)
    
    st.write("") 
    
    # --- Tool 2: Use-Related Risk Analysis (URRA) ---
    with st.container(border=True):
        st.subheader("Use-Related Risk Analysis (URRA) Generator")
        with st.form("urra_form"):
            st.info("Generates a URRA based on IEC 62366 to identify risks associated with product usability.")
            product_info = st.session_state.product_info
            urra_product_name = st.text_input("Product Name", product_info.get('name', ''), key="urra_name")
            urra_product_desc = st.text_area("Product Description & Intended Use", value=product_info.get('ifu', ''), height=100, key="urra_desc")
            urra_user = st.text_input("Intended User Profile", placeholder="e.g., Elderly individuals with limited dexterity", key="urra_user")
            
            use_environments_options = ["Home Healthcare Setting", "Hospital/Clinical Setting", "Long-Term Care Facility", "Outpatient Clinic", "Public Spaces/Transport", "Other"]
            urra_env_selection = st.multiselect("Intended Use Environment(s)", use_environments_options, key="urra_env_multi")

            urra_env_other = ""
            if "Other" in urra_env_selection:
                urra_env_other = st.text_input("Please specify the 'Other' environment:", key="urra_env_other_text")

            if st.form_submit_button("Generate URRA", type="primary", use_container_width=True):
                if 'urra_generator' in st.session_state:
                    final_environments = list(urra_env_selection)
                    if "Other" in final_environments:
                        final_environments.remove("Other")
                        if urra_env_other:
                            final_environments.append(urra_env_other)
                    
                    env_string = ", ".join(final_environments)

                    if all([urra_product_name, urra_product_desc, urra_user, env_string]):
                        with st.spinner("AI is generating the URRA..."):
                            st.session_state.urra = st.session_state.urra_generator.generate_urra(urra_product_name, urra_product_desc, urra_user, env_string)
                    else:
                        st.warning("Please fill in all fields to generate the URRA.")
                else:
                    st.error("URRA Generator is not available. Check API key.")

        if st.session_state.get('urra'):
            st.markdown("### Use-Related Risk Analysis Results")
            st.markdown(st.session_state.urra, unsafe_allow_html=True)
