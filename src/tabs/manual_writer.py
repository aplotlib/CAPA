# src/tabs/manual_writer.py

import streamlit as st

def display_manual_writer_tab():
    """
    Displays the AI-powered tool for generating a product user manual.
    """
    st.header("✍️ AI-Powered Product Manual Writer")
    st.info("This tool helps you quickly generate a draft for your product's user manual. Fill in the key details, select a language, and let the AI build the sections for you.")

    if st.session_state.api_key_missing:
        st.error("AI features are disabled. Please configure your API key to use this feature.")
        return

    # --- INITIALIZATION FIX ---
    # Ensure the container for manual content exists in session state
    if 'manual_content' not in st.session_state:
        st.session_state.manual_content = {}

    # --- Step 1: User Input ---
    with st.container(border=True):
        st.subheader("Step 1: Provide Key Product Information")
        
        # Auto-populate from sidebar info
        product_info = st.session_state.product_info
        
        with st.form("manual_input_form"):
            user_inputs = {}
            user_inputs['features'] = st.text_area(
                "**List the key features and specifications of the product.**",
                placeholder="e.g.,- Large, backlit LCD display\n- One-touch operation\n- Irregular heartbeat detector\n- Memory for 2 users (90 readings each)",
                height=150
            )
            user_inputs['instructions'] = st.text_area(
                "**Provide step-by-step operating instructions.**",
                placeholder="e.g.,1. Sit calmly for 5 minutes.\n2. Wrap the cuff around your upper arm.\n3. Press the START/STOP button to begin measurement.",
                height=200
            )
            user_inputs['warnings'] = st.text_area(
                "**List critical safety warnings and contraindications.**",
                placeholder="e.g.,- Do not use on an arm with an intravenous drip.\n- Consult your physician before use if you have a pacemaker.\n- This device is not intended for use on infants.",
                height=150
            )
            
            # Language Selection
            languages = [
                "English", "Spanish (LATAM)", "Portuguese (Brazil)", "French", 
                "German", "Italian", "Dutch"
            ]
            target_language = st.selectbox("Select Target Language", languages)

            submitted = st.form_submit_button("Generate Full Manual Draft", type="primary", use_container_width=True)
            if submitted:
                if all(user_inputs.values()):
                    with st.spinner(f"AI is writing the manual in {target_language}... This may take a moment."):
                        # Define standard manual sections
                        manual_sections = [
                            "Introduction & Intended Use",
                            "Package Contents",
                            "Product Features & Diagram",
                            "Safety Precautions & Warnings",
                            "Setup & First Use",
                            "Step-by-Step Operating Instructions",
                            "Understanding the Results",
                            "Troubleshooting Guide",
                            "Cleaning & Maintenance",
                            "Technical Specifications"
                        ]
                        
                        # Generate each section safely
                        for section in manual_sections:
                            try:
                                content = st.session_state.manual_writer.generate_manual_section(
                                    section_title=section,
                                    product_name=product_info['name'],
                                    product_ifu=product_info['ifu'],
                                    user_inputs=user_inputs,
                                    target_language=target_language
                                )
                                st.session_state.manual_content[section] = content
                            except Exception as e:
                                st.error(f"Error generating section '{section}': {e}")
                                st.session_state.manual_content[section] = "Error generating content."

                    st.success("✅ Manual draft generated successfully!")
                else:
                    st.warning("Please fill in all the product information fields to generate the manual.")
    
    # --- Step 2: Review & Edit Manual ---
    if st.session_state.get('manual_content'):
        st.divider()
        st.subheader("Step 2: Review and Edit Your Manual")
        
        for section, content in st.session_state.manual_content.items():
            with st.expander(section, expanded=False):
                st.markdown(content)
