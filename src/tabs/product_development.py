# src/tabs/product_development.py

import streamlit as st
import json

def display_product_development_tab():
    """
    Displays the Product Development workflow, including Design Controls Triage,
    Project Charter, R&D Hub, and AI-powered Design Controls creation.
    """
    st.header("🚀 Product Development Lifecycle Hub")
    st.info(
        "This streamlined workflow automates key regulatory documentation for Class I & II medical devices. "
        "Define your product, and the AI will generate a draft of your Design Controls and a Traceability Matrix."
    )

    if 'product_dev_data' not in st.session_state:
        st.session_state.product_dev_data = {}
    data = st.session_state.product_dev_data

    # Auto-populate from sidebar
    product_info = st.session_state.product_info

    # --- Step 1: Project Definition ---
    with st.container(border=True):
        st.subheader("Step 1: Define Your Project")
        st.markdown("Provide the core requirements for your device. This information will be used by the AI to generate your design control documentation.")
        
        with st.form("ai_dc_form"):
            user_needs = st.text_area("1. What are the core **User Needs** the device must meet?",
                                      placeholder="Example: The user needs to easily and accurately measure their blood pressure at home without assistance. The device must be comfortable and provide a clear, easy-to-read result.",
                                      height=150)
            tech_reqs = st.text_area("2. What are the key **Technical & Functional Requirements**?",
                                     placeholder="Example: Must comply with AAMI standards for accuracy. Cuff must fit arm circumferences from 9-17 inches. Battery must last for at least 200 measurements. Must sync with an iOS/Android app via Bluetooth.",
                                     height=150)
            risks = st.text_area("3. What are the most significant **Known Risks or Failure Modes**?",
                                 placeholder="Example: Risk of inaccurate readings leading to improper medical decisions. Risk of cuff over-inflation causing discomfort. Risk of software malfunction or data breach.",
                                 height=150)
            
            submitted_dc = st.form_submit_button("🤖 Generate Design Controls & Traceability Matrix", use_container_width=True, type="primary")
            if submitted_dc and not st.session_state.api_key_missing:
                if all([user_needs, tech_reqs, risks]):
                    with st.spinner("AI is drafting the Design Controls and Traceability Matrix..."):
                        dc_draft = st.session_state.ai_design_controls_triager.generate_design_controls(
                            product_info.get('name'), product_info.get('ifu'), user_needs, tech_reqs, risks
                        )
                        if dc_draft and "error" not in dc_draft:
                            data['design_controls'] = dc_draft
                            st.success("✅ AI draft generated! Review the sections below.")
                        else:
                            st.error(f"Failed to generate draft: {dc_draft.get('error', 'Unknown error')}")
                else:
                    st.warning("Please fill out all three fields to generate the draft.")

    # --- Step 2: Review & Edit Design Controls ---
    if 'design_controls' in data and data['design_controls']:
        st.divider()
        st.subheader("Step 2: Review AI-Generated Documentation")
        dc_data = data['design_controls']

        with st.expander("Traceability Matrix Summary", expanded=True):
            st.markdown(dc_data.get('traceability_matrix', "No traceability matrix was generated."))

        with st.expander("Design Inputs (User Needs, Requirements)", expanded=False):
            st.markdown(dc_data.get('inputs', "No data generated."))
            
        with st.expander("Design Outputs (Specifications, Drawings)", expanded=False):
            st.markdown(dc_data.get('outputs', "No data generated."))
            
        with st.expander("Design Verification Plan ('Did we build the product right?')", expanded=False):
            st.markdown(dc_data.get('verification', "No data generated."))
            
        with st.expander("Design Validation Plan ('Did we build the right product?')", expanded=False):
            st.markdown(dc_data.get('validation', "No data generated."))

        with st.expander("Design & Development Plan", expanded=False):
            st.markdown(dc_data.get('plan', "No data generated."))
            
        with st.expander("Design Transfer Plan", expanded=False):
            st.markdown(dc_data.get('transfer', "No data generated."))
            
        with st.expander("Design History File (DHF) Summary", expanded=False):
            st.markdown(dc_data.get('dhf', "No data generated."))

    else:
        st.info("Fill out the form in Step 1 to generate your design control documents.")
