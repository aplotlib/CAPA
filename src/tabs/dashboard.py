from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from src.utils import run_quality_analytics

def display_dashboard_tab():
    st.header("🎯 Product Quality Dashboard")
    st.caption("Unified view of sales, returns, customer feedback, and quality KPIs.")

    # --- FILE INPUT ---
    st.divider()
    st.subheader("📂 Upload Input Data")
    st.caption("Upload your return/sales data and feedback data (or just returns data).")
    col1, col2 = st.columns([1, 1])
    with col1:
        rd_file = st.file_uploader("Upload Returns Data (CSV)", type=["csv"])
    with col2:
        fb_file = st.file_uploader("Upload Feedback Data (CSV)", type=["csv"])

    if rd_file and st.button("✨ Auto-Configure Project", type="primary", width="stretch"):
        st.session_state.product_info = st.session_state.get('product_info', {})
        st.session_state.product_info.update({
            "name": "Sample Product",
            "manufacturer": "Sample Manufacturer",
            "model": "Model X"
        })
        st.success("Auto-configured product info.")

    if rd_file:
        st.divider()
        st.subheader("🔍 Analyze Returns & Quality")
        st.caption("Process returns data, analyze return rates, root causes, and risk scoring.")
        if st.button("🚀 Process Data & Run Analysis", type="primary", width="stretch"):
            with st.spinner("Processing data..."):
                results = run_quality_analytics(rd_file, fb_file)
                st.session_state.dashboard_results = results
                st.success("Analysis complete.")

    if "dashboard_results" not in st.session_state:
        st.info("Upload data to begin analysis.")
        return

    results = st.session_state.dashboard_results

    # --- SUMMARY SECTION ---
    summary = results.get('summary')
    if summary:
        st.subheader("📌 Executive Summary")
        st.markdown(f"**Total Units Sold:** {summary.get('total_units_sold', 'N/A')}")
        st.markdown(f"**Total Returns:** {summary.get('total_returns', 'N/A')}")
        st.markdown(f"**Overall Return Rate:** {summary.get('overall_return_rate', 'N/A')}%")
        st.markdown(f"**Estimated Cost of Quality:** ${summary.get('cost_of_quality', 'N/A'):,}")
    else:
        st.warning("No summary data available.")

    # --- RETURN ANALYSIS ---
    st.divider()
    st.subheader("📉 Return Analysis")

    # --- DATA CLEAN CHECK ---
    if 'return_summary' not in results:
        st.error(results.get('error', 'Unknown analysis error'))
        return

    return_summary = results.get('return_summary')
    if return_summary is None or return_summary.empty:
        st.warning("⚠️ Analysis ran, but no valid return data was generated.")
        return

    # --- EXPORT BUTTON ---
    col_export, _ = st.columns([1, 4])
    if col_export.button("💾 Export Dashboard Report"):
        doc_buffer = st.session_state.doc_generator.generate_dashboard_docx(results, st.session_state.product_info)
        st.download_button(
            "Download Report (.docx)",
            doc_buffer,
            f"Dashboard_Report_{target_sku}_{date.today()}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    # --- SKU SELECTION & BREAKDOWN ---
    st.divider()
    st.subheader("📊 SKU Performance Breakdown")
    with st.expander("View Full Data Table", expanded=True):
        st.dataframe(
            return_summary,
            column_config={
                "sku": "SKU",
                "total_sold": st.column_config.NumberColumn("Total Sales", format="%d"),
                "total_returned": st.column_config.NumberColumn("Total Returns", format="%d"),
                "return_rate": st.column_config.NumberColumn("Return Rate (%)", format="%.2f%%"),
                "quality_status": "Status"
            },
            use_container_width=True,
            hide_index=True
        )

    st.subheader("🔎 Detailed Analysis")
    col_sel, col_blank = st.columns([1, 2])
    sku_list = return_summary['sku'].unique().tolist()
    
    default_idx = 0
    if target_sku in sku_list:
        default_idx = sku_list.index(target_sku)
        
    selected_sku = col_sel.selectbox("Select SKU to Analyze", sku_list, index=default_idx)
    summary_data = return_summary[return_summary['sku'] == selected_sku].iloc[0]

    # --- METRICS DISPLAY ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Return Rate", f"{summary_data.get('return_rate', 0):.2f}%")
    c2.metric("Total Returns", f"{int(summary_data.get('total_returned', 0)):,}")
    c3.metric("Total Sold", f"{int(summary_data.get('total_sold', 0)):,}")
    
    rr = summary_data.get('return_rate', 0)
    if rr > 15: 
        risk_level = "High"
        quality_score = max(0, 30 - (rr - 20) * 3)
    elif rr > 10: 
        risk_level = "Medium"
        quality_score = 50 + (15 - rr) * 4
    else: 
        risk_level = "Low"
        quality_score = 90 + (5 - rr) * 2
        
    delta_color = "inverse" if risk_level in ["Medium", "High"] else "normal"
    c4.metric("Quality Score", f"{int(quality_score)}/100", delta=risk_level, delta_color=delta_color)

    st.write("")

    # --- GAUGE CHART & INSIGHTS ---
    col_chart, col_ai = st.columns([1, 1])

    with col_chart:
        st.subheader("📟 Risk Gauge")
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=rr,
            title={'text': "Return Rate"},
            gauge={'axis': {'range': [0, 25]},
                   'bar': {'color': "darkblue"},
                   'steps': [
                       {'range': [0, 10], 'color': "lightgreen"},
                       {'range': [10, 15], 'color': "orange"},
                       {'range': [15, 25], 'color': "red"}],
                   }))
        st.plotly_chart(gauge_fig, use_container_width=True)

    with col_ai:
        st.subheader("🤖 AI Insights & Recommendations")
        if "dashboard_insights" in results:
            st.success(results["dashboard_insights"])
        else:
            st.info("No AI insights generated.")

    st.divider()

    # --- TOP ISSUES ---
    st.subheader("🚨 Top Return Issues")
    top_issues = results.get("top_return_reasons", pd.DataFrame())
    if not top_issues.empty:
        st.bar_chart(top_issues.set_index('reason')['count'], use_container_width=True)
    else:
        st.info("No top issues identified.")

    # --- FEEDBACK INSIGHTS ---
    st.divider()
    st.subheader("🗣️ Customer Feedback Sentiment")
    if "feedback_summary" in results:
        st.markdown(f"**Overall Sentiment:** {results['feedback_summary'].get('overall_sentiment', 'N/A')}")
        st.markdown(f"**Most Common Complaint:** {results['feedback_summary'].get('common_complaint', 'N/A')}")
    else:
        st.info("No feedback summary available.")

    # --- ACTION PLAN ---
    st.divider()
    st.subheader("📝 Suggested Actions")
    if "action_plan" in results:
        for item in results["action_plan"]:
            st.markdown(f"- {item}")
    else:
        st.info("No action plan generated.")
