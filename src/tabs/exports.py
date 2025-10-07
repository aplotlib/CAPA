# src/tabs/exports.py

import streamlit as st
from datetime import date
from src.audit_logger import AuditLogger

def display_exports_tab():
    st.header("📄 Document Exports & Audit Trail")
    st.info("Generate project reports, export tracker-friendly data, and download the audit trail for this session.")
    
    logger = AuditLogger()
    doc_generator = st.session_state.doc_generator

    with st.container(border=True):
        st.subheader("Comprehensive Project Report")
        export_options = st.multiselect(
            "Select sections to include in the final DOCX report:",
            ["CAPA Form", "CAPA Closure", "FMEA", "ISO 14971 Assessment", "URRA", "Vendor Email Draft", "Human Factors Report"],
            default=["CAPA Form", "CAPA Closure", "FMEA", "URRA"]
        )

        if st.button("Generate Project Summary Report", type="primary", use_container_width=True):
            if not st.session_state.capa_data.get('issue_description') and "CAPA Form" in export_options:
                st.warning("Please fill out the CAPA form before generating a report that includes it.")
            else:
                with st.spinner("Generating comprehensive report..."):
                    doc_buffer = doc_generator.generate_summary_docx(st.session_state, export_options)
                    st.download_button(
                        "📥 Download Project Summary (.docx)", doc_buffer,
                        f"Project_Summary_{st.session_state.product_info['sku']}_{date.today()}.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                    logger.log_action(
                        user="current_user",
                        action="export_document",
                        entity="project_summary",
                        details={"sections": export_options, "format": "docx"}
                    )
    
    st.divider()
    st.subheader("Tracker & Audit Exports")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("Generate CAPA Tracker Data", use_container_width=True):
            if not st.session_state.capa_data.get('issue_description'):
                st.warning("Please fill out the CAPA form first to generate tracker data.")
            else:
                with st.spinner("Generating tracker data..."):
                    excel_buffer = doc_generator.generate_capa_tracker_excel(st.session_state)
                    st.download_button(
                        "📥 Download Tracker Data (.xlsx)",
                        data=excel_buffer,
                        file_name=f"CAPA_Tracker_{st.session_state.product_info['sku']}_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="download_tracker" # Unique key
                    )
                    logger.log_action(
                        user="current_user",
                        action="export_capa_tracker",
                        entity="capa_data",
                        details={"sku": st.session_state.product_info['sku']}
                    )

    with c2:
        audit_log_csv = logger.get_audit_log_csv()
        st.download_button(
            label="Download Audit Trail (CSV)",
            data=audit_log_csv,
            file_name=f"audit_trail_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )
