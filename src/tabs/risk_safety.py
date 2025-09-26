# src/tabs/risk_safety.py

import streamlit as st
import pandas as pd

def display_risk_safety_tab():
    st.header("Risk & Safety Analysis Hub")
    if st.session_state.api_key_missing:
        st.error("AI features are disabled. Please configure your API key.")
        return

    # --- Tool 1: FMEA ---
    with st.container(border=True):
        st.subheader("Failure Mode and Effects Analysis (FMEA)")
        with st.expander("What is an FMEA?"):
            st.markdown("""
            An FMEA is a proactive method to evaluate a process for potential failures and their impacts. Use this tool to identify and prioritize risks based on Severity, Occurrence, and Detection.
            - **Severity (S):** Impact of the failure (1=Low, 5=High).
            - **Occurrence (O):** Likelihood of the failure (1=Low, 5=High).
            - **Detection (D):** How likely you are to detect the failure (1=High, 5=Low).
            **RPN = S × O × D**. Higher RPNs are higher priorities.
            """)

        c1, c2 = st.columns(2)
        if c1.button("Suggest Failure Modes with AI", width='stretch', key="fmea_ai"):
            if st.session_state.analysis_results:
                with st.spinner("AI is suggesting failure modes..."):
                    insights = st.session_state.analysis_results.get('insights', 'High return rate observed.')
                    suggestions = st.session_state.fmea_generator.suggest_failure_modes(insights, st.session_state.analysis_results)
                    df = pd.DataFrame(suggestions)
                    # Ensure score columns exist with default values
                    for col in ['Severity', 'Occurrence', 'Detection']:
                        if col not in df.columns:
                            df[col] = 1
                    st.session_state.fmea_data = df
            else:
                st.warning("Run an analysis on the dashboard first.")
        
        if c2.button("Add Manual FMEA Row", width='stretch', key="fmea_add"):
            new_row = pd.DataFrame([{"Potential Failure Mode": "", "Potential Effect(s)": "", "Severity": 1, "Potential Cause(s)": "", "Occurrence": 1, "Current Controls": "", "Detection": 1, "RPN": 1}])
            st.session_state.fmea_data = pd.concat([st.session_state.fmea_data, new_row], ignore_index=True)

        if not st.session_state.fmea_data.empty:
            edited_df = st.data_editor(st.session_state.fmea_data, column_config={
                    "Severity": st.column_config.SelectboxColumn("S", options=list(range(1, 6)), required=True),
                    "Occurrence": st.column_config.SelectboxColumn("O", options=list(range(1, 6)), required=True),
                    "Detection": st.column_config.SelectboxColumn("D", options=list(range(1, 6)), required=True),
                }, num_rows="dynamic", key="fmea_editor")
            
            edited_df['RPN'] = (
                pd.to_numeric(edited_df['Severity'], errors='coerce').fillna(1) *
                pd.to_numeric(edited_df['Occurrence'], errors='coerce').fillna(1) *
                pd.to_numeric(edited_df['Detection'], errors='coerce').fillna(1)
            ).astype(int)
            st.session_state.fmea_data = edited_df
    
    st.write("") 
    
    # --- Tool 2: ISO 14971 Risk Assessment ---
    with st.container(border=True):
        st.subheader("ISO 14971 Risk Assessment Generator")
        with st.form("risk_assessment_form"):
            st.info("Generates a formal risk assessment for a medical device according to ISO 14971.")
            ra_product_name = st.text_input("Product Name", st.session_state.target_sku)
            ra_product_desc = st.text_area("Product Description & Intended Use", height=100)
            if st.form_submit_button("Generate Risk Assessment", type="primary", width='stretch'):
                if ra_product_name and ra_product_desc:
                    with st.spinner("AI is generating the ISO 14971 assessment..."):
                        st.session_state.risk_assessment = st.session_state.risk_assessment_generator.generate_assessment(ra_product_name, st.session_state.target_sku, ra_product_desc)
                else:
                    st.warning("Please provide a product name and description.")
        
        if st.session_state.get('risk_assessment'):
            st.markdown(st.session_state.risk_assessment)

    st.write("") 

    # --- Tool 3: Use-Related Risk Analysis (URRA) ---
    with st.container(border=True):
        st.subheader("Use-Related Risk Analysis (URRA) Generator")
        with st.form("urra_form"):
            st.info("Generates a URRA based on IEC 62366 to identify risks associated with product usability.")
            urra_product_name = st.text_input("Product Name", st.session_state.target_sku, key="urra_name")
            urra_product_desc = st.text_area("Product Description & Intended Use", height=100, key="urra_desc")
            urra_user = st.text_input("Intended User Profile", placeholder="e.g., Elderly individuals with limited dexterity")
            urra_env = st.text_input("Intended Use Environment", placeholder="e.g., Home healthcare setting")
            if st.form_submit_button("Generate URRA", type="primary", width='stretch'):
                if urra_product_name and urra_product_desc and urra_user and urra_env:
                    with st.spinner("AI is generating the URRA..."):
                        st.session_state.urra = st.session_state.urra_generator.generate_urra(urra_product_name, urra_product_desc, urra_user, urra_env)
                else:
                    st.warning("Please fill in all fields to generate the URRA.")

        if st.session_state.get('urra'):
            st.markdown(st.session_state.urra)

