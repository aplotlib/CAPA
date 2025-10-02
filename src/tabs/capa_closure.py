# src/tabs/capa_closure.py

import streamlit as st
from datetime import date

def display_capa_closure_tab():
    """
    Displays the CAPA Effectiveness Check and Closure workflow with improved UI/UX.
    """
    st.header("✅ CAPA Effectiveness Check & Closure")
    st.info("A critical step in the CAPA process is to verify that the actions taken were effective and did not introduce any new risks.")

    # Check if data has been loaded from the main CAPA tab
    if 'capa_closure_data' not in st.session_state or not st.session_state.capa_closure_data.get('original_capa'):
        st.warning("⬅️ To begin, please complete the form on the **CAPA** tab and click **'🚀 Proceed to Effectiveness Check'**.", icon="👈")
        # You can replace the imgur link with a local image if you prefer
        st.image("https://i.imgur.com/g8e5gG3.png", caption="Click the 'Proceed to Effectiveness Check' button on the CAPA tab first.")
        return # Stop rendering the rest of the page

    data = st.session_state.capa_closure_data
    original_capa = data['original_capa']
    original_metrics = data['original_metrics']

    # --- Step 1: Review Initial CAPA Data ---
    with st.container(border=True):
        st.subheader("Step 1: Review Original CAPA")
        
        c1, c2 = st.columns(2)
        c1.text_input("CAPA Number", value=original_capa.get('capa_number'), disabled=True)
        c2.text_input("Product SKU", value=original_capa.get('product_name'), disabled=True)

        st.text_area("Problem Description", value=original_capa.get('issue_description'), disabled=True, height=100)
        st.text_area("Root Cause Analysis", value=original_capa.get('root_cause'), disabled=True, height=100)
        
        if original_metrics and original_metrics.get('return_summary') is not None:
            original_rate = original_metrics['return_summary'].iloc[0]['return_rate']
            st.metric("Initial Performance Metric (Return Rate)", f"{original_rate:.2f}%", help="This was the return rate when the CAPA was initiated.")

    # --- Step 2: Document Action Implementation ---
    with st.container(border=True):
        st.subheader("Step 2: Document Implementation")
        
        c1, c2 = st.columns(2)
        data['implemented_by'] = c1.text_input("Actions Implemented By", key="impl_by")
        data['implementation_date'] = c2.date_input("Implementation Completion Date", key="impl_date")
        
        data['implementation_details'] = st.text_area("Implementation Details & Evidence", 
            placeholder="Summarize how the corrective/preventive actions were implemented. Reference any change orders, new SOPs, or training records.",
            key="impl_details_area")

    # --- Step 3: Analyze Effectiveness ---
    with st.container(border=True):
        st.subheader("Step 3: Analyze Post-Implementation Performance")
        st.markdown("Enter new data for a similar time period *after* the implementation date to measure the change.")
        
        with st.form("effectiveness_form"):
            c1, c2 = st.columns(2)
            new_sales = c1.text_input("New Sales Data (Post-CAPA)", placeholder="e.g., 8500")
            new_returns = c2.text_input("New Returns Data (Post-CAPA)", placeholder="e.g., 50")
            
            submitted = st.form_submit_button("📊 Analyze Effectiveness", type="primary", use_container_width=True)
            if submitted:
                if new_sales:
                    from main import parse_manual_input
                    from src.analysis import run_full_analysis
                    
                    sales_df = parse_manual_input(new_sales, st.session_state.target_sku)
                    returns_df = parse_manual_input(new_returns, st.session_state.target_sku)
                    
                    with st.spinner("Analyzing new data..."):
                        report_days = (st.session_state.end_date - st.session_state.start_date).days
                        data['new_metrics'] = run_full_analysis(
                            sales_df, returns_df, report_days, 
                            st.session_state.unit_cost, st.session_state.sales_price
                        )
                    st.success("Analysis complete!")
                else:
                    st.warning("New sales data is required to check effectiveness.")

    # --- Step 4: Review Results & Close CAPA ---
    if data.get('new_metrics'):
        with st.container(border=True):
            st.subheader("Step 4: Review Results & Conclude")
            
            original_rate = data['original_metrics']['return_summary'].iloc[0]['return_rate']
            new_rate = data['new_metrics']['return_summary'].iloc[0]['return_rate']
            improvement = original_rate - new_rate

            st.write("#### Performance Comparison")
            c1, c2, c3 = st.columns(3)
            c1.metric("Initial Return Rate", f"{original_rate:.2f}%")
            c2.metric("New Return Rate", f"{new_rate:.2f}%", delta=f"{-improvement:.2f}%", delta_color="inverse")
            
            # Use AI to summarize
            if st.button("🤖 Generate AI Effectiveness Summary", use_container_width=True):
                with st.spinner("AI is generating the summary..."):
                    prompt = f"""
                    Analyze the effectiveness of a CAPA implementation based on the following data:
                    - Initial Return Rate: {original_rate:.2f}%
                    - Return Rate After Actions: {new_rate:.2f}%
                    - Corrective Actions Taken: {original_capa.get('corrective_action')}
                    - Implementation Details: {data.get('implementation_details', 'Not provided.')}
                    
                    Write a concise summary for the 'Effectiveness Check Findings' section of a CAPA form.
                    1. State clearly whether the implemented actions were effective.
                    2. Quantify the improvement (e.g., reduction in return rate).
                    3. Conclude with a definitive recommendation: either "The CAPA can be formally closed" or "The actions were not fully effective; further investigation is required."
                    """
                    data['effectiveness_summary'] = st.session_state.ai_context_helper.generate_response(prompt)

            if data.get('effectiveness_summary'):
                st.text_area("AI-Generated Effectiveness Summary", value=data['effectiveness_summary'], height=200, key="eff_summary")

            st.divider()
            
            st.write("#### Final Closure")
            c1, c2 = st.columns(2)
            data['closed_by'] = c1.text_input("Closed By", key="closed_by")
            data['closure_date'] = c2.date_input("Closure Date", value=date.today(), key="closure_date")
            
            if st.button("✔️ Formally Close CAPA", type="primary", use_container_width=True):
                st.session_state.capa_data['effectiveness_check_findings'] = data.get('effectiveness_summary', 'Effectiveness confirmed by metric improvement.')
                st.session_state.capa_data['closed_by'] = data.get('closed_by')
                st.session_state.capa_data['closure_date'] = data.get('closure_date')
                st.success(f"CAPA {original_capa.get('capa_number')} has been formally closed on {data['closure_date']}.")
                st.balloons()
