# src/utils.py

import time
import random
from functools import wraps
import openai
import streamlit as st
import pandas as pd
from io import StringIO
import json
import re

def retry_with_backoff(retries=5, initial_delay=1, backoff_factor=2, jitter=0.1):
    """
    Decorator for retrying OpenAI API calls with exponential backoff.
    Handles transient errors like rate limiting or server overload (HTTP 429).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except openai.APIStatusError as e:
                    # Specifically check for "Too Many Requests" or server-side errors
                    if e.status_code in [429, 500, 502, 503, 504]:
                        if i < retries - 1:
                            sleep_time = delay + random.uniform(0, jitter)
                            st.toast(f"AI server busy. Retrying in {sleep_time:.1f}s...")
                            time.sleep(sleep_time)
                            delay *= backoff_factor
                        else:
                            st.error("AI server is currently overloaded. Please try again later.")
                            raise e
                    else:
                        # For other API errors (like authentication), don't retry
                        raise e
                except Exception as e:
                    # Re-raise other exceptions immediately
                    raise e
        return wrapper
    return decorator

def parse_manual_input(input_str: str, target_sku: str) -> pd.DataFrame:
    """Parses manual string input into a DataFrame for sales or returns data."""
    if not input_str.strip():
        return pd.DataFrame()

    if input_str.strip().isnumeric():
        return pd.DataFrame([{'sku': target_sku, 'quantity': int(input_str)}])

    try:
        # If headers are not present, add them
        if 'sku' not in input_str.lower() or 'quantity' not in input_str.lower():
            input_str = f"sku,quantity\n{target_sku},{input_str}"
        return pd.read_csv(StringIO(input_str))
    except Exception:
        st.error("Could not parse manual data.")
        return pd.DataFrame()

def parse_ai_json_response(raw_content: str) -> dict:
    """
    Robustly parses a JSON object from a string that may include markdown fences or other text.
    """
    try:
        # Clean the string by removing markdown fences for JSON
        cleaned_content = re.sub(r'```json\s*|\s*```', '', raw_content.strip())
        
        # Find the JSON object using a regex that looks for the outer curly braces
        json_match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
        
        if json_match:
            json_string = json_match.group(0)
            return json.loads(json_string)
        else:
            # Fallback for simple cases if regex fails
            return json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        # This will be caught by the calling function's exception handler
        raise e
    except Exception as e:
        raise ValueError(f"An unexpected error occurred during JSON parsing: {e}")
