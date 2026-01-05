import time
import random
import difflib
from functools import wraps
import logging

# Setup basic logging
logger = logging.getLogger(__name__)

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    """
    Decorator to retry a function with exponential backoff.
    Useful for API calls (OpenAI, Google) that might hit rate limits.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        logger.error(f"Failed after {retries} retries: {e}")
                        raise e
                    sleep = (backoff_in_seconds * 2 ** x) + random.uniform(0, 1)
                    time.sleep(sleep)
                    x += 1
        return wrapper
    return decorator

def calculate_fuzzy_similarity(s1: str, s2: str) -> float:
    """
    Calculates the fuzzy similarity score (0 to 100) between two strings
    using SequenceMatcher.
    
    Args:
        s1 (str): First string (e.g., My Product Name)
        s2 (str): Second string (e.g., Recall Description)
        
    Returns:
        float: Similarity score (0-100)
    """
    if not s1 or not s2:
        return 0.0
    
    # Normalize strings (lowercase)
    s1_clean = str(s1).lower().strip()
    s2_clean = str(s2).lower().strip()
    
    # Use standard python difflib
    ratio = difflib.SequenceMatcher(None, s1_clean, s2_clean).ratio()
    return ratio * 100