**`src/tabs/vendor_comms.py`**
```python
# src/tabs/vendor_comms.py

import streamlit as st
from datetime import date

def display_vendor_comm_tab():
    st.header("Vendor Communications Center")
    if st.session_state.api_key_missing: st.error("AI features are disabled."); return
    if not st.session_state.analysis_results: st.info("Run an analysis on the Dashboard tab first to activate this feature."); return
    
    with st.form("vendor_email_form"):
        st.subheader("Draft a Vendor Email with AI")
        c1, c2 = st.columns(2)
        vendor_name = c1.text_input("Vendor Name")
        contact_name = c2.text_input("Contact Name")
        english_ability = st.slider("Recipient's English Proficiency", 1, 5, 3, help="1: Low, 5: High")
        
        if st.form_submit_button("Draft Email", type="primary", width='stretch'):
            with st.spinner("AI is drafting email..."):
                goal = f"Start a collaborative investigation into the recent return rate for SKU {st.session_state.target_sku}."
                st.session_state.vendor_email_draft = st.session_state.ai_email_drafter.draft_vendor_email(
                    goal, st.session_state.analysis_results, st.session_state.target_sku,
                    vendor_name, contact_name, english_ability)
    
    if st.session_state.vendor_email_draft:
        st.text_area("Generated Draft", st.session_state.vendor_email_draft, height=300)
        if st.button("Generate Formal SCAR Document"):
            with st.spinner("Generating SCAR document..."):
                st.download_button("Download SCAR (.docx)", 
                    st.session_state.doc_generator.generate_scar_docx(st.session_state.capa_data, vendor_name),
                    f"SCAR_{st.session_state.target_sku}_{date.today()}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

**`src/tabs/compliance.py`**
```python
# src/tabs/compliance.py

import streamlit as st

def display_compliance_tab():
    st.header("Compliance Center")
    if st.session_state.api_key_missing: st.error("AI features are disabled."); return

    col1, col2 = st.columns(2)
    with col1, st.container(border=True):
        st.subheader("Medical Device Classification")
        with st.form("classification_form"):
            device_desc = st.text_area("Device's intended use:", height=150, placeholder="e.g., A foam cushion for comfort in a wheelchair.")
            if st.form_submit_button("Classify Device", type="primary", width='stretch'):
                if device_desc:
                    with st.spinner("AI is classifying..."):
                        st.session_state.medical_device_classification = st.session_state.medical_device_classifier.classify_device(device_desc)
                else:
                    st.warning("Please describe the device.")
        if st.session_state.get('medical_device_classification'):
            res = st.session_state.medical_device_classification
            if "error" in res: st.error(res['error'])
            else:
                st.success(f"**Classification:** {res.get('classification', 'N/A')}")
                st.markdown(f"**Rationale:** {res.get('rationale', 'N/A')}")
    
    with col2, st.container(border=True):
        st.subheader("Pre-Mortem Analysis")
        scenario = st.text_input("Define failure scenario:", "Our new product launch failed.")
        if st.button("Generate Pre-Mortem Questions", width='stretch'):
            with st.spinner("AI is generating questions..."):
                st.session_state.pre_mortem_questions = st.session_state.pre_mortem_generator.generate_questions(scenario)
        
        if st.session_state.get('pre_mortem_questions'):
            answers = {q: st.text_area(q, key=q, label_visibility="collapsed") for q in st.session_state.pre_mortem_questions}
            if st.button("Summarize Pre-Mortem Analysis", width='stretch'):
                qa_list = [{"question": q, "answer": a} for q, a in answers.items() if a]
                if qa_list:
                    with st.spinner("AI is summarizing..."):
                        st.session_state.pre_mortem_summary = st.session_state.pre_mortem_generator.summarize_answers(qa_list)
                else:
                    st.warning("Please answer at least one question.")
        
        if st.session_state.get('pre_mortem_summary'):
            st.markdown(st.session_state.pre_mortem_summary)

**`src/tabs/cost_of_quality.py`**
```python
# src/tabs/cost_of_quality.py

import streamlit as st

def display_cost_of_quality_tab():
    st.header("Cost of Quality (CoQ) Calculator")
    st.info("Estimate the total cost of quality, broken down into prevention, appraisal, and failure costs.")

    with st.form("coq_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Prevention Costs")
            quality_planning = st.number_input("Quality Planning ($)", 0.0, step=100.0)
            training = st.number_input("Quality Training ($)", 0.0, step=100.0)
            st.subheader("Failure Costs")
            scrap_rework = st.number_input("Internal Failures ($)", 0.0, step=100.0)
            returns_warranty = st.number_input("External Failures ($)", 0.0, step=100.0)
        with c2:
            st.subheader("Appraisal Costs")
            inspection = st.number_input("Inspection & Testing ($)", 0.0, step=100.0)
            audits = st.number_input("Quality Audits ($)", 0.0, step=100.0)

        if st.form_submit_button("Calculate Cost of Quality", type="primary", width='stretch'):
            total_prevention = quality_planning + training
            total_appraisal = inspection + audits
            total_failure = scrap_rework + returns_warranty
            st.session_state.coq_results = {
                "Prevention Costs": total_prevention, "Appraisal Costs": total_appraisal,
                "Failure Costs": total_failure, "Total Cost of Quality": total_prevention + total_appraisal + total_failure
            }

    if st.session_state.get('coq_results'):
        results = st.session_state.coq_results
        st.subheader("Cost of Quality Results")
        st.metric("Total Cost of Quality", f"${results['Total Cost of Quality']:,.2f}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Prevention Costs", f"${results['Prevention Costs']:,.2f}")
        c2.metric("Appraisal Costs", f"${results['Appraisal Costs']:,.2f}")
        c3.metric("Failure Costs", f"${results['Failure Costs']:,.2f}")
        if results['Total Cost of Quality'] > 0:
            st.progress(results['Failure Costs'] / results['Total Cost of Quality'], text=f"{(results['Failure Costs']/results['Total Cost of Quality']):.1%} Failure Costs")
        if st.button("Get AI Insights on CoQ", width='stretch'):
            with st.spinner("AI is analyzing..."):
                st.markdown(st.session_state.ai_context_helper.generate_response(f"Analyze this CoQ data: {results}. Give advice on shifting spending from failure to prevention."))
