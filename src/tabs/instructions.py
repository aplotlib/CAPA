# src/tabs/instructions.py

import streamlit as st

def display_instructions_tab():
    st.header("📘 Start Here: User Guide & Workflow")
    st.markdown("""
    Welcome to **ORION QMS**. This AI-assisted platform helps you manage quality processes, generate documentation, 
    and maintain compliance (ISO 13485 / FDA 21 CFR 820).
    """)

    st.subheader("Recommended Workflow")
    st.info("Follow this path to effectively manage a quality event from initiation to closure.")

    # Mermaid diagram for visual workflow
    st.markdown(
        """
        ```mermaid
        graph TD
            A[1. Mission Control] -->|Identify Trends| B[2. CAPA / Risk Hub]
            B -->|Investigate & Root Cause| C[3. Drafting]
            C -->|AI Suggestions & Voice Input| C
            C -->|Generate Documents| D[4. Exports]
            D -->|Download DOCX Draft| E[5. External Review]
            E -->|Approve via Google Docs/Word| F[6. Final Closure]
            F -->|Update Status| B
        ```
        """,
        unsafe_allow_html=True
    )

    with st.expander("STEP 1: Dashboard & Monitoring", expanded=True):
        st.markdown("""
        - Go to **Mission Control**.
        - Upload sales/returns data to identify trends.
        - If a KPI (like Return Rate) exceeds the threshold, initiate a CAPA.
        """)

    with st.expander("STEP 2: CAPA & Investigation"):
        st.markdown("""
        - Navigate to **Quality Management > CAPA Lifecycle**.
        - Use **Voice-to-Text** to quickly describe the issue.
        - Use **Root Cause Tools** (Fishbone/5 Whys) to dig deeper.
        - Use **AI Suggestions** to draft professional corrective actions.
        """)

    with st.expander("STEP 3: Risk Analysis"):
        st.markdown("""
        - Go to **Risk & Safety**.
        - Update your FMEA (Failure Mode and Effects Analysis) based on the new issue.
        - Ensure the Risk Priority Number (RPN) is acceptable.
        """)

    with st.expander("STEP 4: Export & Review (Critical)"):
        st.markdown("""
        - Go to **Mission Control > Data Exports**.
        - Select the sections you want (CAPA Form, FMEA, Investigation).
        - **Download the DOCX**.
        - **External Review:** Upload to Google Docs or Sharepoint. Have your Quality Review Board (QRB) comment and approve the document outside of this app.
        """)

    with st.expander("STEP 5: Closure"):
        st.markdown("""
        - Once approved externally, return to the **CAPA Lifecycle** tab.
        - Enter the **Closure Date** and final signatures.
        - The system will log this in the Audit Trail.
        """)
