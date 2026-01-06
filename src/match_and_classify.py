# src/match_and_classify.py
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional
from rapidfuzz import fuzz

CATEGORY_SYNONYMS = {
    "bpm": ["blood pressure monitor", "bp monitor", "sphygmomanometer"],
    "scooter": ["mobility scooter", "powered scooter", "electric scooter"],
    "insulin pump": ["insulin infusion pump", "diabetes pump"],
    "infusion pump": ["iv pump", "intravenous pump", "syringe pump"],
    "pacemaker": ["cardiac pacemaker", "implantable pacemaker"],
    "defibrillator": ["aed", "automated external defibrillator", "icd", "implantable cardioverter defibrillator"],
    "ventilator": ["respirator", "mechanical ventilator"],
    "catheter": ["vascular catheter", "central line", "cvc", "urinary catheter"],
    "stent": ["vascular stent", "coronary stent"],
    "hip implant": ["hip prosthesis", "hip replacement", "acetabular cup"],
}


@dataclass
class ScoredHit:
    source: str
    title: str
    url: str
    snippet: str
    date: Optional[str]
    score: float
    raw: Dict[str, Any]


def _expand_synonyms(term: str) -> List[str]:
    expanded = {term}
    lowered = term.lower()
    for key, vals in CATEGORY_SYNONYMS.items():
        if key in lowered or lowered in vals:
            expanded.update(vals)
            expanded.add(key)
    return list(expanded)


def _extract_model_tokens(text: str) -> List[str]:
    """
    Pull out model-ish tokens containing digits (e.g., "X500", "AB-1234").
    """
    if not text:
        return []
    return re.findall(r"[A-Za-z]*\d[A-Za-z0-9\-]{2,}", text)


def fuzzy_score(product_name: str, title: str, snippet: str, manufacturer: Optional[str] = None) -> float:
    """
    Stronger matching that blends synonym search, typo tolerance, and model-number sensitivity.
    Returns score in 0.0 - 1.0.
    """
    title = title or ""
    snippet = snippet or ""
    product_name = product_name or ""

    base_a = fuzz.token_set_ratio(product_name, title)
    base_b = fuzz.token_set_ratio(product_name, snippet)
    base_score = max(base_a, base_b) / 100.0

    # Synonym expansion (catch BPMs, scooters, etc.)
    synonyms = _expand_synonyms(product_name)
    syn_scores = []
    for syn in synonyms:
        syn_scores.append(fuzz.token_set_ratio(syn, title))
        syn_scores.append(fuzz.token_set_ratio(syn, snippet))
    synonym_score = (max(syn_scores) / 100.0) if syn_scores else 0.0

    # Model numbers: near-exact matching gets a boost
    model_tokens = _extract_model_tokens(product_name)
    target_tokens = _extract_model_tokens(f"{title} {snippet}")
    model_match = 0.0
    for mt in model_tokens:
        for tt in target_tokens:
            model_match = max(model_match, fuzz.ratio(mt, tt) / 100.0)
    if model_match >= 0.85:
        base_score = max(base_score, model_match)

    # Manufacturer cue: small bump if name appears
    manufacturer_score = 0.0
    if manufacturer:
        manufacturer_score = max(
            fuzz.partial_ratio(manufacturer.lower(), title.lower()),
            fuzz.partial_ratio(manufacturer.lower(), snippet.lower()),
        ) / 100.0

    combined = max(base_score, synonym_score, manufacturer_score)

    # Soft bonus for recall/alert keywords in the snippet/title
    keywords = ["recall", "safety", "alert", "warning", "class i", "class ii", "enforcement", "field safety"]
    keyword_bonus = 0.05 if any(k in f"{title.lower()} {snippet.lower()}" for k in keywords) else 0.0

    return min(1.0, combined + keyword_bonus)
