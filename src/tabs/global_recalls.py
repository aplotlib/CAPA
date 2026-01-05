import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from src.services.regulatory_service import RegulatoryService
from src.services.agent_service import RecallResponseAgent

def get_ai_service():
    """Retrieves AI Service from session state."""
    return st.session_state.get('ai_service')

def display_recalls_tab():
    st.header("🌍 Global Regulatory Intelligence & Media Monitor")
    st.caption("Advanced surveillance of FDA Recalls, Adverse Events (MAUDE), and Global Media.")

    ai = get_ai_service()
    
    # Initialize Session State
    if 'recall_hits' not in st.session_state: 
        st.session_state.recall_hits = pd.DataFrame()
    if 'recall_log' not in st.session_state: 
        st.session_state.recall_log = {}

    p_info = st.session_state.get('product_info', {})
    default_name = p_info.get('name', '')
    default_manufacturer = p_info.get('manufacturer', '')
    default_model = p_info.get('model', '')

    # --- CONTROL PANEL ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            st.markdown("### 🎯 Target")
            search_term = st.text_input("Device Name / Keyword", value=default_name, placeholder="e.g. Infusion Pump", key="intel_search")
            auto_expand = st.checkbox("Use AI Synonyms (Broaden Search)", value=True, help="AI will search for 'Infusion Pump', 'Syringe Pump', 'PCA', etc.")
        
        with c2:
            st.markdown("### 🏢 My Context")
            my_firm = st.text_input("My Manufacturer", value=default_manufacturer, placeholder="e.g. Medtronic", key="intel_firm")
            my_model = st.text_input("My Model", value=default_model, placeholder="e.g. MiniMed", key="intel_model")

        with c3:
            st.markdown("### 🚀 Action")
            st.write("")
            if st.button("RUN DEEP SCAN", type="primary", use_container_width=True):
                if not search_term:
                    st.error("Please enter a search term.")
                else:
                    run_comprehensive_scan(search_term, my_firm, my_model, auto_expand, ai)

    # --- DASHBOARD METRICS ---
    if not st.session_state.recall_hits.empty:
        df = st.session_state.recall_hits
        
        # Calculate Quick Stats
        total_hits = len(df)
        high_risk = len(df[df['Risk_Level'] == 'High']) if 'Risk_Level' in df.columns else 0
        media_hits = len(df[df['Source'] == 'Media'])
        adverse_events = len(df[df['Source'] == 'FDA MAUDE'])
        
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Intelligence Records", total_hits)
        m2.metric("High Risk / Critical", high_risk, delta_color="inverse")
        m3.metric("Adverse Events (MAUDE)", adverse_events)
        m4.metric("Negative Media Hits", media_hits)
        
        st.divider()

        # --- INTELLIGENCE FEED ---
        st.subheader("📡 Live Intelligence Feed")
        
        # Tabs for different views
        tab_feed, tab_data, tab_agent = st.tabs(["⚠️ Threat Feed", "📊 Raw Data Table", "🤖 AI Agent Actions"])
        
        with tab_feed:
            render_threat_feed(df)

        with tab_data:
            st.dataframe(
                df, 
                column_config={
                    "Link": st.column_config.LinkColumn("Source Link"),
                    "Date": st.column_config.DateColumn("Date"),
                },
                use_container_width=True
            )

        with tab_agent:
            render_agent_artifacts(df, ai)

    elif st.session_state.recall_log:
        st.info("Scan complete. No records found matching your criteria.")

def run_comprehensive_scan(term, my_firm, my_model, auto_expand, ai):
    """Orchestrates the multi-source search."""
    st.session_state.recall_hits = pd.DataFrame()
    st.session_state.recall_log = {}
    
    # 1. Expand Terms
    search_terms = [term]
    if auto_expand and ai:
        with st.spinner("AI is generating synonyms for broader coverage..."):
            try:
                synonyms = ai.generate_search_keywords(term, "")
                if synonyms:
                    search_terms.extend(synonyms)
                    st.toast(f"AI expanded search: {', '.join(synonyms)}")
            except Exception as e:
                print(f"Synonym error: {e}")
    
    # Remove duplicates
    search_terms = list(set(search_terms))
    
    # 2. Execute Search
    all_results = pd.DataFrame()
    logs = {}
    
    prog_bar = st.progress(0, "Initializing Global Scan...")
    status_text = st.empty()
    
    reg_service = RegulatoryService()
    
    total_steps = len(search_terms)
    for i, t in enumerate(search_terms):
        status_text.text(f"Scanning FDA, CPSC, Canada, UK, and News for: '{t}'...")
        prog_bar.progress((i)/total_steps)
        
        # Lookback 3 years by default
        start_date = datetime.now() - timedelta(days=365*3)
        end_date = datetime.now()
        
        results, batch_log = reg_service.search_all_sources(t, start_date, end_date)
        
        if not results.empty:
            all_results = pd.concat([all_results, results])
        
        # Aggregate logs
        for k, v in batch_log.items():
            logs[k] = logs.get(k, 0) + v
            
    prog_bar.progress(100)
    time.sleep(0.5)
    prog_bar.empty()
    status_text.empty()
    
    # 3. Post-Processing & Deduplication
    if not all_results.empty:
        # Deduplicate based on ID if possible, otherwise similar content
        all_results.drop_duplicates(subset=['ID'], inplace=True)
        
        # Basic Risk Scoring (Client-side Heuristic before AI Deep Dive)
        all_results['Risk_Level'] = all_results.apply(
            lambda x: heuristic_risk_score(x, my_firm, my_model), axis=1
        )
        
        # Sort: High Risk first, then by Date
        all_results.sort_values(by=['Risk_Level', 'Date'], ascending=[False, False], inplace=True)
        
    st.session_state.recall_hits = all_results
    st.session_state.recall_log = logs

