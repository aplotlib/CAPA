# src/tabs/risk_safety.py

import streamlit as st
import pandas as pd

def display_risk_safety_tab():
    """
    Displays the Risk & Safety Analysis Hub with updated tooltips.
    """
    st.header("⚠️ Risk & Safety Analysis Hub")
    if st.session_state.api_key_missing:
        st.warning("AI features are disabled (No API Key). You can still use manual tools.", icon="⚠️")

    if 'fmea_rows' not in st.session_state:
        st.session_state.fmea_rows = []

    # --- Tool 1: FMEA ---
    with st.container(border=True):
        st.subheader("Failure Mode and Effects Analysis (FMEA)")
        with st.expander("What is an FMEA?", expanded=False):
            st.markdown("""
            An FMEA is a proactive method to evaluate a process for potential problems before they happen.
            - **Severity (S):** Impact of the failure (1=Low, 10=High).
            - **Occurrence (O):** Likelihood of the failure (1=Low, 10=High).
            - **Detection (D):** How likely you are to detect the failure (1=High, 10=Low).
            **RPN = S × O × D**. Higher RPNs are higher priorities.
            """)
        
        if not st.session_state.fmea_rows:
            df = pd.DataFrame(columns=["Potential Failure Mode", "Potential Effect(s)", "Potential Cause(s)", "Severity", "Occurrence", "Detection", "RPN"])
        else:
            df = pd.DataFrame(st.session_state.fmea_rows)

        numeric_cols = ["Severity", "Occurrence", "Detection", "RPN"]
        for col in numeric_cols:
            if col not in df.columns:
                df[col] = 5 if col != "RPN" else 125
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(5).astype(int)

        st.markdown("##### FMEA Worksheet")
        st.caption("Double-click a cell to edit. RPN is calculated automatically.")
        
        # Updated width="stretch"
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            width="stretch",
            column_config={
                "Severity": st.column_config.NumberColumn(min_value=1, max_value=10, help="1 (Minor) to 10 (Hazardous)"),
                "Occurrence": st.column_config.NumberColumn(min_value=1, max_value=10, help="1 (Remote) to 10 (Frequent)"),
                "Detection": st.column_config.NumberColumn(min_value=1, max_value=10, help="1 (Certain Detection) to 10 (Undetectable)"),
                "RPN": st.column_config.NumberColumn(disabled=True, help="Risk Priority Number (S*O*D)"),
                "Potential Failure Mode": st.column_config.TextColumn(required=True, help="What could go wrong?"),
                "Potential Effect(s)": st.column_config.TextColumn(help="Consequence of the failure."),
                "Potential Cause(s)": st.column_config.TextColumn(help="Why would this happen?"),
            },
            key="fmea_editor"
        )

        if not edited_df.equals(df):
            edited_df['RPN'] = edited_df['Severity'] * edited_df['Occurrence'] * edited_df['Detection']
            st.session_state.fmea_rows = edited_df.to_dict('records')
            st.session_state.fmea_data = edited_df
            st.rerun()

        st.markdown("##### AI Assistance")
        # Updated width="stretch"
        if st.button("🤖 Suggest Additional Failure Modes with AI", width="stretch", type="primary", help="AI will brainstorm risks based on your product SKU."):
            if 'fmea_generator' in st.session_state and not st.session_state.api_key_missing:
                with st.spinner("AI is brainstorming other risks..."):
                    analysis_results = st.session_state.get('analysis_results')
                    insights = "High return rate observed."
                    if analysis_results:
                        insights = analysis_results.get('insights', insights)

                    suggestions = st.session_state.fmea_generator.suggest_failure_modes(
                        st.session_state.product_info.get('ifu', insights), 
                        analysis_results, 
                        st.session_state.fmea_rows
                    )
                    
                    new_rows = []
                    for s in suggestions:
                        s_dict = {
                            "Potential Failure Mode": s.get("Potential Failure Mode", "New Mode"),
                            "Potential Effect(s)": s.get("Potential Effect(s)", ""),
                            "Potential Cause(s)": s.get("Potential Cause(s)", ""),
                            "Severity": 5, "Occurrence": 5, "Detection": 5, "RPN": 125
                        }
                        new_rows.append(s_dict)
                    
                    st.session_state.fmea_rows.extend(new_rows)
                    st.success(f"AI added {len(new_rows)} new failure modes.")
                    st.rerun()
            elif st.session_state.api_key_missing:
                st.error("Please provide an API Key to use AI features.")
    
    st.write("") 
    
    # --- Tool 2: URRA ---
    with st.container(border=True):
        st.subheader("Use-Related Risk Analysis (URRA) Generator")
        with st.form("urra_form"):
            st.info("Generates a URRA based on IEC 62366 to identify risks associated with product usability.")
            product_info = st.session_state.product_info
            urra_product_name = st.text_input("Product Name", product_info.get('name', ''), key="urra_name", help="Name of the device.")
            urra_product_desc = st.text_area("Product Description & Intended Use", value=product_info.get('ifu', ''), height=100, key="urra_desc", help="What does it do and who is it for?")
            urra_user = st.text_input("Intended User Profile", placeholder="e.g., Elderly individuals with limited dexterity", key="urra_user", help="Who is operating the device?")
            
            use_environments_options = ["Home Healthcare Setting", "Hospital/Clinical Setting", "Long-Term Care Facility", "Outpatient Clinic", "Public Spaces/Transport", "Other"]
            urra_env_selection = st.multiselect("Intended Use Environment(s)", use_environments_options, key="urra_env_multi", help="Where will it be used?")

            urra_env_other = ""
            if "Other" in urra_env_selection:
                urra_env_other = st.text_input("Please specify the 'Other' environment:", key="urra_env_other_text")

            # Updated width="stretch"
            if st.form_submit_button("Generate URRA", type="primary", width="stretch", help="Generate a usability risk table."):
                if 'urra_generator' in st.session_state and not st.session_state.api_key_missing:
                    final_environments = list(urra_env_selection)
                    if "Other" in final_environments:
                        final_environments.remove("Other")
                        if urra_env_other:
                            final_environments.append(urra_env_other)
                    
                    env_string = ", ".join(final_environments)

                    if all([urra_product_name, urra_product_desc, urra_user, env_string]):
                        with st.spinner("AI is generating the URRA..."):
                            st.session_state.urra = st.session_state.urra_generator.generate_urra(urra_product_name, urra_product_desc, urra_user, env_string)
                            st.rerun()
                    else:
                        st.warning("Please fill in all fields to generate the URRA.")

        if st.session_state.get('urra'):
            st.markdown("### Use-Related Risk Analysis Results")
            st.markdown(st.session_state.urra, unsafe_allow_html=True)
