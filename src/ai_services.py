import streamlit as st
from google import genai
from google.genai import types
from typing import Optional, Dict, Any, List
import json
import os

class AIService:
    def __init__(self, api_key: str):
        # Initialize the modern GenAI client
        self.client = genai.Client(api_key=api_key)
        # Using the latest available experimental models for multimodal capabilities
        self.fast_model = "gemini-2.0-flash-exp" 
        self.reasoning_model = "gemini-2.0-flash-thinking-exp"

    def analyze_text(self, prompt: str, system_instruction: str = None) -> str:
        """Generic text analysis using the fast model."""
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            st.error(f"AI Error: {str(e)}")
            return "Analysis failed due to AI service error."

    def transcribe_and_structure(self, audio_bytes: bytes, context: str = "") -> Dict[str, str]:
        """
        Transcribes audio (server-side) and extracts structured CAPA data.
        """
        prompt_text = f"""
        You are a Quality Assurance Assistant. 
        Listen to this dictation regarding a potential Quality Event or CAPA.
        
        CONTEXT: {context}
        
        TASK:
        1. Transcribe the audio accurately.
        2. Extract the following fields if present:
           - Issue Description (The core problem)
           - Root Cause (If mentioned)
           - Immediate Actions (Corrections taken)
        
        OUTPUT FORMAT (JSON):
        {{
            "transcription": "Full text...",
            "issue_description": "...",
            "root_cause": "...",
            "immediate_actions": "..."
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                    prompt_text
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            st.error(f"Transcription Error: {str(e)}")
            return {"error": str(e)}

    def analyze_meeting_transcript(self, transcript_text: str) -> Dict[str, str]:
        """
        Analyzes a meeting transcript or notes to extract CAPA details.
        """
        system_prompt = """
        You are a Quality Assurance Expert analyzing meeting notes.
        Extract relevant details to initiate a CAPA (Corrective and Preventive Action) record.
        Ignore chit-chat; focus on the technical issue, root cause discussions, and action items.
        """
        
        user_prompt = f"""
        Analyze the following meeting notes/transcript:
        
        "{transcript_text}"
        
        Extract the following into a JSON object:
        - "issue_description": A clear, technical summary of the problem.
        - "root_cause": Any discussed root causes (if any).
        - "immediate_actions": Any short-term fixes discussed.
        - "preventive_action": Any long-term system fixes discussed.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            return json.loads(response.text)
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def screen_recalls(self, product_description: str) -> str:
        """
        Screens a product against known regulatory databases via AI knowledge.
        """
        system_prompt = """
        You are a Global Regulatory Affairs Expert (ISO 13485/MDR).
        Your task is to screen a medical device against known recall patterns and hazard alerts 
        from FDA (USA), EUDAMED (EU), TGA (Australia), Health Canada, and MHRA (UK).
        """
        
        user_prompt = f"""
        Analyze the following device for potential regulatory alerts:
        DEVICE: {product_description}
        
        1. Identify the likely classification and product code (FDA/GMDN).
        2. Summarize COMMON recall reasons for this specific type of device in the last 5 years.
        3. List any specific HIGH PROFILE alerts for this technology category.
        4. Provide a "Watchlist" of keywords to search for in the official databases.
        
        Format as a professional Markdown risk report.
        """
        
        return self.analyze_text(user_prompt, system_instruction=system_prompt)

# Singleton management
def get_ai_service():
    if 'ai_service' not in st.session_state and st.session_state.get('api_key'):
        st.session_state.ai_service = AIService(st.session_state.api_key)
    return st.session_state.get('ai_service')
