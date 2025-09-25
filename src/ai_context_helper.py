# src/ai_context_helper.py

import streamlit as st
from typing import Optional, Dict
import openai
import pandas as pd
from .utils import retry_with_backoff

class AIContextHelper:
    """
    AI assistant that uses OpenAI to understand the context across all application tabs.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                st.error(f"Failed to initialize OpenAI Client: {e}")

    def get_full_context(self) -> str:
        """Gathers all available data from session state to form a comprehensive context."""
        context_parts = []
        
        context_parts.append("You are an AI assistant integrated into a Product Lifecycle & Quality Management application called A.Q.M.S.")
        context_parts.append("Your goal is to provide cohesive, context-aware answers by synthesizing information from different parts of the tool.")
        
        target_sku = st.session_state.get('target_sku', 'Not specified')
        if target_sku:
            context_parts.append(f"The product currently under analysis has the SKU: {target_sku}.")
        
        # Dashboard Context
        if st.session_state.get('analysis_results'):
            results = st.session_state.analysis_results
            summary_df = results.get('return_summary')
            if summary_df is not None and not summary_df.empty:
                sku_specific_summary = summary_df[summary_df['sku'] == target_sku]
                if not sku_specific_summary.empty:
                    summary_data = sku_specific_summary.iloc[0]
                    context_parts.append("\n--- DASHBOARD SUMMARY ---")
                    context_parts.append(f"Overall Return Rate: {summary_data.get('return_rate', 'N/A'):.2f}%")
                    context_parts.append(f"Total Sold: {int(summary_data.get('total_sold', 0))}, Total Returned: {int(summary_data.get('total_returned', 0))}")
                    context_parts.append(f"AI Insights: {results.get('insights', 'N/A')}")

        # FMEA Context
        if st.session_state.get('fmea_data') is not None:
            fmea_df = st.session_state.fmea_data
            if isinstance(fmea_df, pd.DataFrame) and not fmea_df.empty:
                context_parts.append("\n--- FMEA DATA ---")
                context_parts.append("The following failure modes have been identified:")
                fmea_context_df = fmea_df[['Potential Failure Mode', 'Potential Cause(s)', 'RPN']]
                context_parts.append(fmea_context_df.to_string(index=False))
                if 'RPN' in fmea_df.columns and fmea_df['RPN'].notna().any():
                    highest_risk = fmea_df.loc[fmea_df['RPN'].idxmax()]
                    context_parts.append(f"The highest priority risk is '{highest_risk['Potential Failure Mode']}' with an RPN of {highest_risk['RPN']}.")

        # Pre-Mortem Context
        if st.session_state.get('pre_mortem_summary'):
            context_parts.append("\n--- PRE-MORTEM SUMMARY ---")
            context_parts.append(st.session_state.pre_mortem_summary)
            
        # Medical Device Classification
        if st.session_state.get('medical_device_classification'):
            context_parts.append("\n--- MEDICAL DEVICE CLASSIFICATION ---")
            classification = st.session_state.medical_device_classification
            context_parts.append(f"Device was classified as: {classification.get('classification')}")
            context_parts.append(f"Rationale: {classification.get('rationale')}")

        # Vendor Communication Context
        if st.session_state.get('vendor_email_draft'):
            context_parts.append("\n--- VENDOR COMMUNICATION DRAFT ---")
            context_parts.append("An email has been drafted to the vendor with the following content summary:")
            context_parts.append(st.session_state.vendor_email_draft[:300] + "...")

        # Cost of Quality Context
        if st.session_state.get('coq_results'):
            context_parts.append("\n--- COST OF QUALITY (CoQ) ---")
            coq_results = st.session_state.coq_results
            for key, value in coq_results.items():
                context_parts.append(f"{key}: ${value:,.2f}")
            
        return "\n".join(context_parts)

    @retry_with_backoff()
    def generate_response(self, user_query: str) -> str:
        """Generates a response to a user query based on the full application context."""
        if not self.client:
            return "AI assistant is not available. Please configure the OpenAI API key."

        full_context = self.get_full_context()
        
        system_prompt = "You are a helpful AI assistant embedded in a quality management application called A.Q.M.S. Use the provided context from the application's different tabs to answer the user's question. Be concise, helpful, and synthesize information where possible. If the user asks for something outside the context, use your general knowledge but specify that it is not from the application's data."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the full context of what is happening in the application:\n{full_context}\n\nNow, answer my question:\n{user_query}"}
                ],
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error generating AI response: {e}")
            return "Sorry, I encountered an error while generating a response."
