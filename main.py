from __future__ import annotations

import os
import time
import pandas as pd
import streamlit as st
import yaml
from datetime import date, datetime, timedelta

# Import Services and Tabs
from src.services.regulatory_service import RegulatoryService
from src.ai_services import get_ai_service
from src.tabs.ai_chat import display_chat_interface
from src.tabs.web_search import display_web_search

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="CAPA Regulatory Agent", 
    layout="wide", 
    page_icon="🛡️"
)

# ============================================================
# SESSION & API SETUP
# ============================================================
def init_session():
    if "GOOGLE_API_KEY" not in st.secrets and "GOOGLE_API_KEY" in os.environ:
        pass 

    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

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

    if 'ai_service' not in st.session_state:
        if st.session_state.provider == "openai":
            st.session_state.api_key = st.session_state.openai_api_key
        elif st.session_state.provider == "gemini":
            st.session_state.api_key = st.session_state.gemini_api_key
        get_ai_service()

init_session()

# ============================================================
# SIDEBAR CONFIGURATION
# ============================================================
st.sidebar.title("🛡️ Mission Control")

st.sidebar.header("0. AI Controls")
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
    st.session_state.pop("ai_service", None)

verbosity = st.sidebar.select_slider(
    "Verbosity",
    options=["Pithy", "Balanced", "Verbose"],
    value=st.session_state.get("verbosity", "Balanced"),
)
st.session_state.verbosity = verbosity

if st.session_state.provider == "openai":
    st.session_state.api_key = st.session_state.openai_api_key
elif st.session_state.provider == "gemini":
    st.session_state.api_key = st.session_state.gemini_api_key
else:
    st.session_state.api_key = st.session_state.openai_api_key

if st.session_state.provider in {"openai", "both"} and not st.session_state.openai_api_key:
    st.sidebar.warning("OpenAI API key not found in Streamlit secrets.")
if st.session_state.provider in {"gemini", "both"} and not st.session_state.gemini_api_key:
    st.sidebar.warning("Gemini API key not found in Streamlit secrets.")

st.sidebar.header("1. Search Scope")
date_mode = st.sidebar.selectbox(
    "Time Window",
    ["Last 30 days", "Last 90 days", "Last 1 Year", "Last 2 Years", "Custom"],
    index=2
)

if date_mode == "Custom":
    start_date = st.sidebar.date_input("Start", value=date.today() - timedelta(days=365))
    end_date = st.sidebar.date_input("End", value=date.today())
else:
    days_map = {"Last 30 days": 30, "Last 90 days": 90, "Last 1 Year": 365, "Last 2 Years": 730}
    days = days_map.get(date_mode, 365)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

st.sidebar.caption(f"📅 Range: {start_date} → {end_date}")

st.sidebar.header("2. Target Regions")
regions = []
c1, c2 = st.sidebar.columns(2)
with c1:
    if st.checkbox("🇺🇸 US", value=True): regions.append("US")
    if st.checkbox("🇪🇺 EU", value=True): regions.append("EU")
with c2:
    if st.checkbox("🇬🇧 UK", value=True): regions.append("UK")
    if st.checkbox("🇨🇦 Canada", value=True): regions.append("CA")

if st.sidebar.checkbox("🌎 LATAM (BR/MX/CO)", value=True): regions.append("LATAM")

if st.sidebar.checkbox("🌏 APAC", value=False): regions.append("APAC")

mode_select = st.sidebar.radio(
    "Agent Mode",
    ["⚡ Fast (APIs + Snippets)", "🧠 Powerful (Agentic Verify)"],
)
search_mode = "powerful" if "Powerful" in mode_select else "fast"

ai = get_ai_service()

# ============================================================
# MAIN TABS
# ============================================================
st.title("🛡️ Global Regulatory Intelligence Agent")

# Define Tabs
tab_search, tab_batch, tab_chat, tab_web = st.tabs([
    "🔎 Regulatory Search", 
    "📂 Batch Fleet Scan", 
    "💬 AI Assistant",
    "🌐 Web Search"
])

# ------------------------------------------------------------
# TAB 1: REGULATORY SEARCH
# ------------------------------------------------------------
with tab_search:
    col_search, col_act = st.columns([3, 1])
    with col_search:
        query = st.text_input("Enter Product Name / Keyword", placeholder="e.g. Infusion Pump")
        manufacturer_query = st.text_input("Manufacturer / Vendor (optional)", placeholder="e.g. Acme Medical Devices")
    with col_act:
        st.write("")
        st.write("")
        vendor_only = st.checkbox("Vendor-only search", value=False)
        include_sanctions = st.checkbox("Sanctions & Watchlists", value=True)
        run_btn = st.button("🚀 Run Surveillance", type="primary", use_container_width=True)

    if run_btn:
        if not query and not manufacturer_query:
            st.error("Enter a product keyword or manufacturer/vendor name.")
        elif vendor_only and not manufacturer_query:
            st.error("Vendor-only mode requires a manufacturer/vendor name.")
        elif search_mode == "powerful" and not ai:
            st.error("⚠️ Powerful mode requires a configured AI provider API key.")
        else:
            focus_label = "vendor enforcement" if vendor_only else "recalls, alerts, and enforcement"
            with st.status(f"Agent running {search_mode} surveillance for {focus_label}...", expanded=True) as status:
                st.write("📡 Connecting to Global Regulatory Databases, Media, and Sanctions Lists...")
                
                df, logs = RegulatoryService.search_all_sources(
                    query_term=query,
                    manufacturer=manufacturer_query,
                    vendor_only=vendor_only,
                    include_sanctions=include_sanctions,
                    regions=regions,
                    start_date=start_date,
                    end_date=end_date,
                    limit=100,
                    mode=search_mode,
                    ai_service=ai
                )
                
                st.session_state.recall_hits = df
                st.session_state.recall_log = logs
                
                status.write(f"✅ Search Complete. Found {len(df)} records.")
                status.update(label="Mission Complete", state="complete", expanded=False)
