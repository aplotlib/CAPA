# src/tabs/human_factors.py

import streamlit as st

def display_human_factors_tab():
    """
    Displays the Human Factors and Usability Engineering form with an improved, AI-first workflow.
    """
    st.header("👥 Human Factors & Usability Engineering")
    st.info("This AI-powered workflow helps you generate a comprehensive HFE report draft based on a few key questions.")

    if 'human_factors_data' not in st.session_state:
        st.session_state.human_factors_data = {}
    data = st.session_state.human_factors_data
    
    # --- Context Display ---
    # Explicitly confirm the data flow from R&D/Dashboard
    active_skus = st.session_state.product_info.get('sku', 'None')
    active_name = st.session_state.product_info.get('name', 'None')
    
    st.caption(f"**Active Context from R&D:** {active_name} | **SKUs:** {active_skus}")

    # --- NEW: AI-first workflow ---
    with st.container(border=True):
        st.subheader("Step 1: Answer Key Questions for AI Draft")
        st.markdown("We will use the R&D information uploaded in the Dashboard to help contextually draft this report.")
        
        with st.form("hf_questions_form"):
            q1 = st.text_area(
                "**1. Who is the primary user of this device, and in what environment will they use it?**",
                placeholder="e.g., An elderly person with arthritis, using it in their home without assistance.",
                key="hf_q1"
            )
            q2 = st.text_area(
                "**2. What are the 1-3 most critical steps a user must perform for the device to work correctly and safely?**",
                placeholder="e.g., 1. Correctly attaching the cuff. 2. Pressing the start button once. 3. Reading the final measurement.",
                key="hf_q2"
            )
            q3 = st.text_area(
                "**3. What are the most severe potential harms if a user makes a mistake during one of these critical steps?**",
                placeholder="e.g., Incorrect attachment leads to a misdiagnosis of hypertension, resulting in improper medical treatment.",
                key="hf_q3"
            )
            
            submitted = st.form_submit_button("✍️ Generate Full HFE Report with AI", width="stretch", type="primary")
            if submitted:
                if st.session_state.api_key_missing:
                    st.error("AI features are disabled. Please configure your API key.")
                elif q1 and q2 and q3:
                    with st.spinner("AI is drafting the HFE report..."):
                        user_answers = {"user_profile": q1, "critical_tasks": q2, "potential_harms": q3}
                        suggestions = st.session_state.ai_hf_helper.generate_hf_report_from_answers(
                            st.session_state.product_info['name'],
                            st.session_state.product_info['ifu'],
                            user_answers
                        )
                        if suggestions and "error" not in suggestions:
                            st.session_state.human_factors_data = suggestions
                            st.success("✅ AI has generated the HFE report sections below for your review.")
                        else:
                            st.error(f"Could not retrieve AI suggestions: {suggestions.get('error', 'Unknown error')}")
                else:
                    st.warning("Please answer all three questions to generate the report.")
    
    st.divider()

    # --- HFE Report Form Sections (now for review/editing) ---
    if data:
        st.subheader("Step 2: Review and Edit the AI-Generated Report")
        with st.expander("Section 1: Conclusion", expanded=True):
            data['conclusion_statement'] = st.text_area("**Conclusion Statement**", value=data.get('conclusion_statement', ''), height=150, key="hf_conclusion")
        with st.expander("Section 2: Descriptions"):
            data['descriptions'] = st.text_area("**Descriptions of Intended Users, Uses, and Environments**", value=data.get('descriptions', ''), height=200, key="hf_descriptions")
        with st.expander("Section 3: Device User Interface"):
            data['device_interface'] = st.text_area("**Device User Interface**", value=data.get('device_interface', ''), height=200, key="hf_interface")
        with st.expander("Section 4: Summary of Known Use Problems"):
            data['known_problems'] = st.text_area("**Known Use Problems**", value=data.get('known_problems', ''), height=150, key="hf_problems")
        with st.expander("Section 5: Analysis of Hazards and Risks"):
            data['hazards_analysis'] = st.text_area("**Hazards and Risks Analysis**", value=data.get('hazards_analysis', ''), height=200, key="hf_hazards")
        with st.expander("Section 6: Preliminary Analyses"):
            data['preliminary_analyses'] = st.text_area("**Summary of Preliminary Analyses and Evaluations**", value=data.get('preliminary_analyses', ''), height=200, key="hf_prelim")
        with st.expander("Section 7: Critical Tasks"):
            data['critical_tasks'] = st.text_area("**Description and Categorization of Critical Tasks**", value=data.get('critical_tasks', ''), height=200, key="hf_tasks")
        with st.expander("Section 8: Validation Testing"):
            else:
        st.info("Answer the questions above to generate an AI-assisted draft of your Human Factors report.")
