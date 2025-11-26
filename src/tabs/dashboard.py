import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.analysis import run_full_analysis

def display_dashboard():
    st.title(f"Mission Control: `{st.session_state.product_info['sku']}`")

    # --- DATA UPLOAD SECTION ---
    with st.expander("📂 Data Upload & Processing", expanded=not st.session_state.get('analysis_results')):
        c1, c2 = st.columns(2)
        sales_file = c1.file_uploader("Upload Sales Data (CSV/Excel)", type=['csv', 'xlsx'])
        returns_file = c2.file_uploader("Upload Returns Data (CSV/Excel)", type=['csv', 'xlsx'])
        
        if st.button("🚀 Process Data & Run Analysis", type="primary", use_container_width=True):
            if sales_file and returns_file:
                with st.spinner("Processing data..."):
                    try:
                        # Load Data
                        if sales_file.name.endswith('.csv'):
                            sales_df = pd.read_csv(sales_file)
                        else:
                            sales_df = pd.read_excel(sales_file)

                        if returns_file.name.endswith('.csv'):
                            returns_df = pd.read_csv(returns_file)
                        else:
                            returns_df = pd.read_excel(returns_file)
                            
                        # Process Data
                        proc_sales = st.session_state.data_processor.process_sales_data(sales_df)
                        proc_returns = st.session_state.data_processor.process_returns_data(returns_df)
                        
                        # Run Analysis
                        analysis_output = run_full_analysis(
                            proc_sales, proc_returns, 
                            report_period_days=30, # Defaulting to 30 days
                            unit_cost=50.0, # Placeholder or add input field
                            sales_price=150.0 # Placeholder or add input field
                        )
                        
                        # Validate output before saving to session state
                        if "error" in analysis_output:
                            st.error(f"Analysis Failed: {analysis_output['error']}")
                            st.session_state.analysis_results = None
                        else:
                            st.session_state.analysis_results = analysis_output
                            st.success("Analysis Complete!")
                            st.rerun()

                    except Exception as e:
                        st.error(f"Error processing files: {e}")
            else:
                st.warning("Please upload both Sales and Returns files to proceed.")

    # --- DASHBOARD DISPLAY ---
    if not st.session_state.get('analysis_results'):
        st.info("👆 Please upload data above to view metrics.")
        return

    results = st.session_state.analysis_results

    # Check for error key again (redundancy safety)
    if "error" in results:
        st.error(results['error'])
        return

    # Check if return_summary exists and is a valid DataFrame
    return_summary = results.get('return_summary')
    if return_summary is None or return_summary.empty:
        st.warning("⚠️ Analysis ran, but no valid return data was generated. Please ensure your files contain matching SKUs.")
        return

    # Safe to access iloc now
    summary_data = return_summary.iloc[0]
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Return Rate", f"{summary_data.get('return_rate', 0):.2f}%")
    c2.metric("Total Returns", f"{int(summary_data.get('total_returned', 0)):,}")
    
    quality_metrics = results.get('quality_metrics', {})
    risk_level = quality_metrics.get('risk_level', 'Low')
    quality_score = quality_metrics.get('quality_score', 0)
    
    delta_color = "inverse" if risk_level in ["Medium", "High"] else "normal"
    c4.metric("Quality Score", f"{quality_score}/100", delta=risk_level, delta_color=delta_color)

    st.divider()

    # Gauge Chart
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = summary_data.get('return_rate', 0),
        title = {'text': "Return Rate (%)"},
        gauge = {
            'axis': {'range': [None, 20]},
            'bar': {'color': "#00F3FF"},
            'steps': [
                {'range': [0, 5], 'color': "gray"},
                {'range': [5, 10], 'color': "lightgray"},
                {'range': [10, 20], 'color': "red"}
            ],
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
    st.plotly_chart(fig, use_container_width=True)
    
    # AI Insights
    st.subheader("🤖 AI Analysis")
    st.container(border=True).markdown(results.get('insights', 'No detailed insights available.'))
