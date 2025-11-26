# src/tabs/chat_support.py

import streamlit as st
import time

def display_chat_support_tab():
    st.header("💬 ORION AI Support")
    st.caption("Ask me anything about how to use this tool, quality regulations (ISO 13485), or how to fix a specific error.")

    if st.session_state.api_key_missing:
        st.error("AI features are disabled. Please configure your API key.")
        return

    # Initialize chat history for the support bot specifically
    if "support_messages" not in st.session_state:
        st.session_state.support_messages = [
            {"role": "assistant", "content": "Hello! I am your QMS Copilot. How can I help you navigate the app or solve a quality issue today?"}
        ]

    # Display chat messages
    for message in st.session_state.support_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Ask a question..."):
        # Add user message
        st.session_state.support_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            with st.spinner("Consulting the manual..."):
                # We use the context helper but override the system prompt for "Support" mode
                try:
                    # Construct a specific prompt for tool support
                    context_helper = st.session_state.ai_context_helper
                    
                    system_prompt = """
                    You are the expert user guide for the ORION QMS application.
                    Your goal is to help the user navigate the tool, understand features like CAPA, FMEA, and Design Controls,
                    and provide general advice on ISO 13485/FDA compliance.
                    
                    Key App Features to know:
                    - 'Mission Control': Dashboard for data and exports.
                    - 'CAPA Lifecycle': Managing non-conformities (has voice input).
                    - 'Root Cause Tools': 5 Whys and Fishbone diagrams.
                    - 'Manual Writer': Generates user manuals.
                    
                    Keep answers helpful, concise, and friendly.
                    """
                    
                    # We bypass the helper's default method to allow a custom system prompt here, 
                    # or we can use the helper if we add a 'system_override' arg. 
                    # For simplicity, we call the client directly here or rely on the helper's general knowledge.
                    # Let's use the helper's client directly for this specific chat interface.
                    
                    response = context_helper.client.chat.completions.create(
                        model=context_helper.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    full_response = response.choices[0].message.content
                    message_placeholder.markdown(full_response)
                except Exception as e:
                    full_response = f"I'm having trouble connecting to my knowledge base. Error: {e}"
                    message_placeholder.error(full_response)
        
        st.session_state.support_messages.append({"role": "assistant", "content": full_response})
