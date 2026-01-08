from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import List

import pandas as pd
import streamlit as st
import yaml

from src.ai_services import get_ai_service
from src.services.agent_service import RecallResponseAgent
from src.services.regulatory_service import RegulatoryService
from src.tabs.ai_chat import display_chat_interface
from src.tabs.web_search import display_web_search

DEFAULT_RECALL_KEYWORDS = "recall alert safety bulletin problem issue hazard warning defect"


st.set_page_config(
    page_title="CAPA Regulatory Intelligence Hub",
    layout="wide",
    page_icon="🛡️",
)


def apply_enterprise_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --primary: #005ea2;
            --primary-dark: #0b1f3b;
            --accent: #00a6d6;
            --bg: #f3f7fb;
            --card: #ffffff;
            --text: #0b1f3b;
            --muted: #5b6b7a;
            --border: #d6e2f0;
        }
        .main .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2.5rem;
        }
        .enterprise-header {
            background: linear-gradient(135deg, #005ea2 0%, #0b1f3b 55%, #132b49 100%);
            color: #ffffff;
            padding: 1.6rem 2rem;
            border-radius: 16px;
            box-shadow: 0 16px 32px rgba(15, 23, 42, 0.2);
            margin-bottom: 1.5rem;
        }
        .enterprise-header h1 {
            margin: 0;
            font-size: 1.8rem;
            letter-spacing: 0.02em;
        }
        .enterprise-header p {
            margin: 0.35rem 0 0;
            color: rgba(255, 255, 255, 0.85);
        }
        .badge-row {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.8rem;
            flex-wrap: wrap;
        }
        .badge {
            background: rgba(255, 255, 255, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.25);
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            font-size: 0.75rem;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.75rem;
            margin-top: 1rem;
        }
        .metric-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            box-shadow: 0 10px 20px rgba(11, 31, 59, 0.08);
        }
        .metric-title {
            color: var(--muted);
            font-size: 0.75rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .metric-value {
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--text);
        }
        .section-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.2rem;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
        }
        .sidebar .sidebar-content {
            background-color: var(--bg);
        }
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            padding: 0.55rem 1.2rem;
        }
        .stTextInput input, .stTextArea textarea {
            border-radius: 12px;
            border: 1px solid var(--border);
            background-color: #f9fbff;
        }
        .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 12px;
            border: 1px solid var(--border);
            background-color: #f9fbff;
        }
        .stCheckbox > label {
            padding: 0.35rem 0;
        }
        .status-card {
            background: linear-gradient(135deg, rgba(0, 94, 162, 0.16), rgba(0, 166, 214, 0.08));
            border: 1px solid rgba(0, 166, 214, 0.28);
            border-radius: 16px;
            padding: 1rem 1.2rem;
            margin-top: 0.5rem;
        }
        .tag {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.2rem 0.6rem;
            background: rgba(0, 94, 162, 0.14);
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            color: #004b84;
        }
        .fda-divider {
            height: 4px;
            border-radius: 999px;
            background: linear-gradient(90deg, #00a6d6, #005ea2, #0b1f3b);
            margin-top: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe_secret(key: str) -> str | None:
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def _normalize_gemini_key(api_key: str | None) -> tuple[str | None, str | None]:
    if not api_key:
        return None, None
    if api_key.startswith("sk-"):
        return None, "Gemini API key appears to be an OpenAI key. Check GEMINI_API_KEY/GOOGLE_API_KEY."
    return api_key, None


def init_session() -> None:
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = _safe_secret("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if "gemini_api_key" not in st.session_state:
        gemini_api_key = (
            _safe_secret("GEMINI_API_KEY")
            or _safe_secret("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        gemini_api_key, gemini_warning = _normalize_gemini_key(gemini_api_key)
        st.session_state.gemini_api_key = gemini_api_key
        st.session_state.gemini_key_warning = gemini_warning

    if "provider" not in st.session_state:
        if st.session_state.openai_api_key and st.session_state.gemini_api_key:
            st.session_state.provider = "both"
        elif st.session_state.gemini_api_key:
            st.session_state.provider = "gemini"
        else:
            st.session_state.provider = "openai"

    if "model_overrides" not in st.session_state:
        if os.path.exists("config.yaml"):
            with open("config.yaml", "r", encoding="utf-8") as config_file:
                config = yaml.safe_load(config_file) or {}
            st.session_state.model_overrides = config.get("ai_models", {})

    if "ai_service" not in st.session_state:
        if st.session_state.provider == "openai":
            st.session_state.api_key = st.session_state.openai_api_key
        elif st.session_state.provider == "gemini":
            st.session_state.api_key = st.session_state.gemini_api_key
        else:
            st.session_state.api_key = st.session_state.openai_api_key
        get_ai_service()

    st.session_state.setdefault("recall_hits", pd.DataFrame())
    st.session_state.setdefault("recall_log", {})
    st.session_state.setdefault("recall_agent", RecallResponseAgent())


def sidebar_controls() -> tuple[date, date, List[str], str]:
    st.sidebar.title("🛡️ Mission Control")
    st.sidebar.caption("Configure providers, time windows, and coverage zones.")

    provider_label_map = {
        "openai": "OpenAI",
        "gemini": "Gemini",
        "both": "OpenAI + Gemini",
    }
    provider_choice = st.sidebar.selectbox(
        "AI Provider",
        list(provider_label_map.values()),
        index=list(provider_label_map.keys()).index(st.session_state.provider),
    )
    selected_provider = {v: k for k, v in provider_label_map.items()}[provider_choice]
    if selected_provider != st.session_state.provider:
        st.session_state.provider = selected_provider
        if selected_provider == "gemini":
            st.session_state.api_key = st.session_state.gemini_api_key
        elif selected_provider == "openai":
            st.session_state.api_key = st.session_state.openai_api_key
        else:
            st.session_state.api_key = st.session_state.openai_api_key
        st.session_state.pop("ai_service", None)
        st.session_state.pop("recall_agent", None)
        st.session_state.recall_agent = RecallResponseAgent()

    st.sidebar.header("Search Window")
    date_mode = st.sidebar.selectbox(
        "Time Window",
        ["Last 30 days", "Last 90 days", "Last 1 Year", "Last 2 Years", "Custom"],
        index=2,
    )
    if date_mode == "Custom":
        start_date = st.sidebar.date_input("Start", value=date.today() - timedelta(days=365))
        end_date = st.sidebar.date_input("End", value=date.today())
    else:
        days_map = {"Last 30 days": 30, "Last 90 days": 90, "Last 1 Year": 365, "Last 2 Years": 730}
        days = days_map.get(date_mode, 365)
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

    st.sidebar.header("Coverage Regions")
    regions: List[str] = []
    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.checkbox("🇺🇸 US", value=True):
            regions.append("US")
        if st.checkbox("🇪🇺 EU", value=True):
            regions.append("EU")
    with c2:
        if st.checkbox("🇬🇧 UK", value=True):
            regions.append("UK")
        if st.checkbox("🇨🇦 Canada", value=True):
            regions.append("CA")

    if st.sidebar.checkbox("🌎 LATAM (BR/MX/CO)", value=True):
        regions.append("LATAM")

    if st.sidebar.checkbox("🌏 APAC", value=False):
        regions.append("APAC")

    mode_select = st.sidebar.radio(
        "Search Emphasis",
        ["🎯 Accuracy-first (APIs + Web + Media)", "⚡ Fast (APIs Only)"],
        index=0,
    )
    search_mode = "powerful" if "Accuracy" in mode_select else "fast"

    st.sidebar.header("Key Status")
    if st.session_state.provider in {"openai", "both"} and not st.session_state.openai_api_key:
        st.sidebar.warning("OpenAI API key not found in Streamlit secrets.")
    if st.session_state.provider in {"gemini", "both"} and not st.session_state.gemini_api_key:
        if st.session_state.get("gemini_key_warning"):
            st.sidebar.warning(st.session_state.gemini_key_warning)
        else:
            st.sidebar.warning("Gemini API key not found in Streamlit secrets.")

    st.sidebar.caption(f"📅 Range: {start_date} → {end_date}")
    return start_date, end_date, regions, search_mode


def render_search_summary(
    df: pd.DataFrame,
    logs: dict,
    query: str,
    manufacturer: str,
    regions: List[str],
    start_date: date,
    end_date: date,
    search_mode: str,
    use_default_keywords: bool,
) -> None:
    st.subheader("Coverage & Confidence")
    default_terms = DEFAULT_RECALL_KEYWORDS.split() if use_default_keywords else None
    terms = RegulatoryService.prepare_terms(
        query,
        manufacturer,
        max_terms=12 if search_mode == "powerful" else 10,
        extra_terms=default_terms,
    )

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-title">Total Results</div>
                <div class="metric-value">{len(df):,}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Sources Queried</div>
                <div class="metric-value">{len(logs)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Search Terms</div>
                <div class="metric-value">{len(terms)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Regions</div>
                <div class="metric-value">{", ".join(regions) if regions else "Global"}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "✨ Signal Boost: Default safety keywords are **enabled** to broaden matches."
        if use_default_keywords
        else "Signal Boost: Default safety keywords are **off**."
    )

    with st.expander("Search Coverage Details", expanded=False):
        st.markdown("**Search Inputs**")
        st.write(f"Product Query: **{query or '—'}**")
        st.write(f"Manufacturer: **{manufacturer or '—'}**")
        st.write(f"Date Range: **{start_date} → {end_date}**")
        st.write(f"Mode: **{search_mode.upper()}**")
        st.markdown("**Expanded Terms Used**")
        st.code("\n".join(terms) if terms else "No terms available", language="text")

        if logs:
            st.markdown("**Source Yield**")
            for source, count in logs.items():
                st.write(f"- {source}: {count}")


def render_smart_view(df: pd.DataFrame) -> None:
    risk_order = {"High": 0, "Medium": 1, "Low": 2, "TBD": 3}
    df = df.copy()
    df["Risk_Level"] = df.get("Risk_Level", "TBD").fillna("TBD")
    df["sort_key"] = df["Risk_Level"].map(risk_order).fillna(3)
    df.sort_values(["sort_key", "Date"], ascending=[True, False], inplace=True)

    for _, row in df.iterrows():
        risk = row.get("Risk_Level", "TBD")
        risk_color = "🔴" if risk == "High" else "🟠" if risk == "Medium" else "🟢" if risk == "Low" else "⚪"
        title = str(row.get("Product", "Unknown"))[:80]
        source = row.get("Source", "Unknown")
        date_str = row.get("Date", "N/A")
        matched_term = row.get("Matched_Term", "")
        label = f"{risk_color} {risk} | {date_str} | {source} | {title}"

        with st.expander(label):
            left, right = st.columns([3, 2])
            with left:
                st.markdown(f"**Product:** {row.get('Product', 'N/A')}")
                st.markdown(f"**Firm:** {row.get('Firm', 'N/A')}")
                st.markdown(f"**Model Info:** {row.get('Model Info', 'N/A')}")
                st.markdown(f"**Recall Class:** {row.get('Recall_Class', 'N/A')}")
                st.info(f"**Reason/Context:** {row.get('Reason', 'N/A')}")
                if matched_term:
                    st.caption(f"Matched term: {matched_term}")
            with right:
                st.markdown(f"**Description:** {row.get('Description', 'N/A')}")
                link = row.get("Link")
                if link:
                    st.markdown(f"[🔗 Open Source Record]({link})")


def render_table_view(df: pd.DataFrame) -> None:
    st.dataframe(
        df,
        column_config={"Link": st.column_config.LinkColumn("Source Link")},
        width="stretch",
        hide_index=True,
    )
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Download CSV", csv, "regulatory_results.csv", "text/csv")


def run_regulatory_search(
    query: str,
    manufacturer: str,
    vendor_only: bool,
    include_sanctions: bool,
    use_default_keywords: bool,
    regions: List[str],
    start_date: date,
    end_date: date,
    search_mode: str,
) -> None:
    extra_terms = DEFAULT_RECALL_KEYWORDS.split() if use_default_keywords else None
    focus_label = "vendor enforcement" if vendor_only else "recalls, alerts, and enforcement"
    with st.status(f"Running {search_mode} surveillance for {focus_label}...", expanded=True) as status:
        st.write("📡 Connecting to regulatory databases, sanctions lists, and trusted media sources...")
        df, logs = RegulatoryService.search_all_sources(
            query_term=query,
            manufacturer=manufacturer,
            vendor_only=vendor_only,
            include_sanctions=include_sanctions,
            regions=regions,
            start_date=start_date,
            end_date=end_date,
            limit=120,
            mode=search_mode,
            extra_terms=extra_terms,
        )

        st.session_state.recall_hits = df
        st.session_state.recall_log = logs
        st.session_state.search_context = {
            "query": query,
            "manufacturer": manufacturer,
            "use_default_keywords": use_default_keywords,
        }

        status.write(f"✅ Search Complete. Found {len(df)} records.")
        status.update(label="Mission Complete", state="complete", expanded=False)


def render_batch_scan(regions: List[str], default_start: date, default_end: date, default_mode: str) -> None:
    st.header("📂 Batch Fleet Scan")
    st.caption("Upload a list of Product Names (Column A) + SKUs (Column B) to scan for recalls in bulk.")

    st.session_state.setdefault("batch_results", pd.DataFrame())
    st.session_state.setdefault("batch_log", [])
    st.session_state.setdefault("batch_summary", {})
    st.session_state.setdefault("batch_no_matches", pd.DataFrame())

    with st.container(border=True):
        intro_left, intro_right = st.columns([2.2, 1.3])
        with intro_left:
            st.markdown(
                """
                **How this works**
                1. Upload a CSV/XLSX with Column A = Product Name, Column B = SKU.
                2. Optional Column C = Manufacturer/Vendor (for stricter matching).
                3. We expand each product name into optimized regulatory search terms.
                4. Results are fuzzy matched and risk scored for rapid triage.
                """
            )
            st.caption("Tip: Use exact device family names to reduce false positives.")
        with intro_right:
            template_df = pd.DataFrame(
                [
                    {"Product Name": "Infusion Pump", "SKU": "SKU-1001", "Manufacturer": "Acme Medical"},
                    {"Product Name": "Digital Blood Pressure Monitor", "SKU": "SKU-1002", "Manufacturer": "Acme Medical"},
                ]
            )
            template_bytes = template_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Template",
                template_bytes,
                "batch_scan_template.csv",
                "text/csv",
            )

    scan_left, scan_right = st.columns([2, 1])
    with scan_left:
        scan_file = st.file_uploader(
            "Upload CSV or Excel (Column A: Product Name, Column B: SKU, Column C: Manufacturer)",
            type=["csv", "xlsx"],
        )
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Start Date", value=default_start)
        end_date = col2.date_input("End Date", value=default_end)

    with scan_right:
        search_label = "Powerful" if default_mode == "powerful" else "Fast"
        st.markdown("**Search Depth**")
        st.info(f"{search_label} (mirrors Mission Control)")
        fuzzy_threshold = st.slider("Match Threshold", min_value=0.4, max_value=0.9, value=0.7, step=0.05)
        use_default_keywords = st.checkbox(
            "Use default safety keywords",
            value=True,
            help="Adds recall, alert, safety bulletin, and hazard keywords to broaden matches.",
        )

    if st.button("🚀 Run Batch Scan", type="primary", width="stretch"):
        if not scan_file:
            st.error("Please upload a CSV or Excel file.")
            return

        progress = st.progress(0.0, text="Preparing scan...")
        agent: RecallResponseAgent = st.session_state.recall_agent

        def progress_callback(pct: float, message: str) -> None:
            progress.progress(pct, text=message)

        with st.spinner("Scanning product list..."):
            extra_terms = DEFAULT_RECALL_KEYWORDS.split() if use_default_keywords else None
            mode_key = "powerful" if default_mode == "powerful" else "fast"
            results, no_matches, log_messages = agent.run_bulk_scan(
                scan_file,
                start_date=start_date,
                end_date=end_date,
                fuzzy_threshold=fuzzy_threshold,
                progress_callback=progress_callback,
                regions=regions,
                mode=mode_key,
                extra_terms=extra_terms,
            )
        progress.empty()

        st.session_state.batch_results = results
        st.session_state.batch_log = log_messages
        st.session_state.batch_no_matches = no_matches
        scanned_count = 0
        if "My SKU" in results.columns:
            scanned_count += results["My SKU"].nunique()
        if not no_matches.empty:
            scanned_count += no_matches["SKU"].nunique()
        st.session_state.batch_summary = {
            "products_scanned": scanned_count,
            "matches_found": len(results),
            "search_depth": search_label,
        }

    if not st.session_state.batch_results.empty or not st.session_state.batch_no_matches.empty:
        summary = st.session_state.batch_summary
        metric_left, metric_center, metric_right = st.columns(3)
        metric_left.metric("Products Scanned", summary.get("products_scanned", "-"))
        metric_center.metric("Potential Matches", summary.get("matches_found", "-"))
        metric_right.metric("Search Depth", summary.get("search_depth", "-"))
        st.caption("🔎 Summary aligns to the Mission Control coverage window and search depth.")

        if not st.session_state.batch_results.empty:
            st.dataframe(st.session_state.batch_results, width="stretch", hide_index=True)
            csv = st.session_state.batch_results.to_csv(index=False).encode("utf-8")
            st.download_button("💾 Download Batch Results", csv, "batch_scan_results.csv", "text/csv")
        if st.session_state.batch_log:
            st.caption(", ".join(st.session_state.batch_log))
        if st.session_state.batch_results.empty:
            st.warning("No matches found. Consider lowering the match threshold or extending the date range.")

    if not st.session_state.batch_no_matches.empty:
        st.subheader("✅ No-Match Attestation")
        st.caption("Export no-match results with an attestation for audit evidence.")
        reviewed = st.checkbox("I attest these no-match records were manually reviewed for accuracy.")
        reviewer_name = st.text_input("Reviewer name")
        if reviewed and reviewer_name.strip():
            attested = st.session_state.batch_no_matches.copy()
            attested["Reviewed By"] = reviewer_name.strip()
            attested["Reviewed At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            no_match_csv = attested.to_csv(index=False).encode("utf-8")
            st.download_button(
                "🧾 Download No-Match Attestation (CSV)",
                no_match_csv,
                "batch_no_match_attestation.csv",
                "text/csv",
            )
        elif reviewed:
            st.info("Enter a reviewer name to enable the attestation download.")


init_session()
apply_enterprise_theme()
start_date, end_date, regions, search_mode = sidebar_controls()

st.markdown(
    """
    <div class="enterprise-header">
        <h1>CAPA Regulatory Intelligence Hub</h1>
        <p>Enterprise-grade regulatory surveillance spanning recalls, enforcement actions, sanctions, and media signals.</p>
        <div class="badge-row">
            <span class="badge">FDA-Inspired Oversight</span>
            <span class="badge">ISO 13485 Ready</span>
            <span class="badge">MedTech Focus</span>
            <span class="badge">Audit Trail Friendly</span>
        </div>
        <div class="fda-divider"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_labels = ["🔎 Regulatory Search", "📂 Batch Fleet Scan", "💬 AI Assistant", "🌐 Web Search"]
tab_search, tab_batch, tab_chat, tab_web = st.tabs(tab_labels)

with tab_search:
    st.header("🔎 Regulatory Search")
    st.caption("Find recalls, safety notices, and enforcement actions with expanded coverage.")

    with st.container(border=True):
        with st.form("regulatory_search_form"):
            form_col1, form_col2 = st.columns([2, 2])
            with form_col1:
                query = st.text_input("Product Name / Keyword", placeholder="e.g. Infusion Pump")
            with form_col2:
                manufacturer_query = st.text_input(
                    "Manufacturer / Vendor (optional)", placeholder="e.g. Acme Medical Devices"
                )

            settings_col1, settings_col2, settings_col3 = st.columns([1, 1, 1])
            with settings_col1:
                vendor_only = st.checkbox("Vendor-only enforcement search", value=False)
            with settings_col2:
                include_sanctions = st.checkbox("Include sanctions & watchlists", value=True)
            with settings_col3:
                use_default_keywords = st.checkbox(
                    "Use default safety keywords",
                    value=True,
                    help="Adds recall, alert, safety bulletin, and problem keywords to broaden matches.",
                )
                run_btn = st.form_submit_button("🚀 Run Surveillance", width="stretch", type="primary")

    boost_label = (
        "Signal Boost is on: safety keywords will expand the search net."
        if use_default_keywords
        else "Signal Boost is off: searching only your exact product/manufacturer keywords."
    )
    boost_tag = "Enabled" if use_default_keywords else "Disabled"
    st.markdown(
        f"""
        <div class="status-card">
            <span class="tag">✨ Signal Boost • {boost_tag}</span>
            <div style="margin-top:0.35rem;">{boost_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if run_btn:
        if not query and not manufacturer_query:
            st.error("Enter a product keyword or manufacturer/vendor name.")
        elif vendor_only and not manufacturer_query:
            st.error("Vendor-only mode requires a manufacturer/vendor name.")
        else:
            run_regulatory_search(
                query=query,
                manufacturer=manufacturer_query,
                vendor_only=vendor_only,
                include_sanctions=include_sanctions,
                use_default_keywords=use_default_keywords,
                regions=regions,
                start_date=start_date,
                end_date=end_date,
                search_mode=search_mode,
            )

    df = st.session_state.recall_hits
    logs = st.session_state.recall_log
    search_context = st.session_state.get("search_context", {})
    active_query = query or search_context.get("query", "")
    active_manufacturer = manufacturer_query or search_context.get("manufacturer", "")
    active_default_keywords = search_context.get("use_default_keywords", use_default_keywords)

    if not df.empty:
        with st.container(border=True):
            render_search_summary(
                df=df,
                logs=logs,
                query=active_query,
                manufacturer=active_manufacturer,
                regions=regions,
                start_date=start_date,
                end_date=end_date,
                search_mode=search_mode,
                use_default_keywords=active_default_keywords,
            )

        st.divider()
        filter_col1, filter_col2 = st.columns([1, 1])
        with filter_col1:
            sources = ["All"] + sorted(df["Source"].dropna().unique().tolist())
            selected_source = st.selectbox("Filter by Source", sources)
        with filter_col2:
            risks = ["All"] + sorted(df["Risk_Level"].fillna("TBD").unique().tolist())
            selected_risk = st.selectbox("Filter by Risk Level", risks)

        filtered_df = df.copy()
        if selected_source != "All":
            filtered_df = filtered_df[filtered_df["Source"] == selected_source]
        if selected_risk != "All":
            filtered_df = filtered_df[filtered_df["Risk_Level"] == selected_risk]

        tab_smart, tab_table = st.tabs(["⚡ Smart Review", "📊 Data Table"])
        with tab_smart:
            render_smart_view(filtered_df)
        with tab_table:
            render_table_view(filtered_df)
    elif logs:
        st.info("No records found for the current search parameters.")

with tab_batch:
    render_batch_scan(regions, start_date, end_date, search_mode)

with tab_chat:
    display_chat_interface()

with tab_web:
    display_web_search()
