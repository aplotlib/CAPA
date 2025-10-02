# src/tabs/product_development.py

import streamlit as st
import json

def display_product_development_tab():
    """
    Displays the Product Development workflow, including Design Controls Triage,
    Project Charter, R&D Hub, and Design Controls creation.
    """
    st.header("🚀 Product Development Workflow")
    st.info("A hyper-focused toolkit for documenting changes, conducting R&D, and managing design controls.")

    if 'product_dev_data' not in st.session_state:
        st.session_state.product_dev_data = {}
    data = st.session_state.product_dev_data

    # --- Step 1: Design Controls Triage ---
    with st.container(border=True):
        st.subheader("Step 1: Design Controls Triage (AI-Powered) 🧠")
        st.markdown("Determine if your product requires formal design controls under FDA 21 CFR 820.30.")
        
        with st.form("triage_form"):
            device_desc = st.text_area(
                "**Describe your product and its intended use:**",
                height=150,
                placeholder="e.g., A battery-powered, handheld massager intended for temporary relief of minor muscle aches and pains."
            )
            submitted = st.form_submit_button("Analyze Requirement", type="primary", use_container_width=True)
            if submitted:
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

    # --- Step 2: Project Charter & R&D Hub ---
    with st.expander("📝 Step 2: Project Charter & R&D Hub"):
        st.markdown("Define your project to prevent the 'dumpster fire' moment and centralize your research.")
        
        st.text_input("Project Name / Objective", key="pd_project_name")
        st.text_area("Scope", key="pd_scope", height=100)
        st.text_input("Team Members", key="pd_team")

        st.divider()
        st.subheader("R&D Hub / Voice of the Customer (VOC)")
        st.text_area("Paste raw user feedback, competitor analysis, research notes, etc.", key="pd_voc_raw", height=200)

    # --- Step 3: Risk Assessment (FMEA) ---
    with st.expander("⚠️ Step 3: Risk Assessment (FMEA)"):
        st.info("Proactively identify and mitigate risks. This section is linked to the main Risk & Safety tab.")
        from .risk_safety import display_risk_safety_tab # Import locally to avoid circularity
        display_risk_safety_tab()

    # --- Step 4: Create Design Controls ---
    with st.expander("🛠️ Step 4: Create Design Controls"):
        st.warning("Based on your triage, you can begin documenting design controls here.")
        
        st.text_area("Design & Development Plan", key="dc_plan", height=150)
        st.text_area("Design Inputs (User Needs, Requirements)", key="dc_inputs", height=150)
        st.text_area("Design Outputs (Specifications, Drawings)", key="dc_outputs", height=150)
        st.text_area("Design Verification Plan ('Did we build the product right?')", key="dc_verification", height=150)
        st.text_area("Design Validation Plan ('Did we build the right product?')", key="dc_validation", height=150)
