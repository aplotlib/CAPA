# src/match_and_classify.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from rapidfuzz import fuzz

@dataclass
class ScoredHit:
    source: str
    title: str
    url: str
    snippet: str
    date: Optional[str]
    score: float
    raw: Dict[str, Any]

def fuzzy_score(product_name: str, title: str, snippet: str) -> float:
    a = fuzz.token_set_ratio(product_name, title)
    b = fuzz.token_set_ratio(product_name, snippet)
    return max(a, b) / 100.0
