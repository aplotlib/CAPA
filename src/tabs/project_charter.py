import streamlit as st

def display_project_charter_tab():
    """
    Displays the workflow for generating a new medical device project charter.
    """
    st.header("📑 Project Charter Generator")
    st.info(
        "Define the scope, goals, and regulatory strategy for your new product. "
        "This tool will generate a formal project charter document."
    )

    if 'project_charter_data' not in st.session_state:
        st.session_state.project_charter_data = {}

    data = st.session_state.project_charter_data

    with st.form("project_charter_form"):
        st.subheader("1. Project Overview & Business Case")
        data['project_name'] = st.text_input("Project Name / Device Name", 
                                             value=data.get('project_name', st.session_state.product_info.get('name', '')))
        data['problem_statement'] = st.text_area("Problem Statement", 
                                                 value=data.get('problem_statement', ''),
                                                 placeholder="What problem does this device solve?")
        data['project_goal'] = st.text_area("Project Goal", 
                                            value=data.get('project_goal', ''),
                                            placeholder="What is the primary business or clinical goal?")
        data['scope'] = st.text_area("Project Scope", 
                                     value=data.get('scope', ''),
                                     placeholder="What are the key deliverables and boundaries of this project?")

        st.subheader("2. Regulatory & Quality Strategy")
        device_classification = st.selectbox(
            "Device Classification (FDA)",
            ["Class I", "Class II", "Class III", "Unsure"],
            index=["Class I", "Class II", "Class III", "Unsure"].index(data.get('device_classification', 'Class II'))
        )
        data['device_classification'] = device_classification
        
        standards_map = {
            "Class I": ["ISO 13485", "FDA 21 CFR 820"],
            "Class II": ["ISO 13485", "FDA 21 CFR 820.30 (Design Controls)", "ISO 14971 (Risk Management)"],
            "Class III": ["ISO 13485", "FDA 21 CFR 820.30 (Design Controls)", "ISO 14971 (Risk Management)", "PMA Submission Requirements"]
        }
        suggested_standards = standards_map.get(device_classification, [])
        data['applicable_standards'] = st.multiselect(
            "Applicable Standards & Regulations",
            options=["ISO 13485", "FDA 21 CFR 820", "FDA 21 CFR 820.30 (Design Controls)", "ISO 14971 (Risk Management)", "IEC 62366 (Usability)", "IEC 60601 (Electrical Safety)", "PMA Submission Requirements"],
            default=data.get('applicable_standards', suggested_standards)
        )

        st.subheader("3. Key Stakeholders")
        data['stakeholders'] = st.text_input("List Key Stakeholders", 
                                             value=data.get('stakeholders', ''),
                                             placeholder="e.g., Project Manager, Lead Engineer, Regulatory Affairs Specialist")

        submitted = st.form_submit_button("Save Charter Data", type="primary", use_container_width=True)

        if submitted:
            st.session_state.project_charter_data = data
            st.success("✅ Charter data saved! You can now download the document from the 'Exports' tab.")
