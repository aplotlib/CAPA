# src/tabs/compliance.py

import streamlit as st

def display_compliance_tab():
    st.header("Compliance Center")
    if st.session_state.api_key_missing:
        st.error("AI features are disabled.")
        return

    col1, col2 = st.columns(2)
    with col1, st.container(border=True):
        st.subheader("Medical Device Classification")
        with st.form("classification_form"):
            device_desc = st.text_area("Device's intended use:", height=150, placeholder="e.g., A foam cushion for comfort in a wheelchair.")
            if st.form_submit_button("Classify Device", type="primary", width="stretch"):
                if device_desc:
                    with st.spinner("AI is classifying..."):
                        st.session_state.medical_device_classification = st.session_state.medical_device_classifier.classify_device(device_desc)
                else:
                    st.warning("Please describe the device.")
        if st.session_state.get('medical_device_classification'):
            res = st.session_state.medical_device_classification
            if "error" in res:
                st.error(res['error'])
            else:
                st.success(f"**Classification:** {res.get('classification', 'N/A')}")
                st.markdown(f"**Rationale:** {res.get('rationale', 'N/A')}")
    
    with col2, st.container(border=True):
        st.subheader("Pre-Mortem Analysis")
        scenario = st.text_input("Define failure scenario:", "Our new product launch failed.")
        if st.button("Generate Pre-Mortem Questions", width="stretch"):
            with st.spinner("AI is generating questions..."):
                st.session_state.pre_mortem_questions = st.session_state.pre_mortem_generator.generate_questions(scenario)
        
        if st.session_state.get('pre_mortem_questions'):
            answers = {}
            # Ensure questions are a list before iterating
            questions = st.session_state.pre_mortem_questions
            if isinstance(questions, list):
                for i, q in enumerate(questions):
                    answers[q] = st.text_area(f"Question {i+1}", value=q, key=f"q_{i}", disabled=True, label_visibility="collapsed")
                    answers[f"ans_{i}"] = st.text_area("Your Answer", key=f"ans_{i}")

            if st.button("Summarize Pre-Mortem Analysis", width="stretch"):
                qa_list = []
                if isinstance(questions, list):
                    for i, q in enumerate(questions):
                        ans = answers.get(f"ans_{i}")
                        if ans:
                            qa_list.append({"question": q, "answer": ans})
                
                if qa_list:
                    with st.spinner("AI is summarizing..."):
                        st.session_state.pre_mortem_summary = st.session_state.pre_mortem_generator.summarize_answers(qa_list)
                else:
                    st.warning("Please answer at least one question.")
        
        if st.session_state.get('pre_mortem_summary'):
            st.markdown(st.session_state.pre_mortem_summary)
