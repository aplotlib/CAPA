# src/utils.py

import time
import random
from functools import wraps
import openai
import streamlit as st

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
                            st.toast(f"🤖 AI server busy. Retrying in {sleep_time:.1f}s...")
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
