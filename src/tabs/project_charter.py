# src/tabs/project_charter.py

import streamlit as st

def display_project_charter_tab():
    """
    Displays the workflow for generating a new medical device project charter.
    """
    st.header("📑 Project Charter Generator")
    st.info(
        "Define the scope, goals, and regulatory strategy for your new product. "
        "The AI will help generate a formal project charter document."
    )

    with st.form("project_charter_form"):
        st.subheader("1. Project Overview & Business Case")
        project_name = st.text_input("Project Name / Device Name", st.session_state.product_info.get('name', ''))
        problem_statement = st.text_area("Problem Statement", placeholder="What problem does this device solve?")
        project_goal = st.text_area("Project Goal", placeholder="What is the primary business or clinical goal?")
        scope = st.text_area("Project Scope", placeholder="What are the key deliverables and boundaries of this project?")

        st.subheader("2. Regulatory & Quality Strategy")
        device_classification = st.selectbox(
            "Device Classification (FDA)",
            ["Class I", "Class II", "Class III", "Unsure"]
        )
        # Pre-populate standards based on classification
        standards_map = {
            "Class I": ["ISO 13485", "FDA 21 CFR 820"],
            "Class II": ["ISO 13485", "FDA 21 CFR 820.30 (Design Controls)", "ISO 14971 (Risk Management)"],
            "Class III": ["ISO 13485", "FDA 21 CFR 820.30 (Design Controls)", "ISO 14971 (Risk Management)", "PMA Submission Requirements"]
        }
        suggested_standards = standards_map.get(device_classification, [])
        applicable_standards = st.multiselect(
            "Applicable Standards & Regulations",
            options=["ISO 13485", "FDA 21 CFR 820", "FDA 21 CFR 820.30 (Design Controls)", "ISO 14971 (Risk Management)", "IEC 62366 (Usability)", "IEC 60601 (Electrical Safety)", "PMA Submission Requirements"],
            default=suggested_standards
        )

        st.subheader("3. Key Stakeholders")
        stakeholders = st.text_input("List Key Stakeholders", placeholder="e.g., Project Manager, Lead Engineer, Regulatory Affairs Specialist")

        submitted = st.form_submit_button("Generate Charter Document", type="primary", use_container_width=True)

        if submitted:
            charter_data = {
                "project_name": project_name,
                "problem_statement": problem_statement,
                "project_goal": project_goal,
                "scope": scope,
                "device_classification": device_classification,
                "applicable_standards": applicable_standards,
                "stakeholders": stakeholders
            }
            # Store data in session state to be picked up by the document generator
            st.session_state.project_charter_data = charter_data
            st.success("Charter data captured! Proceed to the 'Exports' tab to download the document.")
