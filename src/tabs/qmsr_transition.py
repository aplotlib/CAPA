# src/tabs/qmsr_transition.py

import streamlit as st
from datetime import datetime
import time

def calculate_countdown():
    """Calculates the time remaining until Feb 2, 2026."""
    target_date = datetime(2026, 2, 2)
    now = datetime.now()
    remaining = target_date - now
    return remaining.days

def display_qmsr_transition_tab():
    # --- Custom CSS for "Dark Mode Hero" and Teal Accents ---
    st.markdown("""
        <style>
        .hero-section {
            background-color: #0f172a;
            padding: 2rem;
            border-radius: 10px;
            color: white;
            margin-bottom: 2rem;
            text-align: center;
        }
        .hero-title {
            font-size: 3rem;
            font-weight: 800;
            color: #00BFA5; /* Teal */
        }
        .hero-sub {
            font-size: 1.2rem;
            color: #cbd5e1;
        }
        .countdown-box {
            background-color: #1e293b;
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid #00BFA5;
            margin-top: 1.5rem;
            display: inline-block;
        }
        .card-red {
            border-left: 5px solid #ef4444;
            background-color: #2b1d1d;
            padding: 1rem;
            border-radius: 5px;
        }
        .highlight-teal {
            color: #00BFA5;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    days_left = calculate_countdown()
    
    st.markdown(f"""
        <div class="hero-section">
            <div class="hero-title">The Rules of the Game Are Changing.</div>
            <div class="hero-sub">FDA Harmonization: QSR to QMSR Transition</div>
            <div class="countdown-box">
                <h2>⏱️ {days_left} Days Remaining</h2>
                <p>Target Date: February 2, 2026</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Progress Bar
    st.markdown("**Transition Readiness Progress**")
    st.progress(0.35, text="35% Complete - Analysis Phase")

    st.divider()

    # --- NAVIGATION TABS ---
    tab_overview, tab_prod_dev, tab_supply, tab_action = st.tabs([
        "📖 Overview", "🧬 Product Development", "📦 Supply Chain", "✅ Action Plan"
    ])

    # --- TAB 1: OVERVIEW ---
    with tab_overview:
        st.subheader("The Shift: Compliance vs. Patient Safety")
        st.info("The FDA is retiring the old Quality System Regulation (QSR) and enforcing the new Quality Management System Regulation (QMSR). We are no longer just documenting quality. We are required to thoroughly document and mitigate risk.")

        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("### ❌ The Old Way (QSR)")
                st.markdown("""
                - **Focus:** "Check-the-box" compliance.
                - **Method:** Rigid SOPs.
                - **Goal:** Pass the audit.
                """)
        with c2:
            with st.container(border=True):
                st.markdown(f"### <span style='color:#00BFA5'>✅ The New Way (QMSR/ISO 13485)</span>", unsafe_allow_html=True)
                st.markdown("""
                - **Focus:** Risk-based thinking.
                - **Method:** Flexible, scalable processes.
                - **Goal:** Patient Safety & Product Quality.
                """)

    # --- TAB 2: PRODUCT DEVELOPMENT ---
    with tab_prod_dev:
        st.subheader("The Golden Thread")
        st.markdown("""
        In the new QMSR era, you must prove that **every safety risk** is visually linked to a specific **design feature** and **test**.
        """)
        
        # Visual Flow representation
        st.markdown("""
        ```mermaid
        graph LR
            A[⚠️ Hazard Analysis] -->|Mitigation| B[📐 Design Input]
            B -->|Traceability| C[🧪 Verification Test]
            C -->|Evidence| D[✅ Safe Product]
            style A fill:#2b1d1d,stroke:#ef4444,stroke-width:2px
            style B fill:#0f172a,stroke:#00BFA5,stroke-width:2px
            style C fill:#0f172a,stroke:#00BFA5,stroke-width:2px
            style D fill:#00BFA5,color:#fff,stroke:#fff
        ```
        """, unsafe_allow_html=True)
        
        st.markdown("### Key Action")
        st.warning("Ensure your Design History File (DHF) explicitly maps Hazards -> Inputs -> Outputs -> Verifications.")

    # --- TAB 3: SUPPLY CHAIN ---
    with tab_supply:
        st.subheader("Supplier Risk is Design Risk")
        
        # Exactech Case Study - Red Alert Style
        st.markdown("""
        <div class="card-red">
            <h3>🚨 The Exactech Scenario</h3>
            <p>For 20 years, a supplier provided vacuum bags missing an oxygen barrier layer. 
            This led to oxidation of polyethylene inserts and eventual device failure in patients.</p>
            <p><strong>Lesson:</strong> Purchasing controls must be risk-based, not just price-based.</p>
        </div>
        <br>
        """, unsafe_allow_html=True)

        st.markdown("### Required Changes")
        st.markdown("- **Update Quality Agreements**: Suppliers must notify us of *any* process changes.")
        st.markdown("- **Risk-Based Audits**: High-risk suppliers (sterilization, implants) need on-site audits, not just paper surveys.")

    # --- TAB 4: INTERACTIVE ACTION PLAN ---
    with tab_action:
        st.subheader("🚀 Q1 Transition Action Plan")
        st.caption("Interactive Checklist - Click to mark complete.")

        # Initialize checklist state if not exists
        if 'qmsr_checklist' not in st.session_state:
            st.session_state.qmsr_checklist = {
                "hazard_analysis": False,
                "risk_controls": False,
                "quality_agreements": False,
                "supplier_fmea": False,
                "management_signals": False
            }

        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### Product Team")
            st.session_state.qmsr_checklist['hazard_analysis'] = st.checkbox(
                "Perform Hazard Analysis before User Needs", 
                value=st.session_state.qmsr_checklist['hazard_analysis']
            )
            st.session_state.qmsr_checklist['risk_controls'] = st.checkbox(
                "Link Risk Controls to Design Inputs", 
                value=st.session_state.qmsr_checklist['risk_controls']
            )

        with col_b:
            st.markdown("#### Supply Chain")
            st.session_state.qmsr_checklist['quality_agreements'] = st.checkbox(
                "Update Quality Agreements for Change Notification", 
                value=st.session_state.qmsr_checklist['quality_agreements']
            )
            st.session_state.qmsr_checklist['supplier_fmea'] = st.checkbox(
                "Review Supplier Process FMEAs", 
                value=st.session_state.qmsr_checklist['supplier_fmea']
            )

        st.markdown("#### Management")
        st.session_state.qmsr_checklist['management_signals'] = st.checkbox(
            "Add Supplier Signals to Quarterly Review", 
            value=st.session_state.qmsr_checklist['management_signals']
        )
        
        # Calculate completion for this specific checklist
        total_items = len(st.session_state.qmsr_checklist)
        completed_items = sum(st.session_state.qmsr_checklist.values())
        
        if completed_items == total_items:
            st.balloons()
            st.success("🎉 Q1 Action Plan Complete!")
        else:
            st.progress(completed_items / total_items, text=f"{completed_items}/{total_items} Actions Completed")

    # --- FOOTER ---
    st.divider()
    st.markdown("📧 **Questions?** Contact: Jessica.Marshall@vivehealth.com | Alexander.Popoff@vivehealth.com")
