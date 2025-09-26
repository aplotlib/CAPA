# src/tabs/dashboard.py

import streamlit as st

def display_dashboard():
    """Renders the main dashboard tab with key metrics and AI insights."""
    st.header("📈 Quality Dashboard")

    if not st.session_state.analysis_results:
        st.info("👋 Welcome! Please configure your product and add data in the sidebar to begin.")
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
    sku_summary = summary_df[summary_df['sku'] == st.session_state.target_sku]
    if sku_summary.empty:
        st.warning(f"No summary data could be calculated for SKU: {st.session_state.target_sku}")
        return

    summary_data = sku_summary.iloc[0]

    # Display key metrics in containers
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Return Rate", f"{summary_data.get('return_rate', 0):.2f}%")
        c2.metric("Total Returned", f"{int(summary_data.get('total_returned', 0)):,}")
        c3.metric("Total Sold", f"{int(summary_data.get('total_sold', 0)):,}")
        c4.metric(
            "Quality Score",
            f"{results['quality_metrics'].get('quality_score', 'N/A')}/100",
            delta=results['quality_metrics'].get('risk_level', ''),
            delta_color="inverse"
        )

    st.divider()

    # Display AI-generated insights in a container
    with st.container(border=True):
        st.subheader("🤖 AI Insights")
        st.markdown(f"{results.get('insights', 'No insights generated.')}")
