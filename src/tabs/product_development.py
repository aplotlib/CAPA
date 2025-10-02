# src/tabs/product_development.py

import streamlit as st
import json

def display_product_development_tab():
    """
    Displays the Product Development workflow, including Design Controls Triage,
    Project Charter, R&D Hub, and AI-powered Design Controls creation.
    """
    st.header("🚀 Product Development Lifecycle Hub")
    st.info("A comprehensive toolkit for developing new products, from initial concept and risk analysis to final design controls.")

    if 'product_dev_data' not in st.session_state:
        st.session_state.product_dev_data = {}
    data = st.session_state.product_dev_data

    # Auto-populate from sidebar
    product_info = st.session_state.product_info

    # --- Step 1: Project Charter & R&D Hub ---
    with st.container(border=True):
        st.subheader("Step 1: Project Charter & R&D Hub")
        st.markdown("Define your project to prevent the 'dumpster fire' moment and centralize your research.")
        
        c1, c2 = st.columns(2)
        data['project_name'] = c1.text_input("Project Name / Objective", value=product_info.get('name', ''), key="pd_proj_name")
        data['team_members'] = c2.text_input("Team Members", key="pd_team")
        data['scope'] = st.text_area("Scope", key="pd_scope", height=100, placeholder="What's in and what's out of the project?")

        st.divider()
        st.subheader("Voice of the Customer (VOC) / Research Hub")
        st.text_area("Paste raw user feedback, competitor analysis, research notes, etc.", key="pd_voc_raw", height=200)

    # --- Step 2: Design Controls Triage ---
    with st.container(border=True):
        st.subheader("Step 2: Design Controls Triage (AI-Powered) 🧠")
        st.markdown("Determine if your product requires formal design controls under FDA 21 CFR 820.30.")
        
        with st.form("triage_form"):
            device_desc = st.text_area(
                "**Describe your product and its intended use:**",
                height=150,
                value=product_info.get('ifu', ''),
                key="pd_triage_desc"
            )
            submitted = st.form_submit_button("Analyze Requirement", type="primary", use_container_width=True)
            if submitted and not st.session_state.api_key_missing:
                if device_desc:
                    with st.spinner("AI is analyzing FDA regulations..."):
                        triage_result = st.session_state.ai_design_controls_triager.triage_device(device_desc)
                        data['triage_result'] = triage_result
                else:
                    st.warning("Please provide a product description.")

        if data.get('triage_result'):
            result = data['triage_result']
            if "error" in result:
                st.error(result['error'])
            else:
                st.subheader("Triage Recommendation")
                st.success(f"**{result.get('recommendation')}**")
                st.markdown(f"**Rationale:** {result.get('rationale')}")
                st.markdown(f"**Next Steps:** {result.get('next_steps')}")

    # --- Step 3: AI-Powered Design Controls Generation ---
    with st.container(border=True):
        st.subheader("Step 3: Generate Design Controls with AI ✍️")
        st.info("Answer a few key questions to generate a comprehensive draft of your design controls documentation.")
        with st.form("ai_dc_form"):
            user_needs = st.text_area("What are the core user needs the device must meet?", 
                                      placeholder="e.g., The user needs to easily and accurately measure their blood pressure at home without assistance. The device must be comfortable and provide a clear, easy-to-read result.")
            tech_reqs = st.text_area("What are the key technical requirements or specifications?",
                                     placeholder="e.g., Must comply with AAMI standards for accuracy. Cuff must fit arm circumferences from 9-17 inches. Battery must last for at least 200 measurements.")
            risks = st.text_area("What are the most significant known risks or failure modes?",
                                 placeholder="e.g., Risk of inaccurate readings leading to improper medical decisions. Risk of cuff over-inflation causing discomfort. Risk of software malfunction.")
            
            submitted_dc = st.form_submit_button("Generate Full Design Controls Draft", use_container_width=True, type="primary")
            if submitted_dc and not st.session_state.api_key_missing:
                if all([user_needs, tech_reqs, risks]):
                    with st.spinner("AI is drafting the Design Controls documentation..."):
                        dc_draft = st.session_state.ai_design_controls_triager.generate_design_controls(
                            product_info.get('name'), product_info.get('ifu'), user_needs, tech_reqs, risks
                        )
                        if dc_draft and "error" not in dc_draft:
                            data['design_controls'] = dc_draft
                            st.success("✅ AI draft generated! Review and edit in Step 4.")
                        else:
                            st.error(f"Failed to generate draft: {dc_draft.get('error', 'Unknown error')}")
                else:
                    st.warning("Please fill out all fields to generate the draft.")

    # --- Step 4: Review & Edit Design Controls ---
    with st.expander("🛠️ Step 4: Review & Edit Design Controls Document", expanded=True):
        if 'design_controls' in data and data['design_controls']:
            dc_data = data['design_controls']
            st.text_area("Design & Development Plan", value=dc_data.get('plan', ''), height=150, key="dc_plan")
            st.text_area("Design Inputs (User Needs, Requirements)", value=dc_data.get('inputs', ''), height=150, key="dc_inputs")
            st.text_area("Design Outputs (Specifications, Drawings)", value=dc_data.get('outputs', ''), height=150, key="dc_outputs")
            st.text_area("Design Verification Plan ('Did we build the product right?')", value=dc_data.get('verification', ''), height=150, key="dc_verification")
            st.text_area("Design Validation Plan ('Did we build the right product?')", value=dc_data.get('validation', ''), height=150, key="dc_validation")
            st.text_area("Design Transfer Plan", value=dc_data.get('transfer', ''), height=150, key="dc_transfer")
            st.text_area("Design History File (DHF) Summary", value=dc_data.get('dhf', ''), height=150, key="dc_dhf")
        else:
            st.info("Generate the AI draft in Step 3 to populate this section, or fill it in manually.")
            st.text_area("Design & Development Plan", key="dc_plan_manual", height=150)
            st.text_area("Design Inputs (User Needs, Requirements)", key="dc_inputs_manual", height=150)
            st.text_area("Design Outputs (Specifications, Drawings)", key="dc_outputs_manual", height=150)
            st.text_area("Design Verification Plan ('Did we build the product right?')", key="dc_verification_manual", height=150)
            st.text_area("Design Validation Plan ('Did we build the right product?')", key="dc_validation_manual", height=150)
