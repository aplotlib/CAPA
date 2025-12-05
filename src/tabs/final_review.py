# src/tabs/final_review.py

import streamlit as st

def display_final_review_tab():
    """
    Displays the Final Review tab, which uses AI to synthesize all available
    information into a single executive summary.
    """
    st.header("🔍 Final Review & Synthesis")
    st.info(
        "This final step uses AI to perform a holistic review of all the data and analyses "
        "generated across the application. It looks for connections, discrepancies, and provides "
        "a high-level executive summary suitable for stakeholders."
    )

    if st.session_state.api_key_missing:
        st.error("AI features are disabled. Please configure your API key to use this feature.")
        return

    with st.container(border=True):
        st.subheader("Generate Holistic Project Summary")
        
        # Check if there is any data to analyze
        has_data = any([
            st.session_state.get('capa_data'),
            st.session_state.get('fmea_data') is not None and not st.session_state.get('fmea_data').empty,
            st.session_state.get('urra'),
            st.session_state.get('human_factors_data'),
            st.session_state.get('product_dev_data'),
            st.session_state.get('pre_mortem_summary')
        ])

        if not has_data:
            st.warning("There is no data to analyze yet. Please complete sections in other tabs first.")
            return

        if st.button("🤖 Generate AI Executive Summary & Analysis", type="primary", width="stretch"):
            with st.spinner("AI is performing a holistic analysis of the entire project..."):
                prompt = (
                    "You are a Director of Quality and Product Development. Synthesize all the provided context "
                    "from a Quality Management application into a single, cohesive executive summary. Your summary should:\n"
                    "1. Provide a high-level overview of the product and the project's objective.\n"
                    "2. Summarize the key findings from the risk analyses (FMEA, URRA, Pre-Mortem).\n"
                    "3. If CAPA data is present, connect the CAPA's root cause to the identified risks.\n"
                    "4. Highlight any potential contradictions or discrepancies between different analyses (e.g., a risk identified in the FMEA that is not addressed in the design validation plan).\n"
                    "5. Conclude with a clear, actionable 'Final Recommendations' section on the next steps for the project (e.g., proceed to launch, conduct further testing, revise design based on findings)."
                )
                response = st.session_state.ai_context_helper.generate_response(prompt)
                st.session_state.final_review_summary = response

    if st.session_state.get('final_review_summary'):
        st.subheader("AI-Generated Project Synthesis")
        st.markdown(st.session_state.final_review_summary)
