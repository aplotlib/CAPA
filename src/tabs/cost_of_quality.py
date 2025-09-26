# src/tabs/cost_of_quality.py

import streamlit as st

def display_cost_of_quality_tab():
    st.header("Cost of Quality (CoQ) Calculator")
    st.info("Estimate the total cost of quality, broken down into prevention, appraisal, and failure costs.")

    with st.form("coq_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Prevention Costs")
            quality_planning = st.number_input("Quality Planning ($)", 0.0, step=100.0)
            training = st.number_input("Quality Training ($)", 0.0, step=100.0)
            st.subheader("Failure Costs")
            scrap_rework = st.number_input("Internal Failures (Scrap, Rework) ($)", 0.0, step=100.0)
            returns_warranty = st.number_input("External Failures (Returns, Warranty) ($)", 0.0, step=100.0)
        with c2:
            st.subheader("Appraisal Costs")
            inspection = st.number_input("Inspection & Testing ($)", 0.0, step=100.0)
            audits = st.number_input("Quality Audits ($)", 0.0, step=100.0)

        if st.form_submit_button("Calculate Cost of Quality", type="primary", width='stretch'):
            total_prevention = quality_planning + training
            total_appraisal = inspection + audits
            total_failure = scrap_rework + returns_warranty
            st.session_state.coq_results = {
                "Prevention Costs": total_prevention, "Appraisal Costs": total_appraisal,
                "Failure Costs": total_failure, "Total Cost of Quality": total_prevention + total_appraisal + total_failure
            }

    if st.session_state.get('coq_results'):
        results = st.session_state.coq_results
        st.subheader("Cost of Quality Results")
        st.metric("Total Cost of Quality", f"${results['Total Cost of Quality']:,.2f}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Prevention Costs", f"${results['Prevention Costs']:,.2f}")
        c2.metric("Appraisal Costs", f"${results['Appraisal Costs']:,.2f}")
        c3.metric("Failure Costs", f"${results['Failure Costs']:,.2f}")
        
        total_coq = results.get('Total Cost of Quality', 0)
        if total_coq > 0:
            failure_costs = results.get('Failure Costs', 0)
            percentage = failure_costs / total_coq
            st.progress(percentage, text=f"{percentage:.1%} of Total CoQ is from Failures")

        if st.button("Get AI Insights on CoQ", width='stretch'):
            with st.spinner("AI is analyzing..."):
                prompt = f"Analyze this Cost of Quality (CoQ) data: {results}. Give actionable advice on how to shift spending from failure costs to prevention and appraisal costs to improve overall quality and long-term profitability."
                st.markdown(st.session_state.ai_context_helper.generate_response(prompt))
