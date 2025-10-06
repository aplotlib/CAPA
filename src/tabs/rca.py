# src/tabs/rca.py

import streamlit as st
from src.rca_tools import RootCauseAnalyzer

def display_rca_tab():
    """
    Displays the fully implemented Root Cause Analysis tab with interactive
    5 Whys and Fishbone Diagram tools.
    """
    st.header("🔬 Root Cause Analysis (RCA) Tools")
    st.info("Use these guided tools to conduct a thorough Root Cause Analysis.")

    if st.session_state.api_key_missing:
        st.error("AI features are disabled. Please configure your API key to use these tools.")
        return

    # Initialize the RCA tool analyzer
    # This now points to the class that contains the logic for the tools
    try:
        analyzer = st.session_state.rca_helper
    except AttributeError:
        st.error("RCA helper not initialized. Please check the main application file.")
        return

    # Initialize session state variables for the tools
    if 'whys' not in st.session_state:
        st.session_state.whys = []
    if 'fishbone_causes' not in st.session_state:
        st.session_state.fishbone_causes = {}


    # --- Tool 1: Guided 5 Whys Analysis ---
    with st.container(border=True):
        st.subheader("Guided 5 Whys Analysis")
        st.markdown("Iteratively ask 'Why?' to explore the cause-and-effect relationships underlying a problem.")

        with st.form("five_whys_form"):
            initial_problem = st.text_input(
                "**Problem Statement**",
                placeholder="Example: The new batch of devices has a 15% failure rate during final inspection."
            )
            submitted = st.form_submit_button("Start Analysis")
            if submitted and initial_problem:
                st.session_state.whys = [{"question": "Why?", "answer": initial_problem}]

        if st.session_state.whys:
            for i, why in enumerate(st.session_state.whys):
                st.markdown(f"**Why #{i+1}**: {why['answer']}")
                if i + 1 < 5:
                    next_answer = st.text_area(f"Answer to 'Why did that happen?'", key=f"why_ans_{i}")

                    if st.button(f"🤖 Get AI Suggestion for Next 'Why'", key=f"why_ai_{i}"):
                        with st.spinner("AI is thinking..."):
                            suggestion = analyzer.suggest_next_why(why['answer'])
                            st.info(f"**AI Suggestion**: {suggestion}")

                    if st.button(f"Add to Analysis", key=f"why_add_{i}"):
                        if next_answer:
                            if len(st.session_state.whys) == i + 1:
                                st.session_state.whys.append({"question": "Why?", "answer": next_answer})
                                st.rerun()
                        else:
                            st.warning("Please provide an answer.")

            st.markdown("---")
            st.markdown("#### **Root Cause Analysis Summary**")
            summary = " → ".join([w['answer'] for w in st.session_state.whys])
            st.success(f"**Potential Root Cause Path**: {summary}")

    st.write("") # Spacer

    # --- Tool 2: Fishbone (Ishikawa) Diagram Generator ---
    with st.container(border=True):
        st.subheader("Fishbone Diagram (Ishikawa) Generator")
        st.markdown("Brainstorm potential causes of a problem by organizing them into specific categories.")

        with st.form("fishbone_form"):
            fishbone_problem = st.text_input(
                "**Problem Statement (Effect)**",
                placeholder="Example: Customers are reporting the device battery life is shorter than advertised."
            )
            categories = st.multiselect(
                "**Select Cause Categories**",
                ["Machine (Equipment)", "Method (Process)", "Material", "Manpower (People)", "Measurement", "Environment"],
                default=["Machine (Equipment)", "Method (Process)", "Material", "Manpower (People)"]
            )
            submitted_fishbone = st.form_submit_button("Build Diagram Structure")
            if submitted_fishbone:
                st.session_state.fishbone_causes = {cat: [] for cat in categories}

        if st.session_state.fishbone_causes:
            for category in st.session_state.fishbone_causes:
                with st.expander(f"**{category}** Causes"):
                    current_causes = st.session_state.fishbone_causes.get(category, [])
                    cause_input = st.text_input(f"Add a cause for {category}", key=f"cause_{category}")
                    c1, c2 = st.columns(2)
                    if c1.button(f"Add Cause", key=f"add_cause_{category}"):
                        if cause_input and cause_input not in current_causes:
                            st.session_state.fishbone_causes[category].append(cause_input)
                            st.rerun()

                    if c2.button(f"🤖 Get AI Suggestions", key=f"ai_cause_{category}"):
                        with st.spinner(f"AI is brainstorming causes for {category}..."):
                            suggestions = analyzer.suggest_fishbone_causes(fishbone_problem, category)
                            for s in suggestions:
                                if s not in st.session_state.fishbone_causes[category]:
                                    st.session_state.fishbone_causes[category].append(s)
                            st.rerun()

                    for cause in current_causes:
                        st.markdown(f"- {cause}")

            if st.button("Generate Final Diagram", type="primary"):
                st.session_state.final_fishbone = analyzer.generate_fishbone_markdown(fishbone_problem, st.session_state.fishbone_causes)

        if 'final_fishbone' in st.session_state:
            st.markdown("---")
            st.markdown("### Fishbone Diagram")
            st.markdown(st.session_state.final_fishbone)
