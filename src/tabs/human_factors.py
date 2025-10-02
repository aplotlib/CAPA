# src/tabs/human_factors.py

import streamlit as st

def display_human_factors_tab():
    """
    Displays the Human Factors and Usability Engineering form with AI assistance.
    """
    st.header("Human Factors & Usability Engineering")
    st.info("This workflow is based on the FDA's guidance for Human Factors and Usability Engineering reports, enhanced with AI assistance.")

    if 'human_factors_data' not in st.session_state:
        st.session_state.human_factors_data = {}
    data = st.session_state.human_factors_data

    # --- AI Assistance Section ---
    with st.container(border=True):
        st.subheader("🤖 AI Assistance")
        st.markdown("Provide some basic product details to get AI-generated suggestions for the sections below.")
        
        product_name = st.session_state.product_info['name']
        product_desc = st.session_state.product_info['ifu']
        
        if st.button("✍️ Generate AI Suggestions for HFE Report", use_container_width=True, type="primary"):
            if product_name and product_desc:
                with st.spinner("AI is generating HFE suggestions..."):
                    suggestions = st.session_state.ai_hf_helper.generate_hf_suggestions(product_name, product_desc)
                    if suggestions and "error" not in suggestions:
                        for key, value in suggestions.items():
                            data[key] = value
                        st.success("✅ AI suggestions have been populated in the form below.")
                    else:
                        st.error(f"Could not retrieve AI suggestions: {suggestions.get('error', 'Unknown error')}")
            else:
                st.warning("Please provide a product name and description for the AI.")
    
    st.divider()

    # --- HFE Report Form Sections ---
    st.subheader("HFE Report Sections")

    with st.expander("Section 1: Conclusion", expanded=True, icon="🏁"):
        data['conclusion_statement'] = st.text_area(
            "**Conclusion Statement**",
            value=data.get('conclusion_statement', ''),
            height=150,
            help="Provide a conclusion statement that your medical device has been found to be safe and effective for the intended users, uses, and use environments."
        )

    with st.expander("Section 2: Descriptions", icon="👥"):
        data['descriptions'] = st.text_area(
            "**Descriptions of Intended Users, Uses, and Environments**",
            value=data.get('descriptions', ''),
            height=200,
            help="Describe the intended user population(s), intended use and operational contexts, use environments, and training intended for users."
        )

    with st.expander("Section 3: Device User Interface", icon="📱"):
        data['device_interface'] = st.text_area(
            "**Device User Interface**",
            value=data.get('device_interface', ''),
            height=200,
            help="Provide a description of the device's user interface, including graphical representations and an overview of the operational sequence."
        )

    with st.expander("Section 4: Summary of Known Use Problems", icon="❗"):
        data['known_problems'] = st.text_area(
            "**Known Use Problems**",
            value=data.get('known_problems', ''),
            height=150,
            help="Summarize any known use problems with previous models of the device or similar devices."
        )

    with st.expander("Section 5: Analysis of Hazards and Risks", icon="⚠️"):
        data['hazards_analysis'] = st.text_area(
            "**Hazards and Risks Analysis**",
            value=data.get('hazards_analysis', ''),
            height=200,
            help="Analyze potential use errors, the potential harm and severity of harm, and the risk management measures implemented."
        )

    with st.expander("Section 6: Preliminary Analyses", icon="🧪"):
        data['preliminary_analyses'] = st.text_area(
            "**Summary of Preliminary Analyses and Evaluations**",
            value=data.get('preliminary_analyses', ''),
            height=200,
            help="Summarize the evaluation methods used, key results, design modifications, and key findings that informed the validation test protocol."
        )

    with st.expander("Section 7: Critical Tasks", icon="🎯"):
        data['critical_tasks'] = st.text_area(
            "**Description and Categorization of Critical Tasks**",
            value=data.get('critical_tasks', ''),
            height=200,
            help="Describe the process used to identify critical tasks, list and describe the critical tasks, and categorize them by severity of potential harm."
        )

    with st.expander("Section 8: Validation Testing", icon="📋"):
        data['validation_testing'] = st.text_area(
            "**Details of Human Factors Validation Testing**",
            value=data.get('validation_testing', ''),
            height=300,
            help="Provide details of the human factors validation testing, including the rationale for the test type, the test environment, the number and type of participants, the training provided, and the test results."
        )
