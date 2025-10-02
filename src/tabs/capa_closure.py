# src/tabs/capa_closure.py (NEW FILE)

import streamlit as st
import pandas as pd
from datetime import date
from src.analysis import run_full_analysis

def display_capa_closure_tab():
    """
    Displays the CAPA Effectiveness Check and Closure workflow.
    """
    st.header("✅ CAPA Effectiveness Check & Closure")
    st.info(
        "This workflow allows you to upload a completed CAPA, add new data, "
        "and measure the effectiveness of the implemented actions."
    )

    if 'capa_closure_data' not in st.session_state:
        st.session_state.capa_closure_data = {
            'original_metrics': None,
            'new_metrics': None,
            'effectiveness_summary': None
        }

    data = st.session_state.capa_closure_data

    # --- Step 1: Load Original CAPA Data ---
    with st.expander("📂 Step 1: Load Original CAPA Data", expanded=True):
        if st.session_state.get('capa_data') and st.session_state['capa_data'].get('issue_description'):
            if st.button("Load Current CAPA Data for Effectiveness Check"):
                st.session_state.capa_closure_data['original_capa'] = st.session_state.capa_data
                st.session_state.capa_closure_data['original_metrics'] = st.session_state.analysis_results
                st.success("Loaded current CAPA and analysis results.")
        else:
            st.warning("No active CAPA data found. Please complete the CAPA form first or upload a previous report.")
        
        # Placeholder for uploading a prior JSON/DOCX report
        # uploaded_capa = st.file_uploader("Or Upload a Previous CAPA Report")

    if data.get('original_capa'):
        st.subheader("Original CAPA Summary")
        st.write(f"**CAPA Number:** {data['original_capa'].get('capa_number')}")
        st.write(f"**Issue:** {data['original_capa'].get('issue_description')}")
        
        original_metrics = data.get('original_metrics', {}).get('return_summary')
        if original_metrics is not None and not original_metrics.empty:
            st.metric("Original Return Rate", f"{original_metrics.iloc[0]['return_rate']:.2f}%")

    # --- Step 2: Input New Data Post-Implementation ---
    with st.expander("📊 Step 2: Input New Data for Verification Period"):
        if data.get('original_capa'):
            st.info("Enter the sales and returns data for the period *after* the corrective actions were implemented.")
            new_sales = st.text_area("New Sales Data (Post-CAPA)", placeholder="e.g., 8500")
            new_returns = st.text_area("New Returns Data (Post-CAPA)", placeholder="e.g., 50")

            if st.button("Analyze Effectiveness", type="primary"):
                if new_sales:
                    from main import parse_manual_input, process_data
                    sales_df = parse_manual_input(new_sales, st.session_state.target_sku)
                    returns_df = parse_manual_input(new_returns, st.session_state.target_sku)
                    
                    with st.spinner("Analyzing new data..."):
                        # This assumes the same period length for comparison, can be adjusted
                        report_days = (st.session_state.end_date - st.session_state.start_date).days
                        data['new_metrics'] = run_full_analysis(
                            sales_df, returns_df, report_days, 
                            st.session_state.unit_cost, st.session_state.sales_price
                        )
                    st.success("Effectiveness analysis complete!")
                else:
                    st.warning("New sales data is required to check effectiveness.")

    # --- Step 3: View Results and Generate Summary ---
    if data.get('new_metrics'):
        st.subheader("Effectiveness Check Results")
        
        original_rate = data['original_metrics']['return_summary'].iloc[0]['return_rate']
        new_rate = data['new_metrics']['return_summary'].iloc[0]['return_rate']
        improvement = original_rate - new_rate

        c1, c2, c3 = st.columns(3)
        c1.metric("Original Return Rate", f"{original_rate:.2f}%")
        c2.metric("New Return Rate", f"{new_rate:.2f}%", delta=f"{-improvement:.2f}%")
        
        if st.button("🤖 Generate AI Effectiveness Summary"):
            with st.spinner("AI is generating the summary..."):
                prompt = f"""
                Analyze the effectiveness of a CAPA implementation.
                Original Return Rate: {original_rate:.2f}%
                New Return Rate after CAPA: {new_rate:.2f}%
                Corrective Actions Taken: {data['original_capa'].get('corrective_action')}
                
                Based on this data, write a concise summary for the CAPA closure report.
                - State whether the CAPA was effective and why.
                - Quantify the improvement.
                - Conclude with a recommendation (e.g., close CAPA, continue monitoring).
                """
                data['effectiveness_summary'] = st.session_state.ai_context_helper.generate_response(prompt)

    if data.get('effectiveness_summary'):
        st.markdown("### AI-Generated Effectiveness Summary")
        st.markdown(data['effectiveness_summary'])
