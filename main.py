# main.py
from __future__ import annotations

import os
import re
import time
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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


# -----------------------------
# Secrets / Config
# -----------------------------
def get_secret(name: str, required: bool = True) -> Optional[str]:
    # Streamlit secrets first, then environment variable
    if hasattr(st, "secrets") and name in st.secrets:
        val = str(st.secrets[name]).strip()
        if val:
            return val
    val = (os.getenv(name) or "").strip()
    if val:
        return val
    if required:
        raise RuntimeError(f"Missing required secret/env var: {name}")
    return None


GOOGLE_API_KEY = None
GOOGLE_CX_ID = None

# Only required if user enables Google
def ensure_google_secrets():
    global GOOGLE_API_KEY, GOOGLE_CX_ID
    if GOOGLE_API_KEY is None:
        GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY", required=True)
    if GOOGLE_CX_ID is None:
        GOOGLE_CX_ID = get_secret("GOOGLE_CX_ID", required=True)


# Only required if user enables LLM classification
def ensure_openai_client() -> Any:
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Add `openai` to requirements.txt.")
    api_key = get_secret("OPENAI_API_KEY", required=True)
    return OpenAI(api_key=api_key)


# -----------------------------
# Date windows
# -----------------------------
@dataclass(frozen=True)
class DateWindow:
    start: date
    end: date  # inclusive


def preset_window(days: int, today: Optional[date] = None) -> DateWindow:
    today = today or date.today()
    return DateWindow(start=today - timedelta(days=days), end=today)


def custom_window(start: date, end: date) -> DateWindow:
    if start > end:
        raise ValueError("Start date must be <= end date")
    return DateWindow(start=start, end=end)


# -----------------------------
# IO: read products CSV/XLSX
# -----------------------------
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


# -----------------------------
# Helpers: normalization, fuzzy score
# -----------------------------
def normalize_text(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def fuzzy_score(product_name: str, title: str, snippet: str) -> float:
    pn = normalize_text(product_name)
    t = normalize_text(title or "")
    sn = normalize_text(snippet or "")

    a = fuzz.token_set_ratio(pn, t)
    b = fuzz.token_set_ratio(pn, sn)
    return max(a, b) / 100.0


def safe_get(d: Dict[str, Any], key: str, default: str = "") -> str:
    v = d.get(key)
    return default if v is None else str(v)


# -----------------------------
# Connectors
# -----------------------------
GOOGLE_ENDPOINT = "https://customsearch.googleapis.com/customsearch/v1"
OPENFDA_DEVICE_RECALL = "https://api.fda.gov/device/recall.json"
OPENFDA_DEVICE_ENF = "https://api.fda.gov/device/enforcement.json"
CPSC_ENDPOINT = "https://www.saferproducts.gov/RestWebServices/Recall"


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _request_json(url: str, params: Dict[str, Any], timeout: int = 30) -> Any:
    r = requests.get(url, params=params, timeout=timeout)
    if r.status_code == 404:
        # openFDA commonly uses 404 for no results
        return None
    r.raise_for_status()
    return r.json()


@st.cache_data(show_spinner=False, ttl=60 * 60)
def google_search_cached(query: str, days: Optional[int], num: int) -> List[Dict[str, Any]]:
    ensure_google_secrets()
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


# -----------------------------
# LLM classification (optional)
# -----------------------------
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
    payload = {"sku": sku, "product_name": product_name, "hit": hit}
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": LLM_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_schema", "json_schema": LLM_SCHEMA},
    )
    return resp.output_parsed  # dict


# -----------------------------
# Orchestrator
# -----------------------------
@dataclass
class RunOptions:
    use_google: bool = True
    use_openfda_recall: bool = True
    use_openfda_enforcement: bool = True
    use_cpsc: bool = True

    # Google can't do strict start/end like APIs; use "past N days" via dateRestrict
    google_days: Optional[int] = None

    fuzzy_threshold_google: float = 0.70
    keep_low_score_official_sources: bool = True  # openFDA/CPSC are inherently recall-ish

    use_llm: bool = False
    llm_model: str = "gpt-4.1-mini"
    # simple delay between LLM calls to avoid accidental rate spikes in batch mode
    llm_sleep_seconds: float = 0.0