def heuristic_risk_score(row, my_firm, my_model):
    """
    Assigns a preliminary risk level (High/Medium/Low) based on text matching.
    """
    text_blob = f"{row.get('Product','')} {row.get('Firm','')} {row.get('Description','')} {row.get('Reason','')}".lower()
    firm_match = my_firm.lower() in text_blob if my_firm else False
    model_match = my_model.lower() in text_blob if my_model else False
    
    # Critical Keywords
    is_death = 'death' in text_blob or 'fatal' in text_blob
    is_class_i = 'class i' in text_blob or 'class 1' in text_blob
    
    if (firm_match and model_match) or (firm_match and is_death):
        return "High"
    if firm_match or is_class_i or is_death:
        return "Medium"
    return "Low"

def render_threat_feed(df):
    """Renders the results as a modern feed."""
    for index, row in df.iterrows():
        risk = row.get('Risk_Level', 'Low')
        
        # Card Styling
        if risk == 'High':
            border_color = "#ef4444" # Red
            icon = "🚨"
        elif risk == 'Medium':
            border_color = "#f59e0b" # Orange
            icon = "⚠️"
        else:
            border_color = "#10b981" # Green
            icon = "ℹ️"
            
        with st.container(border=True):
            c1, c2 = st.columns([0.05, 0.95])
            with c1:
                st.markdown(f"## {icon}")
            with c2:
                # Header
                st.markdown(f"**{row['Source']}** | {row['Date']}")
                st.markdown(f"### {row['Product']}")
                
                # Details
                desc = row.get('Description', row.get('Reason', 'No description'))
                if len(str(desc)) > 300:
                    desc = str(desc)[:300] + "..."
                st.markdown(desc)
                
                # Metadata
                m1, m2, m3 = st.columns(3)
                if row.get('Firm') and row['Firm'] != 'Unknown':
                    m1.caption(f"**Firm:** {row['Firm']}")
                if row.get('ID'):
                    m2.caption(f"**ID:** {row['ID']}")
                
                # Link
                if row.get('Link'):
                    st.markdown(f"[Read Source Record]({row['Link']})")

def render_agent_artifacts(df, ai):
    """UI for the AI Agent to process the findings."""
    st.info("The Autonomous Agent can analyze these records to draft CAPAs or PR Statements.")
    
    if st.button("🤖 Activate Agent on Top Risks", type="primary"):
        if not ai:
            st.error("AI Service not connected.")
            return

        # Filter for top risks
        targets = df.head(5) # Analyze top 5 for demo speed
        
        agent = RecallResponseAgent()
        artifacts = []
        
        with st.status("Agent is analyzing risks...", expanded=True) as status:
            for i, row in targets.iterrows():
                status.write(f"Analyzing: {row['Product']}...")
                # Mocking the firm info from session state for the agent
                my_firm = st.session_state.product_info.get('manufacturer', '')
                my_model = st.session_state.product_info.get('model', '')
                
                # Execute agent analysis on single record
                # We reuse the agent's internal logic methods here
                try:
                    analysis = ai.assess_relevance_json(
                        f"Firm: {my_firm}, Model: {my_model}", 
                        f"{row['Product']} {row['Description']}"
                    )
                    
                    artifact = agent._execute_response_protocol(row, analysis.get('analysis', ''), row['Source'])
                    artifacts.append(artifact)
                except Exception as e:
                    print(e)
            
            status.update(label="Analysis Complete!", state="complete")
        
        # Display Generated Artifacts
        for art in artifacts:
            with st.expander(f"📦 Response Package: {art['source_record']['Product']}"):
                st.write(f"**AI Analysis:** {art['risk_analysis']}")
                
                c1, c2 = st.columns(2)
                if art.get('capa_draft'):
                    with c1:
                        st.markdown("#### Draft CAPA")
                        st.json(art['capa_draft'])
                
                if art.get('pr_draft'):
                    with c2:
                        st.markdown("#### Draft PR Statement")
                        st.info(art['pr_draft'])
