# src/utils.py

import time
import random
import streamlit as st
from datetime import date, timedelta
import pandas as pd
from functools import wraps
import openai
import json
import re

def init_session_state():
    """Initializes standard session state keys."""
    defaults = {
        'product_info': {'sku': 'ORION-X1', 'name': 'Neural Link', 'ifu': 'Standard monitoring.'},
        'start_date': date.today() - timedelta(days=30),
        'end_date': date.today(),
        'capa_data': {},
        'analysis_results': None,
        'logged_in': False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def retry_with_backoff(retries=3, initial_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except openai.APIStatusError as e:
                    if e.status_code == 429:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise e
            return func(*args, **kwargs)
        return wrapper
    return decorator

def parse_ai_json_response(response_text: str) -> dict:
    """
    Parses a JSON string from an AI response, handling potential Markdown code blocks.
    """
    try:
        # Strip markdown code blocks if present
        if "```" in response_text:
            # Regex to find the content inside ```json ... ``` or just ``` ... ```
            match = re.search(r"```(?:json)?(.*?)```", response_text, re.DOTALL)
            if match:
                response_text = match.group(1)
        
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON response from AI."}
    except Exception as e:
        return {"error": f"An unexpected error occurred during parsing: {e}"}