def search_one(sku: str, product_name: str, window: DateWindow, opts: RunOptions, llm_client: Any = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    # Google query strategy: use a few "risk" terms
    if opts.use_google:
        q = f"\"{product_name}\" (recall OR warning OR injury OR lawsuit OR \"consumer reports\" OR \"press release\")"
        items = google_search_cached(q, days=opts.google_days, num=10)
        for it in items:
            title = safe_get(it, "title")
            snippet = safe_get(it, "snippet")
            url = safe_get(it, "link")
            score = fuzzy_score(product_name, title, snippet)

            # Filter by fuzzy threshold
            if score < opts.fuzzy_threshold_google:
                continue

            row = {
                "SKU": sku,
                "Product Name": product_name,
                "Source": "google",
                "Title": title,
                "URL": url,
                "Snippet": snippet,
                "Date": "",  # Google item doesn't always include
                "FuzzyScore": round(score, 3),
            }
            rows.append(row)

    # openFDA searches: use strict date window
    start_ymd = _yyyymmdd(window.start)
    end_ymd = _yyyymmdd(window.end)

    def build_openfda_search(pn: str) -> str:
        # conservative: search multiple fields
        # Note: openFDA uses Lucene-ish syntax; quoted string is often enough for product_description
        pnq = pn.replace('"', '\\"')
        return (
            f'(product_description:"{pnq}" OR reason_for_recall:"{pnq}" OR recalling_firm:"{pnq}")'
            f" AND report_date:[{start_ymd} TO {end_ymd}]"
        )

    if opts.use_openfda_recall:
        s = build_openfda_search(product_name)
        results = openfda_cached(OPENFDA_DEVICE_RECALL, s, limit=50)
        for r in results:
            title = safe_get(r, "product_description")[:200]
            snippet = safe_get(r, "reason_for_recall")
            recall_num = safe_get(r, "recall_number")
            score = fuzzy_score(product_name, title, snippet)

            # Keep official sources even with lower fuzzy if you want
            if (not opts.keep_low_score_official_sources) and score < opts.fuzzy_threshold_google:
                continue

            row = {
                "SKU": sku,
                "Product Name": product_name,
                "Source": "openfda_device_recall",
                "Title": title,
                "URL": recall_num,
                "Snippet": snippet,
                "Date": safe_get(r, "report_date"),
                "FuzzyScore": round(score, 3),
            }
            rows.append(row)

    if opts.use_openfda_enforcement:
        s = build_openfda_search(product_name)
        results = openfda_cached(OPENFDA_DEVICE_ENF, s, limit=50)
        for r in results:
            title = safe_get(r, "product_description")[:200]
            snippet = safe_get(r, "reason_for_recall")
            recall_num = safe_get(r, "recall_number")
            score = fuzzy_score(product_name, title, snippet)

            if (not opts.keep_low_score_official_sources) and score < opts.fuzzy_threshold_google:
                continue

            row = {
                "SKU": sku,
                "Product Name": product_name,
                "Source": "openfda_device_enforcement",
                "Title": title,
                "URL": recall_num,
                "Snippet": snippet,
                "Date": safe_get(r, "report_date"),
                "FuzzyScore": round(score, 3),
            }
            rows.append(row)

    if opts.use_cpsc:
        results = cpsc_cached(product_name, window.start.isoformat(), window.end.isoformat(), limit=200)
        for r in results:
            title = safe_get(r, "Title")
            snippet = safe_get(r, "Description")
            url = safe_get(r, "URL")
            recall_date = safe_get(r, "RecallDate")
            score = fuzzy_score(product_name, title, snippet)

            if (not opts.keep_low_score_official_sources) and score < opts.fuzzy_threshold_google:
                continue

            row = {
                "SKU": sku,
                "Product Name": product_name,
                "Source": "cpsc",
                "Title": title,
                "URL": url,
                "Snippet": snippet,
                "Date": recall_date,
                "FuzzyScore": round(score, 3),
            }
            rows.append(row)

    # Deduplicate (same URL+Title+Source)
    seen = set()
    deduped = []
    for r in sorted(rows, key=lambda x: x["FuzzyScore"], reverse=True):
        k = (r["Source"], (r["URL"] or "").strip(), normalize_text(r["Title"]))
        if k in seen:
            continue
        seen.add(k)
        deduped.append(r)

    # Optional LLM classification (agentic labeling)
    if opts.use_llm:
        if llm_client is None:
            llm_client = ensure_openai_client()
        enriched = []
        for r in deduped:
            classification = classify_hit_openai(llm_client, sku, product_name, r, model=opts.llm_model)
            out = dict(r)
            for k, v in classification.items():
                out[f"LLM_{k}"] = v
            enriched.append(out)
            if opts.llm_sleep_seconds > 0:
                time.sleep(opts.llm_sleep_seconds)
        return enriched

    return deduped


# -----------------------------
# Reporting
# -----------------------------
def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Basic flag: any hit is a flag; elevate based on LLM if present
    df["HasHit"] = True

    if "LLM_relation" in df.columns:
        # "likely_match" / "similar_product" are most important
        df["FlagLevel"] = df["LLM_relation"].map(
            {
                "likely_match": "HIGH",
                "similar_product": "MED",
                "uncertain": "MED",
                "not_related": "LOW",
            }
        ).fillna("MED")
    else:
        # Without LLM, use fuzzy score heuristics (Google threshold already applied)
        df["FlagLevel"] = df["FuzzyScore"].apply(lambda x: "HIGH" if x >= 0.90 else ("MED" if x >= 0.80 else "LOW"))
    return df


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["SKU", "Product Name", "FlagLevel", "count"])

    cols = ["SKU", "Product Name", "FlagLevel"]
    summary = df.groupby(cols, dropna=False).size().reset_index(name="count").sort_values(["count"], ascending=False)
    return summary


