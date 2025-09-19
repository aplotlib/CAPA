# src/ai_context_helper.py

import streamlit as st
from typing import Optional, Dict
import anthropic

class AIContextHelper:
    """
    AI assistant that maintains and understands the context across all application tabs.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                st.error(f"Failed to initialize AI Context Helper: {e}")

    def get_full_context(self) -> str:
        """Gathers all available data from session state to form a comprehensive context."""
        context_parts = []
        
        context_parts.append("You are an AI assistant integrated into a Product Lifecycle & Quality Management application.")
        context_parts.append("Your goal is to provide cohesive, context-aware answers by synthesizing information from different parts of the tool.")
        context_parts.append(f"The product currently under analysis has the SKU: {st.session_state.get('target_sku', 'Not specified')}.")
        
        # Dashboard Context
        if st.session_state.get('analysis_results'):
            results = st.session_state.analysis_results
            summary = results.get('overall_summary')
            if summary is not None and not summary.empty:
                summary_data = summary.iloc[0]
                context_parts.append("\n--- DASHBOARD SUMMARY ---")
                context_parts.append(f"Overall Return Rate: {summary_data.get('return_rate', 'N/A'):.2f}%")
                context_parts.append(f"Total Sold: {int(summary_data.get('total_sold', 0))}, Total Returned: {int(summary_data.get('total_returned', 0))}")
                context_parts.append(f"AI Insights: {results.get('insights', 'N/A')}")

        # CAPA Feasibility Context
        if st.session_state.get('capa_feasibility_analysis'):
            context_parts.append("\n--- CAPA FEASIBILITY ANALYSIS ---")
            context_parts.append(st.session_state.capa_feasibility_analysis['summary'])
        
        # FMEA Context
        if st.session_state.get('fmea_data') is not None and not st.session_state.fmea_data.empty:
            context_parts.append("\n--- FMEA DATA ---")
            fmea_df = st.session_state.fmea_data
            context_parts.append("The following failure modes have been identified:")
            context_parts.append(fmea_df[['Potential Failure Mode', 'Potential Cause(s)', 'RPN']].to_string(index=False))
            if not fmea_df.empty:
                highest_risk = fmea_df.loc[fmea_df['RPN'].idxmax()]
                context_parts.append(f"The highest priority risk is '{highest_risk['Potential Failure Mode']}' with an RPN of {highest_risk['RPN']}.")

        # Pre-Mortem Context
        if st.session_state.get('pre_mortem_summary'):
            context_parts.append("\n--- PRE-MORTEM SUMMARY ---")
            context_parts.append(st.session_state.pre_mortem_summary)

        # Vendor Communication Context
        if st.session_state.get('vendor_email_draft'):
            context_parts.append("\n--- VENDOR COMMUNICATION DRAFT ---")
            context_parts.append("An email has been drafted to the vendor with the following content:")
            context_parts.append(st.session_state.vendor_email_draft)
            
        return "\n".join(context_parts)

    def generate_response(self, user_query: str) -> str:
        """Generates a response to a user query based on the full application context."""
        if not self.client:
            return "AI assistant is not available. Please configure the Anthropic API key."

        full_context = self.get_full_context()
        
        system_prompt = "You are a helpful AI assistant embedded in a quality management application. Use the provided context from the application's different tabs to answer the user's question. Be concise and helpful."

        messages = [
            {
                "role": "user",
                "content": f"Here is the full context of what is happening in the application:\n{full_context}\n\nNow, answer my question:\n{user_query}"
            }
        ]

        try:
            with st.spinner("AI is thinking..."):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=system_prompt,
                    messages=messages
                ).content[0].text
            return response
        except Exception as e:
            st.error(f"Error generating AI response: {e}")
            return "Sorry, I encountered an error while generating a response."
