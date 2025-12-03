import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from src.analysis import run_full_analysis
from src.parsers import AIFileParser

def display_dashboard():
    # --- HEADER & CONTEXT ---
    target_sku = st.session_state.product_info.get('sku', 'Unknown')
    st.title(f"Mission Control")

    # --- R&D AUTO-CONFIGURATION (NEW) ---
    with st.expander("🚀 Quick Start: R&D Auto-Configuration", expanded=False):
        st.markdown("### Upload R&D Specification")
        st.info("Upload a Product Specification (DOCX) to auto-populate the System (SKU, Name, FMEA Risks, Costs, Requirements).")
        
        rd_file = st.file_uploader("Upload R&D Spec (DOCX)", type=['docx'], key="rd_uploader")
        
        if rd_file and st.button("✨ Auto-Configure Project", type="primary"):
            if st.session_state.api_key_missing:
                st.error("API Key required for AI processing.")
            else:
                with st.spinner("AI is analyzing R&D document... This may take a minute."):
                    # Initialize parser locally or via factory
                    parser = AIFileParser(st.secrets.get("OPENAI_API_KEY"))
                    config_data = parser.parse_rd_document(rd_file)
                    
                    if "error" in config_data:
                        st.error(config_data['error'])
                    else:
                        # 1. Update Product Info
                        st.session_state.product_info['sku'] = config_data.get('sku', '')
                        st.session_state.product_info['name'] = config_data.get('product_name', '')
                        st.session_state.product_info['ifu'] = config_data.get('description', '')
                        
                        # 2. Update FMEA
                        risks = config_data.get('fmea_rows', [])
                        if risks:
                            st.session_state.fmea_rows = []
                            for r in risks:
                                st.session_state.fmea_rows.append({
                                    "Potential Failure Mode": r.get("Potential Failure Mode", "New Mode"),
                                    "Potential Effect(s)": r.get("Potential Effect(s)", ""),
                                    "Potential Cause(s)": r.get("Potential Cause(s)", ""),
                                    "Severity": 5, "Occurrence": 5, "Detection": 5, "RPN": 125
                                })
                        
                        # 3. Update Financials for Analysis
                        st.session_state.unit_cost = config_data.get('unit_cost', 50.0)
                        st.session_state.sales_price = config_data.get('sales_price', 150.0)
                        
                        # 4. Update Product Dev / Charter Inputs (partial)
                        st.session_state.product_dev_data['user_needs'] = config_data.get('user_needs', '')
                        st.session_state.product_dev_data['tech_requirements'] = config_data.get('tech_requirements', '')
                        
                        st.success(f"✅ Configuration Complete! Switched to SKU: {config_data.get('sku')}")
                        st.rerun()

    # --- DATA UPLOAD SECTION ---
    with st.expander("📂 Sales & Returns Data", expanded=not st.session_state.get('analysis_results')):
        st.markdown("### Define Reporting Period & Upload Data")
        
        # Date Range Inputs
        d_col1, d_col2 = st.columns(2)
        start_date = d_col1.date_input(
            "Start Date", 
            value=st.session_state.get('start_date', date.today().replace(day=1)),
            key="dash_start_date",
            help="Select the beginning of the analysis period."
        )
        end_date = d_col2.date_input(
            "End Date", 
            value=st.session_state.get('end_date', date.today()),
            key="dash_end_date",
            help="Select the end of the analysis period."
        )
        
        st.session_state.start_date = start_date
        st.session_state.end_date = end_date

        c1, c2 = st.columns(2)
        sales_file = c1.file_uploader("Upload Sales/Forecast Data (CSV/Excel)", type=['csv', 'xlsx'], help="File containing SKU and Quantity Sold.")
        returns_file = c2.file_uploader("Upload Returns Pivot/Report (CSV/Excel)", type=['csv', 'xlsx'], help="File containing SKU and Return Reasons/Quantities.")
        
        if st.button("🚀 Process Data & Run Analysis", type="primary", use_container_width=True):
            if sales_file and returns_file:
                with st.spinner("Processing data across SKUs..."):
                    try:
                        if sales_file.name.endswith('.csv'): sales_df = pd.read_csv(sales_file)
                        else: sales_df = pd.read_excel(sales_file)

                        if returns_file.name.endswith('.csv'): returns_df = pd.read_csv(returns_file)
                        else: returns_df = pd.read_excel(returns_file)
                            
                        proc_sales = st.session_state.data_processor.process_sales_data(sales_df)
                        proc_returns = st.session_state.data_processor.process_returns_data(returns_df)
                        
                        duration_days = (end_date - start_date).days
                        if duration_days < 1: duration_days = 1
                        
                        # Use session state costs (potentially from R&D upload)
                        u_cost = st.session_state.get('unit_cost', 50.0)
                        s_price = st.session_state.get('sales_price', 150.0)

                        analysis_output = run_full_analysis(
                            proc_sales, proc_returns, 
                            report_period_days=duration_days,
                            unit_cost=u_cost,
                            sales_price=s_price 
                        )
                        
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

    if not isinstance(results, dict) or "error" in results:
        st.error(results.get('error', 'Unknown analysis error'))
        return

    return_summary = results.get('return_summary')
    if return_summary is None or return_summary.empty:
        st.warning("⚠️ Analysis ran, but no valid return data was generated.")
        return

    # --- EXPORT BUTTON (NEW) ---
    col_export, _ = st.columns([1, 4])
    if col_export.button("💾 Export Dashboard Report", help="Download a DOCX report of these metrics."):
        doc_buffer = st.session_state.doc_generator.generate_dashboard_docx(results, st.session_state.product_info)
        st.download_button(
            "Download Report (.docx)", 
            doc_buffer, 
            f"Dashboard_Report_{target_sku}_{date.today()}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
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
        
    selected_sku = col_sel.selectbox("Select SKU to Analyze", sku_list, index=default_idx, help="Choose a specific product to see detailed charts and AI insights.")
    
    if selected_sku != st.session_state.product_info.get('sku'):
        st.session_state.product_info['sku'] = selected_sku

    summary_data = return_summary[return_summary['sku'] == selected_sku].iloc[0]

    # --- METRICS DISPLAY (Selected SKU) ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Return Rate", f"{summary_data.get('return_rate', 0):.2f}%", help="Percentage of sold units returned.")
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
    c4.metric("Quality Score", f"{int(quality_score)}/100", delta=risk_level, delta_color=delta_color, help="Proprietary score based on return rate benchmarks.")

    st.write("")

    # --- GAUGE CHART & INSIGHTS ---
    col_chart, col_ai = st.columns([1, 1])
    
    with col_chart:
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = summary_data.get('return_rate', 0),
            title = {'text': f"Return Rate: {selected_sku}"},
            gauge = {
                'axis': {'range': [None, max(20, rr + 5)]},
                'bar': {'color': "#00F3FF"},
                'steps': [
                    {'range': [0, 5], 'color': "gray"},
                    {'range': [5, 10], 'color': "lightgray"},
                    {'range': [10, 100], 'color': "red"}
                ],
            }
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_ai:
        st.subheader(f"🤖 AI Insight: {selected_sku}")
        with st.container(border=True):
            if rr > 10:
                st.markdown(f"""
                **Analysis for {selected_sku}:**
                The return rate of **{rr:.2f}%** is above the warning threshold. 
                
                **Recommendations:**
                1. Navigate to the **CAPA Lifecycle** tab to initiate an investigation.
                2. Check the **Returns** file for specific reason codes associated with this SKU.
                3. Review **Risk & Safety** (FMEA) to see if this failure mode was anticipated.
                """)
            else:
                st.markdown(f"""
                **Analysis for {selected_sku}:**
                The return rate of **{rr:.2f}%** is within acceptable limits.
                
                **Recommendations:**
                - Continue monitoring monthly trends.
                - No immediate CAPA action required.
                """)