def export_reports(df: pd.DataFrame, base_name: str) -> Tuple[bytes, bytes]:
    # CSV bytes
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    # XLSX bytes
    from io import BytesIO

    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Findings", index=False)
        summary = build_summary(df)
        summary.to_excel(w, sheet_name="Summary", index=False)

    xlsx_bytes = bio.getvalue()
    return csv_bytes, xlsx_bytes


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="CAPA Screening", layout="wide")
st.title("CAPA Screening – Recalls & Negative Press")

with st.expander("Security / Setup (read this once)", expanded=False):
    st.markdown(
        """
- **Do not hardcode API keys** in code. Use `st.secrets` or environment variables:
  - `OPENAI_API_KEY`
  - `GOOGLE_API_KEY`
  - `GOOGLE_CX_ID`
- If you pasted keys anywhere public, **rotate them**.
"""
    )

# Sidebar settings
st.sidebar.header("Search Settings")

date_mode = st.sidebar.selectbox(
    "Date Range",
    ["Last 30 days", "Last 60 days", "Last 90 days", "Last 180 days", "Last 365 days", "Custom"],
)

if date_mode == "Custom":
    default_start = date.today() - timedelta(days=365)
    start = st.sidebar.date_input("Start date", value=default_start)
    end = st.sidebar.date_input("End date", value=date.today())
    window = custom_window(start, end)
    google_days = None  # not exact for Google
else:
    days = int(date_mode.split()[1])
    window = preset_window(days)
    google_days = days

st.sidebar.caption(f"Window: {window.start.isoformat()} → {window.end.isoformat()}")

use_google = st.sidebar.checkbox("Google (Programmable Search)", value=True)
use_openfda_recall = st.sidebar.checkbox("openFDA Device Recall", value=True)
use_openfda_enforcement = st.sidebar.checkbox("openFDA Device Enforcement", value=True)
use_cpsc = st.sidebar.checkbox("CPSC Recalls", value=True)

fuzzy_threshold = st.sidebar.slider("Google fuzzy threshold", 0.0, 1.0, 0.70, 0.01)
keep_official_low = st.sidebar.checkbox("Keep low-score openFDA/CPSC hits", value=True)

