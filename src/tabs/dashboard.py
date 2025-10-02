# src/tabs/dashboard.py

import streamlit as st
import pandas as pd
import os

def display_dashboard():
    """Renders the main dashboard tab with key metrics and AI insights."""

    if not st.session_state.analysis_results:
        st.info("👋 Welcome to the Automated QMS! Please add product and data in the sidebar to begin your analysis.")
        
        # Safely handle the logo path
        # This assumes dashboard.py is in src/tabs/ and logo.png is in the root project directory
        # This is a robust way to construct the path regardless of where the script is run from.
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        logo_path = os.path.join(project_root, "logo.png")
        
        if os.path.exists(logo_path):
            st.image(logo_path, width=200)
        
        return

    results = st.session_state.analysis_results
    if "error" in results:
        st.error(f"Analysis Failed: {results['error']}")
        return

    summary_df = results.get('return_summary')
    if summary_df is None or summary_df.empty:
        st.warning("No data found for the target SKU to generate a summary.")
        return

    # Filter summary data for the specific target SKU
    sku_summary = summary_df[summary_df['sku'] == st.session_state.product_info['sku']]
    if sku_summary.empty:
        st.warning(f"No summary data could be calculated for SKU: {st.session_state.product_info['sku']}")
        return

    summary_data = sku_summary.iloc[0]

    st.subheader(f"Quality Overview for SKU: {st.session_state.product_info['sku']}")

    # Display key metrics
    cols = st.columns(4)
    cols[0].metric("Return Rate", f"{summary_data.get('return_rate', 0):.2f}%",
                   help="Percentage of units returned out of total units sold.")
    cols[1].metric("Total Returned", f"{int(summary_data.get('total_returned', 0)):,}",
                   help="Total number of units returned in the selected period.")
    cols[2].metric("Total Sold", f"{int(summary_data.get('total_sold', 0)):,}",
                   help="Total number of units sold in the selected period.")
    
    quality_score = results['quality_metrics'].get('quality_score', 0)
    risk_level = results['quality_metrics'].get('risk_level', 'Low')
    delta_color = "inverse" if risk_level in ["Medium", "High"] else "normal"
    
    cols[3].metric(
        "Quality Score",
        f"{quality_score}/100",
        delta=risk_level,
        delta_color=delta_color,
        help="A calculated score from 0-100 based on return rate. Higher is better."
    )

    st.divider()

    # Display AI-generated insights
    with st.container(border=True):
        st.markdown("##### 🤖 AI-Generated Insights")
        st.info(f"{results.get('insights', 'No insights generated.')}")
