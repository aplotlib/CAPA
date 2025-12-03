# src/tabs/exports.py

import streamlit as st
from datetime import date
from src.audit_logger import AuditLogger

def display_exports_tab():
    st.header("塘 Document Exports & Audit Trail")
    st.info("Generate project reports, export tracker-friendly data, and download the audit trail for this session.")
    
    logger = AuditLogger()
    doc_generator = st.session_state.doc_generator

    # Project Charter Export
    if st.session_state.get('project_charter_data'):
        with st.container(border=True):
            st.subheader("Project Charter")
            charter_data = st.session_state.project_charter_data
            # Updated width="stretch"
            if st.button("Generate Project Charter Document", width="stretch"):
                with st.spinner("Generating charter..."):
                    doc_buffer = doc_generator.generate_project_charter_docx(charter_data)
                    st.download_button(
                        "踏 Download Project Charter (.docx)", doc_buffer,
                        f"Project_Charter_{charter_data.get('project_name', 'project').replace(' ', '_')}_{date.today()}.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        width="stretch",
                        type="primary"
                    )
                    logger.log_action(
                        user="current_user",
                        action="export_document",
                        entity="project_charter",
                        details={"project_name": charter_data.get('project_name'), "format": "docx"}
                    )

    with st.container(border=True):
        st.subheader("Comprehensive Project Report")
        export_options = st.multiselect(
            "Select sections to include in the final DOCX report:",
            ["CAPA Form", "CAPA Closure", "FMEA", "ISO 14971 Assessment", "URRA", "Vendor Email Draft", "Human Factors Report"],
            default=["CAPA Form", "CAPA Closure", "FMEA", "URRA"]
        )

        # Updated width="stretch"
        if st.button("Generate Project Summary Report", type="primary", width="stretch"):
            if not st.session_state.capa_data.get('issue_description') and "CAPA Form" in export_options:
                st.warning("Please fill out the CAPA form before generating a report that includes it.")
            else:
                with st.spinner("Generating comprehensive report..."):
                    doc_buffer = doc_generator.generate_summary_docx(st.session_state, export_options)
                    st.download_button(
                        "踏 Download Project Summary (.docx)", doc_buffer,
                        f"Project_Summary_{st.session_state.product_info['sku']}_{date.today()}.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        width="stretch"
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
        # Updated width="stretch"
        if st.button("Generate CAPA Tracker Data", width="stretch"):
            if not st.session_state.capa_data.get('issue_description'):
                st.warning("Please fill out the CAPA form first to generate tracker data.")
            else:
                with st.spinner("Generating tracker data..."):
                    excel_buffer = doc_generator.generate_capa_tracker_excel(st.session_state)
                    st.download_button(
                        "踏 Download Tracker Data (.xlsx)",
                        data=excel_buffer,
                        file_name=f"CAPA_Tracker_{st.session_state.product_info['sku']}_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch",
                        key="download_tracker"
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
            width="stretch"
        )
