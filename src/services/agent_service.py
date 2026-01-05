# src/services/agent_service.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.services.regulatory_service import RegulatoryService
from src.ai_services import get_ai_service

class RecallResponseAgent:
    """
    An autonomous agent that monitors regulatory databases, adverse events, and media.
    Identifies risks and proactively drafts quality documentation (CAPAs, Emails, PR Statements).
    """
    
    def __init__(self):
        self.ai = get_ai_service()
        self.regulatory = RegulatoryService()

    def run_mission(self, search_term, my_firm, my_model, lookback_days=365):
        """
        Executes the full agent workflow: Search -> Analyze -> Draft -> Report.
        """
        mission_log = []
        artifacts = []
        
        # --- PHASE 1: SURVEILLANCE ---
        self._log(mission_log, f"🕵️‍♂️ STARTING MISSION: Surveillance for '{search_term}'...")
        start_date = datetime.now() - timedelta(days=lookback_days)
        
        # 1. Search (Now includes MAUDE and Media)
        df, stats = self.regulatory.search_all_sources(search_term, start_date, datetime.now(), limit=50)
        total_hits = len(df)
        self._log(mission_log, f"✅ SCAN COMPLETE. Found {total_hits} records. Stats: {stats}")

        if df.empty:
            self._log(mission_log, "🏁 MISSION END: No records found.")
            return mission_log, artifacts

        # --- PHASE 2: INTELLIGENCE & FILTERING ---
        self._log(mission_log, f"🧠 ANALYZING: Screening top 25 newest records for relevance to '{my_model}'...")
        
        target_df = df.head(25).copy()
        high_risk_found = False
        
        for index, row in target_df.iterrows():
            source_type = row.get("Source", "Unknown")
            
            # Construct context for the AI
            record_text = f"Source: {source_type}\nProduct: {row['Product']}\nReason/Desc: {row['Reason']}\nFirm: {row['Firm']}"
            my_context = f"My Firm: {my_firm}\nMy Model: {my_model}"
            
            # AI Decision
            try:
                assessment = self.ai.assess_relevance_json(my_context, record_text)
                risk_level = assessment.get("risk", "Low")
                analysis = assessment.get("analysis", "")
                
                # Check for High Risk OR specific source triggers (e.g. Media spikes)
                if risk_level == "High":
                    high_risk_found = True
                    self._log(mission_log, f"🚨 THREAT DETECTED [{source_type}]: {row['Product'][:30]}... ({analysis})")
                    
                    # --- PHASE 3: AUTONOMOUS ACTION ---
                    artifact = self._execute_response_protocol(row, analysis, source_type)
                    artifacts.append(artifact)
                    
            except Exception as e:
                self._log(mission_log, f"⚠️ ERROR analyzing row {index}: {str(e)}")

        if not high_risk_found:
            self._log(mission_log, "🛡️ STATUS: No immediate high-risk threats detected in sample.")

        self._log(mission_log, f"🏁 MISSION COMPLETE. Generated {len(artifacts)} response packages.")
        return mission_log, artifacts

    def _execute_response_protocol(self, record, analysis, source_type):
        """
        Chains tasks based on the SOURCE of the threat.
        """
        capa_draft = None
        email_draft = None
        pr_draft = None
        
        # Protocol A: Recall or Adverse Event -> CAPA + Supplier Email
        if "FDA" in source_type or "CPSC" in source_type or "MHRA" in source_type:
            capa_draft = self._draft_capa_content(record, analysis)
            email_draft = self._draft_vendor_email(record)
            
        # Protocol B: Media/News -> PR Statement + Internal Memo
        if "Media" in source_type:
            pr_draft = self._draft_pr_statement(record, analysis)
            # Media issues might not need a CAPA immediately, but an investigation record
            capa_draft = self._draft_capa_content(record, analysis, is_media=True)

        return {
            "source_record": record,
            "risk_analysis": analysis,
            "capa_draft": capa_draft,
            "email_draft": email_draft,
            "pr_draft": pr_draft,
            "source_type": source_type
        }

    def _draft_capa_content(self, record, analysis, is_media=False):
        """Drafts CAPA content."""
        context_note = "A high-risk regulatory event" if not is_media else "Negative media coverage representing a reputational/safety risk"
        prompt = f"""
        CONTEXT: {context_note} was found matching our product type.
        Product: {record['Product']}
        Issue: {record['Reason']}
        AI Analysis: {analysis}
        
        TASK: Draft a JSON object for a CAPA initiation form.
        Fields: "issue_description", "root_cause_investigation_plan", "containment_action".
        """
        return self.ai._generate_json(prompt, system_instruction="You are a QA Manager drafting a CAPA.")

    def _draft_vendor_email(self, record):
        """Drafts a demand letter to the vendor."""
        prompt = f"""
        CONTEXT: We detected a regulatory issue for a product we might distribute.
        Product: {record['Product']}
        Issue: {record['Reason']}
        
        TASK: Write a professional email to the vendor asking for:
        1. Confirmation if our lots are affected.
        2. Root cause analysis.
        """
        return self.ai._generate_text(prompt)

    def _draft_pr_statement(self, record, analysis):
        """Drafts a PR statement for media handling."""
        prompt = f"""
        CONTEXT: Negative media coverage detected.
        Headline: {record['Description']}
        AI Analysis: {analysis}
        
        TASK: Draft a short internal specific holding statement (PR response) to be used if media inquiries arise.
        Tone: Professional, concerned, committed to safety.
        """
        return self.ai._generate_text(prompt)

    def _log(self, log_list, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_list.append(f"[{timestamp}] {message}")
