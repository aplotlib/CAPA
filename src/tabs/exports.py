# src/tabs/exports.py

import streamlit as st
from datetime import date
from audit_logger import AuditLogger
from exporter import UniversalExporter

def display_exports_tab():
    st.header("📄 Document Exports")
    st.info("Generate a single, comprehensive project summary document by selecting the sections you want to include.")
    
    logger = AuditLogger()
    exporter = UniversalExporter()

    with st.container(border=True):
        export_options = st.multiselect(
            "Select sections to include in the final report:",
            ["CAPA Form", "CAPA Closure", "FMEA", "ISO 14971 Assessment", "URRA", "Vendor Email Draft", "Human Factors Report"],
            default=["CAPA Form", "CAPA Closure", "FMEA"]
        )

        export_format = st.selectbox("Select export format:", ["docx", "pdf", "xlsx"])

        if st.button("Generate Project Summary Report", type="primary", use_container_width=True):
            if not st.session_state.capa_data.get('issue_description') and "CAPA Form" in export_options:
                st.warning("Please fill out the CAPA form before generating a report that includes it.")
            else:
                with st.spinner("Generating comprehensive report..."):
                    if export_format == "docx":
                        doc_buffer = st.session_state.doc_generator.generate_summary_docx(st.session_state, export_options)
                        st.download_button(
                            "📥 Download Project Summary (.docx)", doc_buffer,
                            f"Project_Summary_{st.session_state.product_info['sku']}_{date.today()}.docx",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                    elif export_format == "pdf":
                        pdf_buffer = exporter.export_to_pdf(st.session_state.capa_data)
                        st.download_button(
                            "📥 Download Project Summary (.pdf)", pdf_buffer,
                            f"Project_Summary_{st.session_state.product_info['sku']}_{date.today()}.pdf",
                            "application/pdf",
                            use_container_width=True
                        )
                    elif export_format == "xlsx":
                        excel_buffer = exporter.export_to_excel(st.session_state.capa_data)
                        st.download_button(
                            "📥 Download Project Summary (.xlsx)", excel_buffer,
                            f"Project_Summary_{st.session_state.product_info['sku']}_{date.today()}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    logger.log_action(
                        user="current_user",
                        action="export_document",
                        entity="project_summary",
                        details={"sections": export_options, "format": export_format}
                    )
                    
                    audit_log_csv = logger.get_audit_log_csv()
                    st.download_button(
                        label="Download Audit Trail (CSV)",
                        data=audit_log_csv,
                        file_name=f"audit_trail_{date.today()}.csv",
                        mime="text/csv",
                    )
