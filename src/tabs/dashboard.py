# src/tabs/dashboard.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def display_dashboard():
    # ... (Keep existing data checks) ...
    if not st.session_state.get('analysis_results'):
        st.info("Please process data to view the dashboard.")
        return

    results = st.session_state.analysis_results
    summary_data = results.get('return_summary').iloc[0]
    
    st.title(f"Mission Control: `{st.session_state.product_info['sku']}`")

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Return Rate", f"{summary_data.get('return_rate', 0):.2f}%")
    c2.metric("Total Returns", f"{int(summary_data.get('total_returned', 0)):,}")
    
    risk_level = results['quality_metrics'].get('risk_level', 'Low')
    delta_color = "inverse" if risk_level in ["Medium", "High"] else "normal"
    c4.metric("Quality Score", f"{results['quality_metrics'].get('quality_score')}/100", delta=risk_level, delta_color=delta_color)

    st.divider()

    # THEME AWARE CHARTS (v1.46+)
    # Detect if we are in dark mode to adjust chart background
    theme = st.context.theme
    is_dark = theme.base == "dark" if theme else True
    
    chart_bg = "#151922" if is_dark else "#FFFFFF"
    text_color = "#E0E6ED" if is_dark else "#1A202C"

    # Example Chart
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = summary_data.get('return_rate', 0),
        title = {'text': "Return Rate (%)", 'font': {'color': text_color}},
        gauge = {
            'axis': {'range': [None, 20]},
            'bar': {'color': "#00F3FF"},
            'bgcolor': chart_bg,
            'steps': [
                {'range': [0, 5], 'color': "rgba(0, 255, 157, 0.3)"},
                {'range': [5, 10], 'color': "rgba(255, 255, 0, 0.3)"},
                {'range': [10, 20], 'color': "rgba(255, 0, 0, 0.3)"}
            ],
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': text_color})
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Insights
    st.subheader("🤖 AI Analysis")
    st.container(border=True).markdown(results.get('insights'))
