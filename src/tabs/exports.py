# src/tabs/exports.py

import streamlit as st
from datetime import date

def display_exports_tab():
    st.header("Document Exports")
    st.info("Generate a single, comprehensive project summary document.")
    
    export_options = st.multiselect(
        "Select sections to include in the final report:",
        ["CAPA Form", "FMEA", "ISO 14971 Assessment", "URRA", "Vendor Email Draft", "Human Factors Report"],
        default=["CAPA Form", "FMEA", "Human Factors Report"]
    )

    if st.button("Generate Project Summary Report (.docx)", type="primary"):
        if not st.session_state.capa_data.get('issue_description') and "CAPA Form" in export_options:
            st.warning("Please fill out the CAPA form before generating a report that includes it.")
        else:
            with st.spinner("Generating comprehensive report..."):
                doc_buffer = st.session_state.doc_generator.generate_summary_docx(st.session_state, export_options)
                st.download_button(
                    "Download Project Summary", doc_buffer,
                    f"Project_Summary_{st.session_state.target_sku}_{date.today()}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
