# main.py
from __future__ import annotations

import os
import re
import time
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
from rapidfuzz import fuzz

# Optional: OpenAI (only used if enabled)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore


# ============================================================
# Secrets / Config
# ============================================================
def get_secret(name: str, required: bool = True) -> Optional[str]:
    # Check streamlit secrets first
    if hasattr(st, "secrets") and name in st.secrets:
        v = str(st.secrets[name]).strip()
        if v:
            return v
    # Check environment variables
    v = (os.getenv(name) or "").strip()
    if v:
        return v
    
    if required:
        # Don't raise immediately to avoid crashing before UI loads; 
        # let the specific function handle missing keys.
        return None 
    return None


GOOGLE_API_KEY = None
GOOGLE_CX_ID = None


def ensure_google_secrets():
    global GOOGLE_API_KEY, GOOGLE_CX_ID
    if GOOGLE_API_KEY is None:
        GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY", required=True)
    if GOOGLE_CX_ID is None:
        GOOGLE_CX_ID = get_secret("GOOGLE_CX_ID", required=True)


def ensure_openai_client() -> Any:
    if OpenAI is None:
        st.error("OpenAI package not installed. Please add `openai` to requirements.txt.")
        st.stop()
    
    api_key = get_secret("OPENAI_API_KEY", required=True)
    if not api_key:
        st.error("Missing `OPENAI_API_KEY`. Please set it in .streamlit/secrets.toml")
        st.stop()
        
    return OpenAI(api_key=api_key)


# ============================================================
# Date windows
# ============================================================
@dataclass(frozen=True)
class DateWindow:
    start: date
    end: date  # inclusive

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


def preset_window(days: int, today: Optional[date] = None) -> DateWindow:
    today = today or date.today()
    return DateWindow(start=today - timedelta(days=days), end=today)


def custom_window(start: date, end: date) -> DateWindow:
    if start > end:
        # Graceful fallback instead of crash
        return DateWindow(start=end, end=start)
    return DateWindow(start=start, end=end)


# ============================================================
# IO: read products CSV/XLSX
# ============================================================
REQUIRED_COLS = ["SKU", "Product Name"]


def read_products(uploaded_file) -> pd.DataFrame:
    fname = uploaded_file.name.lower()
    if fname.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif fname.endswith(".xlsx") or fname.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Upload must be .csv or .xlsx")

    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}. Expected headers: {REQUIRED_COLS}")

    df = df[REQUIRED_COLS].copy()
    df["SKU"] = df["SKU"].astype(str).str.strip()
    df["Product Name"] = df["Product Name"].astype(str).str.strip()
    df = df[df["SKU"].ne("") & df["Product Name"].ne("")]
    df = df.drop_duplicates(subset=["SKU", "Product Name"]).reset_index(drop=True)
    return df


# ============================================================
# Helpers: normalization, fuzzy scoring
# ============================================================
def normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def fuzzy_score(product_name: str, title: str, snippet: str) -> float:
    pn = normalize_text(product_name)
    t = normalize_text(title)
    sn = normalize_text(snippet)
    if not pn: return 0.0
    a = fuzz.token_set_ratio(pn, t)
    b = fuzz.token_set_ratio(pn, sn)
    return max(a, b) / 100.0


def safe_get(d: Dict[str, Any], key: str, default: str = "") -> str:
    v = d.get(key)
    return default if v is None else str(v)


def parse_domains(text: str) -> List[str]:
    # Accept newline/comma/space separated
    raw = re.split(r"[,\n\r ]+", text.strip())
    out = []
    for r in raw:
        r = r.strip()
        if not r:
            continue
        r = r.replace("https://", "").replace("http://", "")
        r = r.strip("/")
        out.append(r)
    return sorted(set(out))


# ============================================================
# Connectors
# ============================================================
GOOGLE_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"

OPENFDA_DEVICE_RECALL = "https://api.fda.gov/device/recall.json"
OPENFDA_DEVICE_ENF = "https://api.fda.gov/device/enforcement.json"
CPSC_ENDPOINT = "https://www.saferproducts.gov/RestWebServices/Recall"

