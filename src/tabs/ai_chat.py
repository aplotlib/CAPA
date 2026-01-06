import streamlit as st
from src.ai_services import get_ai_service

def display_chat_interface():
    st.header("💬 Regulatory AI Assistant")
    st.caption("Discuss search findings, draft emails, or analyze regulatory risks.")

    ai = get_ai_service()
    if not ai:
        st.warning("⚠️ AI Service not initialized. Please check your API Key.")
        return

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I've reviewed the regulatory data found in your current session. How can I assist you with it?"}
        ]

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Ask about recalls, regulations, or draft a response..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing context..."):
                
                # Gather Context from Session State (The "Review" capability)
                context_str = "CURRENT SESSION CONTEXT:\n"
                
                # 1. Product Info
                p_info = st.session_state.get('product_info', {})
                if p_info:
                    context_str += f"Target Product: {p_info.get('name', 'Unknown')}\n"

                # 2. Search Findings
                if 'recall_hits' in st.session_state and not st.session_state.recall_hits.empty:
                    hits = st.session_state.recall_hits
                    # Summarize top 5 findings for the LLM
                    top_findings = hits.head(5).to_dict(orient='records')
                    context_str += f"\nTOP 5 SEARCH FINDINGS:\n{str(top_findings)}\n"
                    context_str += f"\nTotal Records Found: {len(hits)}\n"
                else:
                    context_str += "\nNo search results found in current session.\n"

                # 3. Chat Logic
                full_prompt = f"""
                {context_str}
                
                USER QUERY:
                {prompt}
                
                TASK:
                You are a Senior Regulatory Affairs Specialist. Answer the user's query based on the Context provided.
                If drafting text (emails, CAPAs), be professional and precise.
                """
                
                response = ai._generate_text(full_prompt, system_instruction="You are a helpful Regulatory Assistant.")
                st.markdown(response)
                
                # Add assistant response to history
                st.session_state.messages.append({"role": "assistant", "content": response})