st.sidebar.divider()
use_llm = st.sidebar.checkbox("Enable AI classification (agentic)", value=False)
llm_model = st.sidebar.text_input("LLM model", value="gpt-4.1-mini", disabled=not use_llm)
llm_sleep = st.sidebar.slider("LLM delay per hit (seconds)", 0.0, 2.0, 0.0, 0.1, disabled=not use_llm)

opts = RunOptions(
    use_google=use_google,
    use_openfda_recall=use_openfda_recall,
    use_openfda_enforcement=use_openfda_enforcement,
    use_cpsc=use_cpsc,
    google_days=google_days if use_google else None,
    fuzzy_threshold_google=float(fuzzy_threshold),
    keep_low_score_official_sources=bool(keep_official_low),
    use_llm=bool(use_llm),
    llm_model=str(llm_model),
    llm_sleep_seconds=float(llm_sleep),
)

tab1, tab2 = st.tabs(["Single Search", "Batch Upload"])

# ---- Single Search ----
with tab1:
    st.subheader("Single Search")
    colA, colB = st.columns(2)
    with colA:
        sku = st.text_input("SKU", value="")
    with colB:
        product_name = st.text_input("Product Name", value="")

    run_single = st.button("Run Search", type="primary", disabled=not product_name.strip())

    if run_single:
        llm_client = None
        if opts.use_llm:
            try:
                llm_client = ensure_openai_client()
            except Exception as e:
                st.error(f"OpenAI not configured: {e}")
                st.stop()

        if opts.use_google:
            try:
                ensure_google_secrets()
            except Exception as e:
                st.error(f"Google not configured: {e}")
                st.stop()

        with st.spinner("Searching sources..."):
            rows = search_one(sku.strip(), product_name.strip(), window, opts, llm_client=llm_client)

        if not rows:
            st.info("No hits found for the selected sources/date range.")
        else:
            df = add_flags(pd.DataFrame(rows))
            st.dataframe(df, use_container_width=True, hide_index=True)

            csv_bytes, xlsx_bytes = export_reports(df, base_name="single_search_report")
            st.download_button("Download CSV", data=csv_bytes, file_name="single_search_report.csv")
            st.download_button("Download XLSX", data=xlsx_bytes, file_name="single_search_report.xlsx")

# ---- Batch Upload ----
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

        if opts.use_google:
            try:
                ensure_google_secrets()
            except Exception as e:
                st.error(f"Google not configured: {e}")
                st.stop()

        st.write(f"Products loaded: **{len(products)}**")
        progress = st.progress(0.0)
        status = st.empty()

        all_rows: List[Dict[str, Any]] = []
        t0 = time.time()

        for i, r in products.iterrows():
            sku = str(r["SKU"]).strip()
            pn = str(r["Product Name"]).strip()
            status.write(f"Searching **{i+1}/{len(products)}**: `{sku}` – {pn}")

            rows = search_one(sku, pn, window, opts, llm_client=llm_client)
            all_rows.extend(rows)

            progress.progress((i + 1) / len(products))

        elapsed = time.time() - t0
        status.write(f"Done in {elapsed:.1f}s. Total hits: **{len(all_rows)}**")

        if not all_rows:
            st.info("No hits found for any uploaded products in the selected sources/date range.")
            st.stop()

        df = add_flags(pd.DataFrame(all_rows))

        # Helpful pivot-like view: best flag per SKU/Product Name
        best = (
            df.sort_values(["SKU", "Product Name", "FlagLevel", "FuzzyScore"], ascending=[True, True, True, False])
              .groupby(["SKU", "Product Name"], as_index=False)
              .first()
        )
        st.markdown("### Screening Overview (top hit per product)")
        st.dataframe(best[["SKU", "Product Name", "Source", "FlagLevel", "FuzzyScore", "Title", "URL"]], use_container_width=True, hide_index=True)

        st.markdown("### All Findings")
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv_bytes, xlsx_bytes = export_reports(df, base_name="batch_screening_report")
        st.download_button("Download CSV", data=csv_bytes, file_name="batch_screening_report.csv")
        st.download_button("Download XLSX", data=xlsx_bytes, file_name="batch_screening_report.xlsx")