GDELT_DOC_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _request_json(url: str, params: Dict[str, Any], timeout: int = 30) -> Any:
    """Safely executes a GET request and handles 401/403/404 errors gracefully."""
    try:
        r = requests.get(url, params=params, timeout=timeout)
        
        if r.status_code == 404:
            return None
            
        r.raise_for_status()
        return r.json()
        
    except requests.exceptions.HTTPError as e:
        # Log error to console instead of UI to avoid CacheReplayClosureError
        print(f"⚠️ HTTP Error ({e.response.status_code}) fetching {url}: {e}")
        return None
        
    except Exception as e:
        print(f"Network/Connection Error fetching {url}: {e}")
        return None


@st.cache_data(show_spinner=False, ttl=60 * 60)
def google_search_cached(query: str, days: Optional[int], num: int) -> List[Dict[str, Any]]:
    ensure_google_secrets()
    
    if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
        # Return empty list without UI side effect to prevent cache errors
        print("Skipping Google Search: Missing API Key or CX ID.")
        return []

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX_ID,
        "q": query,
        "num": min(max(int(num), 1), 10),
    }
    if days is not None:
        params["dateRestrict"] = f"d{int(days)}"
        
    data = _request_json(GOOGLE_ENDPOINT, params=params)
    if not data:
        return []
    return data.get("items", []) or []


@st.cache_data(show_spinner=False, ttl=60 * 60)
def openfda_cached(endpoint: str, search: str, limit: int = 50) -> List[Dict[str, Any]]:
    params = {"search": search, "limit": min(max(int(limit), 1), 1000)}
    data = _request_json(endpoint, params=params)
    if not data:
        return []
    return data.get("results", []) or []


@st.cache_data(show_spinner=False, ttl=60 * 60)
def cpsc_cached(product_name: str, start_iso: str, end_iso: str, limit: int = 200) -> List[Dict[str, Any]]:
    params = {
        "format": "json",
        "ProductName": product_name,
        "RecallDateStart": start_iso,
        "RecallDateEnd": end_iso,
    }
    data = _request_json(CPSC_ENDPOINT, params=params)
    if not data:
        return []
    if isinstance(data, list):
        return data[:limit]
    return []


def _gdelt_dt(d: date, end: bool) -> str:
    # GDELT expects UTC YYYYMMDDHHMMSS.
    # Use 000000 at start, 235959 at end.
    t = "235959" if end else "000000"
    return f"{d.strftime('%Y%m%d')}{t}"


@st.cache_data(show_spinner=False, ttl=30 * 60)
def gdelt_search_cached(query: str, window_start: date, window_end: date, maxrecords: int = 250) -> List[Dict[str, Any]]:
    # GDELT Doc API: best for recent coverage; can be inconsistent beyond ~3 months.
    params = {
        "query": query,
        "format": "json",
        "mode": "ArtList",
        "maxrecords": min(max(int(maxrecords), 1), 250),
        "sort": "DateDesc",
        "startdatetime": _gdelt_dt(window_start, end=False),
        "enddatetime": _gdelt_dt(window_end, end=True),
    }
    data = _request_json(GDELT_DOC_ENDPOINT, params=params, timeout=30)
    if not data:
        return []
    return data.get("articles", []) or []


# ============================================================
# LLM classification & Summarization (Agentic)
# ============================================================
LLM_SYSTEM = (
    "You are a safety/compliance analyst. "
    "Classify whether a record likely pertains to the given product. "
    "Be conservative: if unclear, say 'uncertain' and lower confidence. "
    "Return ONLY JSON."
)

LLM_SCHEMA = {
    "name": "hit_classification",
    "schema": {
        "type": "object",
        "properties": {
            "relation": {"type": "string", "enum": ["likely_match", "similar_product", "not_related", "uncertain"]},
            "category": {"type": "string", "enum": ["recall", "regulatory_action", "injury", "lawsuit", "negative_press", "other"]},
            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "why": {"type": "string"},
        },
        "required": ["relation", "category", "severity", "confidence", "why"],
        "additionalProperties": False,
    },
}


def classify_hit_openai(client: Any, sku: str, product_name: str, hit: Dict[str, Any], model: str) -> Dict[str, Any]:
    try:
        payload = {"sku": sku, "product_name": product_name, "hit": hit}
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": LLM_SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_schema", "json_schema": LLM_SCHEMA},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"LLM Classification Error: {e}")
        return {}


