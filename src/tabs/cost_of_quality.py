# src/tabs/cost_of_quality.py

import streamlit as st
import plotly.express as px
import pandas as pd

def display_cost_of_quality_tab():
    st.header("Cost of Quality (CoQ) Calculator")
    st.info("Estimate the total cost of quality, broken down into prevention, appraisal, and failure costs. This helps visualize where quality-related expenses are concentrated.")

    with st.form("coq_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("Prevention Costs")
            quality_planning = st.number_input("Quality Planning ($)", 0.0, step=100.0)
            training = st.number_input("Quality Training ($)", 0.0, step=100.0)
        with c2:
            st.subheader("Appraisal Costs")
            inspection = st.number_input("Inspection & Testing ($)", 0.0, step=100.0)
            audits = st.number_input("Quality Audits ($)", 0.0, step=100.0)
        with c3:
            st.subheader("Failure Costs")
            scrap_rework = st.number_input("Internal Failures (Scrap, Rework) ($)", 0.0, step=100.0)
            returns_warranty = st.number_input("External Failures (Returns, Warranty) ($)", 0.0, step=100.0)

        if st.form_submit_button("Calculate Cost of Quality", type="primary", width="stretch"):
            total_prevention = quality_planning + training
            total_appraisal = inspection + audits
            total_failure = scrap_rework + returns_warranty
            st.session_state.coq_results = {
                "Prevention Costs": total_prevention, "Appraisal Costs": total_appraisal,
                "Failure Costs": total_failure, "Total Cost of Quality": total_prevention + total_appraisal + total_failure
            }

    if st.session_state.get('coq_results'):
        results = st.session_state.coq_results
        total_coq = results.get('Total Cost of Quality', 0)
        
        st.subheader("Cost of Quality Results")
        st.metric("Total Cost of Quality", f"${total_coq:,.2f}")
        
        if total_coq > 0:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.metric("Prevention Costs", f"${results['Prevention Costs']:,.2f}")
                st.metric("Appraisal Costs", f"${results['Appraisal Costs']:,.2f}")
                st.metric("Failure Costs", f"${results['Failure Costs']:,.2f}")

                failure_costs = results.get('Failure Costs', 0)
                percentage = failure_costs / total_coq if total_coq > 0 else 0
                st.progress(percentage, text=f"{percentage:.1%} of Total CoQ is from Failures")
            
            with col2:
                # Create a pie chart
                coq_data = pd.DataFrame({
                    'Category': ['Prevention Costs', 'Appraisal Costs', 'Failure Costs'],
                    'Cost': [results['Prevention Costs'], results['Appraisal Costs'], results['Failure Costs']]
                })
                fig = px.pie(coq_data, values='Cost', names='Category', title='Cost of Quality Breakdown',
                             color_discrete_map={
                                 'Prevention Costs': '#4CAF50', # Green
                                 'Appraisal Costs': '#FFC107', # Amber
                                 'Failure Costs': '#F44336'   # Red
                             })
                fig.update_layout(showlegend=False, font_family="Inter")
                fig.update_traces(textposition='inside', textinfo='percent+label')
                
                # Fix: Replaced use_container_width=True with width="stretch"
                st.plotly_chart(fig, width="stretch")

            if not st.session_state.api_key_missing:
                if st.button("Get AI Insights on CoQ", width="stretch"):
                    with st.spinner("AI is analyzing..."):
                        prompt = f"Analyze this Cost of Quality (CoQ) data: {results}. Give actionable advice on how to shift spending from failure costs to prevention and appraisal costs to improve overall quality and long-term profitability."
                        st.info(st.session_state.ai_context_helper.generate_response(prompt))
