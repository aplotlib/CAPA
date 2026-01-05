# src/orchestrator.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from .search.google_cse import google_search
from .search.openfda import search_device_recall, search_device_enforcement
from .search.cpsc import cpsc_search
from .match_and_classify import ScoredHit, fuzzy_score
from .llm_classifier import classify_hit

@dataclass
class RunOptions:
    use_google: bool = True
    use_openfda_recall: bool = True
    use_openfda_enforcement: bool = True
    use_cpsc: bool = True
    google_days: Optional[int] = None  # for presets
    fuzzy_threshold: float = 0.70
    use_llm: bool = False

def search_one(sku: str, product_name: str, start: date, end: date, opts: RunOptions) -> List[Dict[str, Any]]:
    hits: List[ScoredHit] = []

    if opts.use_google:
        items = google_search(f'"{product_name}" recall OR warning OR lawsuit OR injury', days=opts.google_days, num=10)
        for it in items:
            title = it.get("title","")
            snippet = it.get("snippet","")
            url = it.get("link","")
            score = fuzzy_score(product_name, title, snippet)
            hits.append(ScoredHit("google", title, url, snippet, None, score, it))

    if opts.use_openfda_recall:
        res = search_device_recall(product_name, start, end, limit=50)
        for r in res:
            title = r.get("product_description","")[:140]
            snippet = r.get("reason_for_recall","")
            url = r.get("recall_number","")
            score = fuzzy_score(product_name, title, snippet)
            hits.append(ScoredHit("openfda_device_recall", title, url, snippet, r.get("report_date"), score, r))

    if opts.use_openfda_enforcement:
        res = search_device_enforcement(product_name, start, end, limit=50)
        for r in res:
            title = r.get("product_description","")[:140]
            snippet = r.get("reason_for_recall","")
            url = r.get("recall_number","")
            score = fuzzy_score(product_name, title, snippet)
            hits.append(ScoredHit("openfda_device_enforcement", title, url, snippet, r.get("report_date"), score, r))

    if opts.use_cpsc:
        res = cpsc_search(product_name, start, end, limit=100)
        for r in res:
            title = r.get("Title","")
            snippet = r.get("Description","")
            url = r.get("URL","")
            score = fuzzy_score(product_name, title, snippet)
            hits.append(ScoredHit("cpsc", title, url, snippet, r.get("RecallDate"), score, r))

    # keep high-ish matches + always keep openFDA/CPSC if any (they're already “recall-shaped”)
    filtered = [h for h in hits if (h.source != "google") or (h.score >= opts.fuzzy_threshold)]
    filtered.sort(key=lambda x: x.score, reverse=True)

    out: List[Dict[str, Any]] = []
    for h in filtered:
        row = {
            "SKU": sku,
            "Product Name": product_name,
            "Source": h.source,
            "Title": h.title,
            "URL": h.url,
            "Snippet": h.snippet,
            "Date": h.date,
            "FuzzyScore": round(h.score, 3),
        }
        if opts.use_llm:
            row.update({f"LLM_{k}": v for k, v in classify_hit(sku, product_name, row).items()})
        out.append(row)

    return out
