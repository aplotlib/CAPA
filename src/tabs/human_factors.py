# src/tabs/human_factors.py (MODIFIED)

import streamlit as st

def display_human_factors_tab():
    """
    Displays the Human Factors and Usability Engineering form with AI assistance.
    """
    st.header("Human Factors & Usability Engineering")
    st.info("This workflow is based on the FDA's guidance for Human Factors and Usability Engineering reports.")

    if 'human_factors_data' not in st.session_state:
        st.session_state.human_factors_data = {}
    data = st.session_state.human_factors_data

    # --- AI Suggestions Button ---
    if not st.session_state.get('api_key_missing', True):
        st.subheader("AI Assistance")
        product_name = st.text_input("Product Name for AI Analysis", st.session_state.get('target_sku', ''))
        product_desc = st.text_area("Brief Product Description for AI", height=100, placeholder="e.g., A handheld digital thermometer for home use.")
        
        if st.button("🤖 Generate AI Suggestions for HFE Report", use_container_width=True):
            if product_name and product_desc:
                with st.spinner("AI is generating HFE suggestions..."):
                    suggestions = st.session_state.ai_hf_helper.generate_hf_suggestions(product_name, product_desc)
                    if suggestions and "error" not in suggestions:
                        # Populate form fields with AI suggestions
                        for key, value in suggestions.items():
                            data[key] = value
                        st.success("✅ AI suggestions have been populated below.")
                    else:
                        st.error("Could not retrieve AI suggestions. Please try again.")
            else:
                st.warning("Please provide a product name and description for the AI.")
    
    st.divider()

    with st.expander("Section 1: Conclusion", expanded=True):
        data['conclusion_statement'] = st.text_area(
            "Conclusion Statement",
            value=data.get('conclusion_statement', ''),
            height=150,
            help="Provide a conclusion statement that your medical device has been found to be safe and effective for the intended users, uses, and use environments."
        )

    with st.expander("Section 2: Descriptions of Intended Users, Uses, and Environments"):
        data['descriptions'] = st.text_area(
            "Descriptions",
            value=data.get('descriptions', ''),
            height=200,
            help="Describe the intended user population(s), intended use and operational contexts, use environments, and training intended for users."
        )

    with st.expander("Section 3: Description of Device User Interface"):
        data['device_interface'] = st.text_area(
            "Device User Interface",
            value=data.get('device_interface', ''),
            height=200,
            help="Provide a description of the device's user interface, including graphical representations and an overview of the operational sequence."
        )

    with st.expander("Section 4: Summary of Known Use Problems"):
        data['known_problems'] = st.text_area(
            "Known Use Problems",
            value=data.get('known_problems', ''),
            height=150,
            help="Summarize any known use problems with previous models of the device or similar devices."
        )

    with st.expander("Section 5: Analysis of Hazards and Risks"):
        data['hazards_analysis'] = st.text_area(
            "Hazards and Risks Analysis",
            value=data.get('hazards_analysis', ''),
            height=200,
            help="Analyze potential use errors, the potential harm and severity of harm, and the risk management measures implemented."
        )

    with st.expander("Section 6: Summary of Preliminary Analyses and Evaluations"):
        data['preliminary_analyses'] = st.text_area(
            "Preliminary Analyses and Evaluations",
            value=data.get('preliminary_analyses', ''),
            height=200,
            help="Summarize the evaluation methods used, key results, design modifications, and key findings that informed the validation test protocol."
        )

    with st.expander("Section 7: Description and Categorization of Critical Tasks"):
        data['critical_tasks'] = st.text_area(
            "Critical Tasks",
            value=data.get('critical_tasks', ''),
            height=200,
            help="Describe the process used to identify critical tasks, list and describe the critical tasks, and categorize them by severity of potential harm."
        )

    with st.expander("Section 8: Details of Human Factors Validation Testing"):
        data['validation_testing'] = st.text_area(
            "Validation Testing",
            value=data.get('validation_testing', ''),
            height=300,
            help="Provide details of the human factors validation testing, including the rationale for the test type, the test environment, the number and type of participants, the training provided, and the test results."
        )