def summarize_risks_openai(client: Any, product_name: str, hits: List[Dict[str, Any]], model: str) -> str:
    """Agentic capability: Summarize findings into a Regulatory Intelligence Briefing."""
    if not hits:
        return "No findings to summarize."
    
    # Minimize token usage by sending only key fields
    context_hits = []
    for h in hits:
        context_hits.append({
            "Region": h.get("Region"),
            "Category": h.get("Category"),
            "Title": h.get("Title"),
            "Snippet": h.get("Snippet", "")[:150],
            "Date": h.get("Date")
        })

    system_prompt = (
        "You are a Regulatory Intelligence Agent. "
        "Your goal is to screen search results for a medical device and provide a 'Regulatory Briefing'."
        "Group your response by Region (US, EU, UK, LATAM, Global). "
        "Highlight any 'High Severity' issues like Recalls, Safety Alerts, or Lawsuits. "
        "Ignore obvious noise or unrelated products."
    )
    
    user_prompt = f"""
    Product: {product_name}
    Search Results: {json.dumps(context_hits, indent=1)}
    
    Format the output as a clean Markdown report with:
    1. Executive Summary (1-2 sentences).
    2. Regional Breakdown (US, EU, UK, LATAM).
    3. Action Recommendations (if any risks found).
    """

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Agent Summary Error: {e}"


# ============================================================
# Orchestrator
# ============================================================
@dataclass
class RunOptions:
    # Primary sources
    use_google_general: bool = True
    use_google_regulators: bool = True
    use_openfda_recall: bool = True
    use_openfda_enforcement: bool = True
    use_cpsc: bool = True
    use_gdelt_media: bool = True

    # Region toggles for regulator site search
    regulators_uk: bool = True
    regulators_eu: bool = True
    regulators_latam: bool = True

    # Domains (user editable)
    uk_domains: List[str] = None  # type: ignore
    eu_domains: List[str] = None  # type: ignore
    latam_domains: List[str] = None  # type: ignore
    media_domains: List[str] = None  # type: ignore

    # Google dateRestrict days (rolling)
    google_days: Optional[int] = None

    # thresholds
    fuzzy_threshold_google: float = 0.70
    keep_low_score_official_sources: bool = True

    # LLM
    use_llm: bool = False
    llm_model: str = "gpt-4o-mini" # Corrected from gpt-4.1-mini
    llm_sleep_seconds: float = 0.0

    # Controls
    max_hits_per_source: int = 50  # cap within UI


DEFAULT_UK_DOMAINS = [
    "gov.uk/drug-device-alerts",
    "mhra.gov.uk", 
    "nice.org.uk"
]
DEFAULT_EU_DOMAINS = [
    "ema.europa.eu",
    "health.ec.europa.eu", # EUDAMED portal
    "bfarm.de",          # Germany
    "ansm.sante.fr",     # France
    "aemps.gob.es",      # Spain
    "hpra.ie",           # Ireland
    "fimea.fi",          # Finland
    "lakemedelsverket.se",  # Sweden
    "swissmedic.ch"      # Switzerland (important for EU market)
]
DEFAULT_LATAM_DOMAINS = [
    "invima.gov.co",        # Colombia
    "gov.br/anvisa",        # Brazil
    "gob.mx/cofepris",      # Mexico
    "argentina.gob.ar/anmat", # Argentina
    "gob.pe/digemid",       # Peru
    "ispch.cl",             # Chile
]
DEFAULT_MEDIA_DOMAINS = [
    "reuters.com",
    "apnews.com",
    "bbc.co.uk",
    "nytimes.com",
    "wsj.com",
    "theguardian.com",
    "bloomberg.com",
    "ft.com",
    "medtechdive.com",
    "massdevice.com"
]


def build_site_query(domains: List[str], base_terms: str) -> str:
    # Use OR of site: filters
    # Example: (site:ema.europa.eu OR site:bfarm.de) <terms>
    parts = []
    for d in domains:
        d = d.strip()
        if not d:
            continue
        parts.append(f"site:{d}")
    if not parts:
        return base_terms
    return f"({' OR '.join(parts)}) {base_terms}"


