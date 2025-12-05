# src/tabs/capa_closure.py

import streamlit as st
import pandas as pd
from datetime import date
# Use absolute imports for reliability
from src.analysis import run_full_analysis

def parse_manual_input_local(input_str: str, sku: str) -> pd.DataFrame:
    """
    Parses a single number string into a DataFrame for analysis.
    Local helper to replace missing util function.
    """
    try:
        val = float(str(input_str).strip().replace(',', ''))
        return pd.DataFrame([{'sku': sku, 'quantity': val}])
    except (ValueError, TypeError):
        return pd.DataFrame()

def display_capa_closure_tab():
    """
    Displays the CAPA Effectiveness Check and Closure workflow with improved UI/UX.
    """
    st.header("✅ CAPA Effectiveness Check & Closure")
    st.info("A critical step in the CAPA process is to verify that the actions taken were effective and did not introduce any new risks.")

    # Validate state exists
    if 'capa_closure_data' not in st.session_state or not st.session_state.capa_closure_data.get('original_capa'):
        st.warning("⬅️ To begin, please complete the form on the **CAPA** tab and click **'🚀 Proceed to Effectiveness Check'**.", icon="👈")
        return

    data = st.session_state.capa_closure_data
    original_capa = data['original_capa']
    original_metrics = data.get('original_metrics')

    with st.container(border=True):
        st.subheader("Step 1: Review Original CAPA")
        
        c1, c2 = st.columns(2)
        c1.text_input("CAPA Number", value=original_capa.get('capa_number'), disabled=True, key="closure_capa_num_display")
        c2.text_input("Product SKU", value=original_capa.get('product_name'), disabled=True, key="closure_sku_display")

        st.text_area("Problem Description", value=original_capa.get('issue_description'), disabled=True, height=100, key="closure_desc_display")
        st.text_area("Root Cause Analysis", value=original_capa.get('root_cause'), disabled=True, height=100, key="closure_root_cause_display")
        
        # Safe access to original metrics
        original_rate_val = 0.0
        if original_metrics and not original_metrics.get('error'):
            summary = original_metrics.get('return_summary')
            if summary is not None and not summary.empty:
                original_rate_val = summary.iloc[0].get('return_rate', 0.0)
                st.metric("Initial Performance Metric (Return Rate)", f"{original_rate_val:.2f}%", help="This was the return rate when the CAPA was initiated.")
            else:
                st.warning("Original return data is unavailable.")
        else:
            st.warning("Metrics for the original issue are missing or invalid.")

    with st.container(border=True):
        st.subheader("Step 2: Document Implementation")
        
        c1, c2 = st.columns(2)
        data['implemented_by'] = c1.text_input("Actions Implemented By", key="impl_by")
        data['implementation_date'] = c2.date_input("Implementation Completion Date", key="impl_date")
        
        data['implementation_details'] = st.text_area("Implementation Details & Evidence", 
            placeholder="Summarize how the corrective/preventive actions were implemented...",
            key="impl_details_area")

    with st.container(border=True):
        st.subheader("Step 3: Analyze Post-Implementation Performance")
        st.markdown("Enter new data for a similar time period *after* the implementation date to measure the change.")
        
        with st.form("effectiveness_form"):
            c1, c2 = st.columns(2)
            new_sales = c1.text_input("New Sales Data (Post-CAPA)", placeholder="e.g., 8500")
            new_returns = c2.text_input("New Returns Data (Post-CAPA)", placeholder="e.g., 50")
            
            submitted = st.form_submit_button("📊 Analyze Effectiveness", type="primary", width="stretch")
            if submitted:
                if new_sales:
                    sku = st.session_state.product_info['sku']
                    sales_df = parse_manual_input_local(new_sales, sku)
                    returns_df = parse_manual_input_local(new_returns, sku)
                    
                    with st.spinner("Analyzing new data..."):
                        # Ensure report_days is valid
                        start_d = st.session_state.get('start_date', date.today())
                        end_d = st.session_state.get('end_date', date.today())
                        report_days = (end_d - start_d).days if end_d > start_d else 30
                        
                        # Use default costs if not in session state to prevent crash
                        unit_cost = st.session_state.get('unit_cost', 50.0)
                        sales_price = st.session_state.get('sales_price', 150.0)

                        result = run_full_analysis(
                            sales_df, returns_df, report_days, 
                            unit_cost, sales_price
                        )
                        
                        if "error" in result:
                            st.error(f"Analysis Error: {result['error']}")
                            data['new_metrics'] = None
                        else:
                            data['new_metrics'] = result
                            st.success("Analysis complete!")
                            st.rerun()
                else:
                    st.warning("New sales data is required to check effectiveness.")

    # Step 4: Results
    if data.get('new_metrics'):
        new_metrics = data['new_metrics']
        
        # Double check for error key in stored data
        if "error" in new_metrics:
            st.error(f"Saved metrics contain errors: {new_metrics['error']}")
        else:
            with st.container(border=True):
                st.subheader("Step 4: Review Results & Conclude")
                
                # Safely get new rate
                new_summary = new_metrics.get('return_summary')
                if new_summary is not None and not new_summary.empty:
                    new_rate = new_summary.iloc[0].get('return_rate', 0.0)
                    
                    improvement = original_rate_val - new_rate

                    st.write("#### Performance Comparison")
                    c1, c2, _ = st.columns(3)
                    c1.metric("Initial Return Rate", f"{original_rate_val:.2f}%")
                    c2.metric("New Return Rate", f"{new_rate:.2f}%", delta=f"{-improvement:.2f}%", delta_color="inverse")
                    
                    if st.button("🤖 Generate AI Effectiveness Summary", width="stretch", type="primary"):
                        with st.spinner("AI is generating the summary..."):
                            prompt = f"""
                            Analyze the effectiveness of a CAPA implementation based on the following data:
                            - Initial Return Rate: {original_rate_val:.2f}%
                            - Return Rate After Actions: {new_rate:.2f}%
                            - Corrective Actions Taken: {original_capa.get('corrective_action')}
                            - Implementation Details: {data.get('implementation_details', 'Not provided.')}
                            
                            Write a concise summary for the 'Effectiveness Check Findings' section of a CAPA form.
                            1. State clearly whether the implemented actions were effective.
                            2. Quantify the improvement (e.g., reduction in return rate).
                            3. Conclude with a definitive recommendation.
                            """
                            data['effectiveness_summary'] = st.session_state.ai_context_helper.generate_response(prompt)
                            st.rerun()
                else:
                    st.error("New analysis data is empty or invalid.")

            data['effectiveness_summary'] = st.text_area("Effectiveness Summary", value=data.get('effectiveness_summary', ''), height=200, key="eff_summary")

            st.divider()
            
            st.write("#### Final Closure")
            c1, c2 = st.columns(2)
            data['closed_by'] = c1.text_input("Closed By", key="closed_by")
            data['closure_date'] = c2.date_input("Closure Date", value=date.today(), key="closure_date")
            
           if st.button("✔️ Formally Close CAPA", type="primary", width="stretch"):
                st.session_state.capa_data['effectiveness_check_findings'] = data.get('effectiveness_summary', 'Effectiveness confirmed.')
                st.session_state.capa_data['closed_by'] = data.get('closed_by')
                st.session_state.capa_data['closure_date'] = data.get('closure_date')
                st.success(f"CAPA {original_capa.get('capa_number')} has been formally closed on {data['closure_date']}.")
                st.balloons()
