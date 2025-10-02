# src/tabs/vendor_comms.py

import streamlit as st
from datetime import date

def display_vendor_comm_tab():
    st.header("Vendor Communications Center")

    if st.session_state.api_key_missing:
        st.error("AI features are disabled. Please configure your API key in the sidebar.")
        return
        
    if not st.session_state.get('analysis_results'):
        st.info("Run an analysis on the Dashboard tab first to activate this feature.")
        return
    
    with st.form("vendor_email_form"):
        st.subheader("Draft a Vendor Email with AI")
        c1, c2 = st.columns(2)
        vendor_name = c1.text_input("Vendor Name")
        contact_name = c2.text_input("Contact Name")
        english_ability = st.slider("Recipient's English Proficiency", 1, 5, 3, help="1: Low, 5: High")
        
        if st.form_submit_button("Draft Email", type="primary", use_container_width=True):
            with st.spinner("AI is drafting email..."):
                # FIX: Correctly access the SKU from product_info
                sku = st.session_state.product_info['sku']
                goal = f"Start a collaborative investigation into the recent return rate for SKU {sku}."
                st.session_state.vendor_email_draft = st.session_state.ai_email_drafter.draft_vendor_email(
                    goal, st.session_state.analysis_results, sku,
                    vendor_name, contact_name, english_ability)
    
    if st.session_state.get('vendor_email_draft'):
        st.text_area("Generated Draft", st.session_state.vendor_email_draft, height=300)
        
        # Allow SCAR generation from here
        if 'capa_data' in st.session_state and st.session_state.capa_data.get('issue_description'):
            scar_buffer = st.session_state.doc_generator.generate_scar_docx(st.session_state.capa_data, vendor_name or "Vendor")
            st.download_button(
                "Download Formal SCAR (.docx)", 
                data=scar_buffer,
                file_name=f"SCAR_{st.session_state.product_info['sku']}_{date.today()}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        else:
            st.warning("Please fill out the CAPA form before generating a SCAR.")