def search_one(
    sku: str,
    product_name: str,
    window: DateWindow,
    opts: RunOptions,
    llm_client: Any = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """Returns list of hits AND an optional Agent Summary string."""
    rows: List[Dict[str, Any]] = []

    # Terms tuned for "bad news" / regulatory actions
    # Added: "safety notice", "bulletin", "warning letter"
    risk_terms = '(recall OR "field safety" OR "safety notice" OR "urgent safety" OR "risk of" OR warning OR injury OR lawsuit OR bulletin OR alert OR "warning letter")'
    base_terms = f"\"{product_name}\" {risk_terms}"

    # ------------------
    # Google - General Web (News/Media)
    # ------------------
    if opts.use_google_general:
        q = base_terms
        items = google_search_cached(q, days=opts.google_days, num=10)
        for it in items:
            title = safe_get(it, "title")
            snippet = safe_get(it, "snippet")
            url = safe_get(it, "link")
            score = fuzzy_score(product_name, title, snippet)
            if score < opts.fuzzy_threshold_google:
                continue
            rows.append({
                "SKU": sku,
                "Product Name": product_name,
                "Source": "Google Web",
                "Category": "News/Media",
                "Region": "Global",
                "Title": title,
                "URL": url,
                "Snippet": snippet,
                "Date": "",
                "FuzzyScore": round(score, 3),
            })

    # ------------------
    # Google - Regulators (site scoped)
    # ------------------
    if opts.use_google_regulators:
        # Build per-region domain list
        reg_sets: List[Tuple[str, List[str], bool]] = [
            ("UK", opts.uk_domains or DEFAULT_UK_DOMAINS, opts.regulators_uk),
            ("EU", opts.eu_domains or DEFAULT_EU_DOMAINS, opts.regulators_eu),
            ("LATAM", opts.latam_domains or DEFAULT_LATAM_DOMAINS, opts.regulators_latam),
        ]
        for region_name, domains, enabled in reg_sets:
            if not enabled or not domains:
                continue
            q = build_site_query(domains, base_terms)
            items = google_search_cached(q, days=opts.google_days, num=10)
            for it in items:
                title = safe_get(it, "title")
                snippet = safe_get(it, "snippet")
                url = safe_get(it, "link")
                score = fuzzy_score(product_name, title, snippet)
                if score < max(0.55, opts.fuzzy_threshold_google - 0.10):
                    continue
                rows.append({
                    "SKU": sku,
                    "Product Name": product_name,
                    "Source": f"Regulator ({region_name})",
                    "Category": "Regulatory Action",
                    "Region": region_name,
                    "Title": title,
                    "URL": url,
                    "Snippet": snippet,
                    "Date": "",
                    "FuzzyScore": round(score, 3),
                })

    # ------------------
    # openFDA (strict date window)
    # ------------------
    start_ymd = _yyyymmdd(window.start)
    end_ymd = _yyyymmdd(window.end)

    def build_openfda_search(pn: str) -> str:
        pnq = pn.replace('"', '\\"')
        return (
            f'(product_description:"{pnq}" OR reason_for_recall:"{pnq}" OR recalling_firm:"{pnq}")'
            f" AND report_date:[{start_ymd} TO {end_ymd}]"
        )

    if opts.use_openfda_recall:
        s = build_openfda_search(product_name)
        results = openfda_cached(OPENFDA_DEVICE_RECALL, s, limit=50)
        for r in results[: opts.max_hits_per_source]:
            title = safe_get(r, "product_description")[:220]
            snippet = safe_get(r, "reason_for_recall")
            recall_num = safe_get(r, "recall_number")
            score = fuzzy_score(product_name, title, snippet)
            if (not opts.keep_low_score_official_sources) and score < opts.fuzzy_threshold_google:
                continue
            rows.append({
                "SKU": sku,
                "Product Name": product_name,
                "Source": "FDA Device Recall",
                "Category": "Regulatory Action",
                "Region": "US",
                "Title": title,
                "URL": f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRES/res.cfm?id={r.get('event_id','')}", # Construct actionable link
                "Snippet": snippet,
                "Date": safe_get(r, "report_date"),
                "FuzzyScore": round(score, 3),
            })

    if opts.use_openfda_enforcement:
        s = build_openfda_search(product_name)
        results = openfda_cached(OPENFDA_DEVICE_ENF, s, limit=50)
        for r in results[: opts.max_hits_per_source]:
            title = safe_get(r, "product_description")[:220]
            snippet = safe_get(r, "reason_for_recall")
            recall_num = safe_get(r, "recall_number")
            score = fuzzy_score(product_name, title, snippet)
            if (not opts.keep_low_score_official_sources) and score < opts.fuzzy_threshold_google:
                continue
            rows.append({
                "SKU": sku,
                "Product Name": product_name,
                "Source": "FDA Enforcement",
                "Category": "Regulatory Action",
                "Region": "US",
                "Title": title,
                "URL": recall_num,
                "Snippet": snippet,
                "Date": safe_get(r, "report_date"),
                "FuzzyScore": round(score, 3),
            })

    # ------------------
    # CPSC (strict date window)
    # ------------------
    if opts.use_cpsc:
        results = cpsc_cached(product_name, window.start.isoformat(), window.end.isoformat(), limit=200)
        for r in results[: opts.max_hits_per_source]:
            title = safe_get(r, "Title")
            snippet = safe_get(r, "Description")
            url = safe_get(r, "URL")
            recall_date = safe_get(r, "RecallDate")
            score = fuzzy_score(product_name, title, snippet)
            if (not opts.keep_low_score_official_sources) and score < opts.fuzzy_threshold_google:
                continue
            rows.append({
                "SKU": sku,
                "Product Name": product_name,
                "Source": "CPSC (Consumer Safety)",
                "Category": "Regulatory Action",
                "Region": "US",
                "Title": title,
                "URL": url,
                "Snippet": snippet,
                "Date": recall_date,
                "FuzzyScore": round(score, 3),
            })

    # ------------------
    # Media: GDELT (recent coverage) + optional domain scoping
    # ------------------
    if opts.use_gdelt_media and window.days <= 93:
        gdelt_q = f"\"{product_name}\" (recall OR safety OR warning OR injury OR lawsuit)"
        if opts.media_domains:
            dom_ops = " OR ".join([f"domain:{d}" for d in opts.media_domains if d])
            gdelt_q = f"({gdelt_q}) ({dom_ops})"

        articles = gdelt_search_cached(gdelt_q, window.start, window.end, maxrecords=250)
        for a in articles[: opts.max_hits_per_source]:
            title = safe_get(a, "title")
            url = safe_get(a, "url")
            snippet = safe_get(a, "sourceCountry") + " " + safe_get(a, "domain")
            dt = safe_get(a, "seendate")
            score = fuzzy_score(product_name, title, snippet)
            if score < max(0.55, opts.fuzzy_threshold_google - 0.10):
                continue
            rows.append({
                "SKU": sku,
                "Product Name": product_name,
                "Source": "GDELT Media",
                "Category": "News/Media",
                "Region": "Global",
                "Title": title,
                "URL": url,
                "Snippet": snippet.strip(),
                "Date": dt,
                "FuzzyScore": round(score, 3),
            })

    # If user wants media domains via Google too (site:)
    if opts.media_domains:
        q = build_site_query(opts.media_domains, base_terms)
        items = google_search_cached(q, days=opts.google_days, num=10)
        for it in items:
            title = safe_get(it, "title")
            snippet = safe_get(it, "snippet")
            url = safe_get(it, "link")
            score = fuzzy_score(product_name, title, snippet)
            if score < opts.fuzzy_threshold_google:
                continue
            rows.append({
                "SKU": sku,
                "Product Name": product_name,
                "Source": "Google News Domains",
                "Category": "News/Media",
                "Region": "Global",
                "Title": title,
                "URL": url,
                "Snippet": snippet,
                "Date": "",
                "FuzzyScore": round(score, 3),
            })

    # Deduplicate (source+url+title)
    seen = set()
    deduped = []
    for r in sorted(rows, key=lambda x: x["FuzzyScore"], reverse=True):
        k = (r["Source"], (r["URL"] or "").strip(), normalize_text(r["Title"]))
        if k in seen:
            continue
        seen.add(k)
        deduped.append(r)

    # Agentic: Summarization & Classification
    agent_summary = ""
    if opts.use_llm:
        if llm_client is None:
            llm_client = ensure_openai_client()
        
        # 1. Summarize all findings (The "Agent")
        if deduped:
            agent_summary = summarize_risks_openai(llm_client, product_name, deduped, opts.llm_model)

        # 2. Detailed Classification
        enriched = []
        for r in deduped:
            classification = classify_hit_openai(llm_client, sku, product_name, r, model=opts.llm_model)
            out = dict(r)
            if classification:
                for k, v in classification.items():
                    out[f"LLM_{k}"] = v
            enriched.append(out)
            if opts.llm_sleep_seconds > 0:
                time.sleep(opts.llm_sleep_seconds)
        return enriched, agent_summary

    return deduped, ""


# ============================================================
# Reporting
# ============================================================
def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["HasHit"] = True

    if "LLM_relation" in df.columns:
        df["FlagLevel"] = df["LLM_relation"].map({
            "likely_match": "HIGH",
            "similar_product": "MED",
            "uncertain": "MED",
            "not_related": "LOW",
        }).fillna("MED")
        df["Severity"] = df.get("LLM_severity", "")
        df["Category"] = df.get("LLM_category", "")
        df["Confidence"] = df.get("LLM_confidence", "")
    else:
        df["FlagLevel"] = df["FuzzyScore"].apply(lambda x: "HIGH" if x >= 0.90 else ("MED" if x >= 0.80 else "LOW"))
        df["Severity"] = ""
        # df["Category"] is already set by search_one
        df["Confidence"] = ""
    return df


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["SKU", "Product Name", "FlagLevel", "count"])
    cols = ["SKU", "Product Name", "FlagLevel"]
    summary = df.groupby(cols, dropna=False).size().reset_index(name="count").sort_values(["count"], ascending=False)
    return summary


