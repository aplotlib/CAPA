# src/utils.py

import time
import streamlit as st
from datetime import date, timedelta
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
        'product_dev_data': {},  # Fixed: Added to prevent KeyError in dashboard
        'analysis_results': None,
        'logged_in': False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def retry_with_backoff(retries=3, initial_delay=1):
    """
    Robust retry decorator that handles specific OpenAI errors.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except openai.RateLimitError:
                    st.toast(f"Rate limit hit. Retrying in {delay}s...", icon="⏳")
                    time.sleep(delay)
                    delay *= 2
                except openai.APIConnectionError:
                    st.toast(f"Connection error. Retrying in {delay}s...", icon="🔌")
                    time.sleep(delay)
                    delay *= 2
                except openai.APIError as e:
                    # Don't retry on fatal API errors (like invalid request)
                    st.error(f"OpenAI API Error: {e}")
                    raise e
                except Exception as e:
                    # General catch-all for other unexpected issues
                    print(f"Unexpected error: {e}")
                    raise e
            return func(*args, **kwargs)
        return wrapper
    return decorator

def parse_ai_json_response(response_text: str) -> dict:
    """
    Parses a JSON string from an AI response, handling potential Markdown code blocks.
    """
    try:
        if "```" in response_text:
            match = re.search(r"```(?:json)?(.*?)```", response_text, re.DOTALL)
            if match:
                response_text = match.group(1)
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON response from AI."}
    except Exception as e:
        return {"error": f"An unexpected error occurred during parsing: {e}"}
