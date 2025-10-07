# src/tabs/project_charter.py

import streamlit as st

def display_project_charter_tab():
    """
    Displays an AI-powered workflow for generating a new medical device project charter.
    """
    st.header("Project Charter Generator")
    st.info(
        "Define the core concept of your new product, and let the AI generate a formal project charter draft. "
        "You can then review, edit, and finalize the document."
    )

    if 'project_charter_data' not in st.session_state:
        st.session_state.project_charter_data = {}
    data = st.session_state.project_charter_data

    # --- Step 1: Provide Key Inputs for AI ---
    with st.container(border=True):
        st.subheader("Step 1: Provide Initial Project Details")
        with st.form("ai_charter_form"):
            product_name = st.text_input("Project Name / Device Name", 
                                         value=st.session_state.product_info.get('name', ''))
            problem_statement = st.text_area("What clinical or user problem does this device solve?",
                                             placeholder="e.g., Post-operative patients lack a simple way to track their range of motion at home, leading to slower recovery times.")
            target_user = st.text_input("Who is the primary target user?",
                                        placeholder="e.g., Physical therapists and post-operative orthopedic patients.")
            
            submitted = st.form_submit_button("Generate AI Charter Draft", type="primary", use_container_width=True)
            if submitted:
                if st.session_state.api_key_missing:
                    st.error("AI features are disabled. Please configure your API key.")
                elif all([product_name, problem_statement, target_user]):
                    with st.spinner("AI is drafting the project charter..."):
                        draft = st.session_state.ai_charter_helper.generate_charter_draft(
                            product_name, problem_statement, target_user
                        )
                        if draft and "error" not in draft:
                            # Populate session state with the AI draft
                            st.session_state.project_charter_data = draft
                            # Also update the project name from the input field
                            st.session_state.project_charter_data['project_name'] = product_name
                            st.success("AI draft generated! Review and edit the sections below.")
                        else:
                            st.error(f"Could not generate draft: {draft.get('error', 'Unknown error')}")
                else:
                    st.warning("Please fill in all fields to generate the charter draft.")

    # --- Step 2: Review and Edit the AI-Generated Draft ---
    if data:
        st.divider()
        st.subheader("Step 2: Review, Edit, and Finalize Charter")
        with st.form("project_charter_review_form"):
            with st.expander("1. Project Overview & Business Case", expanded=True):
                data['project_name'] = st.text_input("Project Name", value=data.get('project_name', ''))
                data['problem_statement'] = st.text_area("Problem Statement", value=data.get('problem_statement', ''), height=150)
                data['project_goal'] = st.text_area("Project Goal", value=data.get('project_goal', ''), height=150)
                data['scope'] = st.text_area("Project Scope", value=data.get('scope', ''), height=200)

            with st.expander("2. Regulatory & Quality Strategy", expanded=True):
                data['device_classification'] = st.selectbox(
                    "Device Classification (FDA)",
                    ["Class I", "Class II", "Class III", "Unsure"],
                    index=["Class I", "Class II", "Class III", "Unsure"].index(data.get('device_classification', 'Unsure'))
                )
                data['applicable_standards'] = st.multiselect(
                    "Applicable Standards & Regulations",
                    options=["ISO 13485", "FDA 21 CFR 820", "FDA 21 CFR 820.30 (Design Controls)", "ISO 14971 (Risk Management)", "IEC 62366 (Usability)", "IEC 60601 (Electrical Safety)", "PMA Submission Requirements"],
                    default=data.get('applicable_standards', [])
                )

            with st.expander("3. Key Stakeholders", expanded=True):
                data['stakeholders'] = st.text_input("Key Stakeholders", value=data.get('stakeholders', ''))

            if st.form_submit_button("Save Final Charter Data", use_container_width=True):
                st.session_state.project_charter_data = data
                st.success("Charter data saved! You can now download the document from the 'Exports' tab.")