def build_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Region", "Category", "Source", "FlagLevel", "count"])
    breakdown = (
        df.groupby(["Region", "Category", "Source", "FlagLevel"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count"], ascending=False)
    )
    return breakdown


def export_reports(df: pd.DataFrame) -> Tuple[bytes, bytes]:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    from io import BytesIO
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Findings", index=False)
        build_summary(df).to_excel(w, sheet_name="Summary", index=False)
        build_breakdown(df).to_excel(w, sheet_name="Breakdown", index=False)
    return csv_bytes, bio.getvalue()


# ============================================================
# UI
# ============================================================
st.set_page_config(page_title="CAPA Regulatory Agent", layout="wide", page_icon="🛡️")
st.title("🛡️ Global Regulatory Intelligence & CAPA Agent")
st.caption("Surveillance of FDA, EU, UK, LATAM, CPSC, and Global Media for Recalls & Safety Alerts")

with st.expander("Security / Setup (read this once)", expanded=False):
    st.markdown(
        """
**Keys (required only if you enable that source):**
- `GOOGLE_API_KEY`, `GOOGLE_CX_ID` (Google Programmable Search)
- `OPENAI_API_KEY` (AI classification)

Use `.streamlit/secrets.toml` or environment variables. **Never hardcode keys.**
"""
    )

st.sidebar.header("Date Range")
date_mode = st.sidebar.selectbox(
    "Date Range",
    ["Last 30 days", "Last 60 days", "Last 90 days", "Last 180 days", "Last 365 days", "Custom"],
)

if date_mode == "Custom":
    default_start = date.today() - timedelta(days=365)
    start = st.sidebar.date_input("Start date", value=default_start)
    end = st.sidebar.date_input("End date", value=date.today())
    window = custom_window(start, end)
    google_days = None
else:
    days = int(date_mode.split()[1])
    window = preset_window(days)
    google_days = days

st.sidebar.caption(f"Window: {window.start.isoformat()} → {window.end.isoformat()}  ({window.days} days)")

st.sidebar.divider()
st.sidebar.header("Sources")

use_google_general = st.sidebar.checkbox("Google – General web (News)", value=True)
use_google_regulators = st.sidebar.checkbox("Google – Regulators (EU/UK/LATAM)", value=True, help="Specific site searches for MHRA, EMA, ANVISA, etc.")

use_openfda_recall = st.sidebar.checkbox("openFDA – Device recall", value=True)
use_openfda_enforcement = st.sidebar.checkbox("openFDA – Device enforcement", value=True)
use_cpsc = st.sidebar.checkbox("CPSC – Recalls", value=True)

use_gdelt_media = st.sidebar.checkbox("GDELT – Media database (recent)", value=True)

if use_gdelt_media and window.days > 93:
    st.sidebar.warning("GDELT is best for recent windows (≤ ~90 days). For longer windows, rely on Google/site searches.")

st.sidebar.divider()
st.sidebar.header("Regulators – Regions")
reg_uk = st.sidebar.checkbox("UK regulators (MHRA)", value=True)
reg_eu = st.sidebar.checkbox("EU regulators (EMA/National)", value=True)
reg_latam = st.sidebar.checkbox("LATAM regulators (ANVISA/COFEPRIS/INVIMA)", value=True)

st.sidebar.divider()
st.sidebar.header("Matching & Limits")
fuzzy_threshold = st.sidebar.slider("Google fuzzy threshold", 0.0, 1.0, 0.70, 0.01)
keep_official_low = st.sidebar.checkbox("Keep low-score openFDA/CPSC hits", value=True)
max_hits = st.sidebar.slider("Max hits per source (cap)", 10, 200, 50, 10)

st.sidebar.divider()
st.sidebar.header("Agentic AI")
use_llm = st.sidebar.checkbox("Enable AI Agent", value=True, help="Analyzes results to generate a briefing and categorize risk.")
llm_model = st.sidebar.text_input("LLM model", value="gpt-4o-mini", disabled=not use_llm)
llm_sleep = st.sidebar.slider("LLM delay per hit (seconds)", 0.0, 2.0, 0.0, 0.1, disabled=not use_llm)

st.sidebar.divider()
st.sidebar.header("Domain Lists (editable)")

uk_domains_text = st.sidebar.text_area(
    "UK domains (one per line)",
    value="\n".join(DEFAULT_UK_DOMAINS),
    height=100,
)
eu_domains_text = st.sidebar.text_area(
    "EU domains (one per line)",
    value="\n".join(DEFAULT_EU_DOMAINS),
    height=120,
)
latam_domains_text = st.sidebar.text_area(
    "LATAM domains (one per line)",
    value="\n".join(DEFAULT_LATAM_DOMAINS),
    height=120,
)
media_domains_text = st.sidebar.text_area(
    "Media domains (optional, one per line)",
    value="\n".join(DEFAULT_MEDIA_DOMAINS),
    height=100,
)

opts = RunOptions(
    use_google_general=use_google_general,
    use_google_regulators=use_google_regulators,
    use_openfda_recall=use_openfda_recall,
    use_openfda_enforcement=use_openfda_enforcement,
    use_cpsc=use_cpsc,
    use_gdelt_media=use_gdelt_media,

    regulators_uk=reg_uk,
    regulators_eu=reg_eu,
    regulators_latam=reg_latam,

    uk_domains=parse_domains(uk_domains_text),
    eu_domains=parse_domains(eu_domains_text),
    latam_domains=parse_domains(latam_domains_text),
    media_domains=parse_domains(media_domains_text),

    google_days=google_days if (use_google_general or use_google_regulators) else None,

    fuzzy_threshold_google=float(fuzzy_threshold),
    keep_low_score_official_sources=bool(keep_official_low),

    use_llm=bool(use_llm),
    llm_model=str(llm_model),
    llm_sleep_seconds=float(llm_sleep),

    max_hits_per_source=int(max_hits),
)

tab1, tab2 = st.tabs(["Single Search", "Batch Upload"])

# ------------------------------------------------------------
# Single Search
# ------------------------------------------------------------
with tab1:
    st.subheader("Single Search")
    colA, colB = st.columns(2)
    with colA:
        sku = st.text_input("SKU", value="")
    with colB:
        product_name = st.text_input("Product Name / Description", value="")

    run_single = st.button("Run Search", type="primary", disabled=not product_name.strip())

    if run_single:
        llm_client = None

        # Validate keys only if needed
        if opts.use_llm:
            try:
                llm_client = ensure_openai_client()
            except Exception as e:
                st.error(f"OpenAI not configured: {e}")
                st.stop()

        if opts.use_google_general or opts.use_google_regulators:
            try:
                ensure_google_secrets()
            except Exception as e:
                # Do not stop execution for Google error, just warn and continue
                st.toast(f"Google configuration missing/invalid. Searching other sources...", icon="⚠️")

        with st.spinner("Agent is querying global health agencies & media..."):
            rows, agent_summary = search_one(sku.strip(), product_name.strip(), window, opts, llm_client=llm_client)

        if not rows:
            st.info("No hits found for the selected sources/date range.")
        else:
            df = add_flags(pd.DataFrame(rows))
            
            # --- Agent Briefing ---
            if agent_summary:
                st.success("Analysis Complete")
                with st.expander("📝 Agent Regulatory Briefing", expanded=True):
                    st.markdown(agent_summary)
            
            st.divider()

            # --- Categorized Findings ---
            st.markdown("### Findings by Category")
            
            # Create sub-tabs for easier viewing
            subtabs = st.tabs(["All", "Regulatory Actions (Official)", "News & Media", "US", "EU", "LATAM"])
            
            with subtabs[0]:
                st.dataframe(
                    df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={"URL": st.column_config.LinkColumn("Source Link")}
                )
            
            with subtabs[1]:
                reg_df = df[df["Category"] == "Regulatory Action"]
                st.dataframe(
                    reg_df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={"URL": st.column_config.LinkColumn("Source Link")}
                )

            with subtabs[2]:
                news_df = df[df["Category"] == "News/Media"]
                st.dataframe(
                    news_df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={"URL": st.column_config.LinkColumn("Source Link")}
                )
            
            with subtabs[3]: # US
                st.dataframe(df[df["Region"] == "US"], use_container_width=True, hide_index=True, column_config={"URL": st.column_config.LinkColumn("Source Link")})
            with subtabs[4]: # EU
                st.dataframe(df[df["Region"] == "EU"], use_container_width=True, hide_index=True, column_config={"URL": st.column_config.LinkColumn("Source Link")})
            with subtabs[5]: # LATAM
                st.dataframe(df[df["Region"] == "LATAM"], use_container_width=True, hide_index=True, column_config={"URL": st.column_config.LinkColumn("Source Link")})


            st.markdown("### Regional Breakdown")
            st.dataframe(build_breakdown(df), use_container_width=True, hide_index=True)

            csv_bytes, xlsx_bytes = export_reports(df)
            c1, c2 = st.columns(2)
            c1.download_button("Download CSV", data=csv_bytes, file_name="single_search_report.csv")
            c2.download_button("Download XLSX", data=xlsx_bytes, file_name="single_search_report.xlsx")


# ------------------------------------------------------------
# Batch Upload
# ------------------------------------------------------------
with tab2:
    st.subheader("Batch Upload")
    st.caption('Upload a CSV/XLSX with headers: **SKU**, **Product Name**')

    up = st.file_uploader("Upload file", type=["csv", "xlsx", "xls"])
    run_batch = st.button("Run Batch Screening", type="primary", disabled=up is None)

    if up and run_batch:
        try:
            products = read_products(up)
        except Exception as e:
            st.error(f"Upload error: {e}")
            st.stop()

        if products.empty:
            st.warning("No valid rows found in the upload.")
            st.stop()

        llm_client = None
        if opts.use_llm:
            try:
                llm_client = ensure_openai_client()
            except Exception as e:
                st.error(f"OpenAI not configured: {e}")
                st.stop()

        if opts.use_google_general or opts.use_google_regulators:
            try:
                ensure_google_secrets()
            except Exception:
                pass # Already handled inside search_one

        st.write(f"Products loaded: **{len(products)}**")
        progress = st.progress(0.0)
        status = st.empty()

        all_rows: List[Dict[str, Any]] = []
        t0 = time.time()

        for i, r in products.iterrows():
            sku_i = str(r["SKU"]).strip()
            pn_i = str(r["Product Name"]).strip()
            status.write(f"Searching **{i+1}/{len(products)}**: `{sku_i}` – {pn_i}")

            rows, _ = search_one(sku_i, pn_i, window, opts, llm_client=llm_client)
            all_rows.extend(rows)

            progress.progress((i + 1) / len(products))

        elapsed = time.time() - t0
        status.write(f"Done in {elapsed:.1f}s. Total hits: **{len(all_rows)}**")

        if not all_rows:
            st.info("No hits found for any uploaded products in the selected sources/date range.")
            st.stop()

        df = add_flags(pd.DataFrame(all_rows))

        # Overview: best flag per SKU/product
        best = (
            df.sort_values(["SKU", "Product Name", "FlagLevel", "FuzzyScore"], ascending=[True, True, True, False])
            .groupby(["SKU", "Product Name"], as_index=False)
            .first()
        )

        st.markdown("### Screening Overview (top hit per product)")
        st.dataframe(
            best[["SKU", "Product Name", "Region", "Category", "Source", "FlagLevel", "FuzzyScore", "Title", "URL"]],
            use_container_width=True,
            hide_index=True,
            column_config={"URL": st.column_config.LinkColumn("Source Link")}
        )

        st.markdown("### All Findings")
        st.dataframe(df, use_container_width=True, hide_index=True, column_config={"URL": st.column_config.LinkColumn("Source Link")})

        st.markdown("### Breakdown")
        st.dataframe(build_breakdown(df), use_container_width=True, hide_index=True)

        csv_bytes, xlsx_bytes = export_reports(df)
        st.download_button("Download CSV", data=csv_bytes, file_name="batch_screening_report.csv")
        st.download_button("Download XLSX", data=xlsx_bytes, file_name="batch_screening_report.xlsx")
