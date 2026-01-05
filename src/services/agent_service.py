# src/services/agent_service.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.services.regulatory_service import RegulatoryService
from src.ai_services import get_ai_service

class RecallResponseAgent:
    """
    An autonomous agent that monitors regulatory databases, identifies risks,
    and proactively drafts quality documentation (CAPAs, Emails).
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
        
        # 1. Search
        df, stats = self.regulatory.search_all_sources(search_term, start_date, datetime.now(), limit=50)
        total_hits = len(df)
        self._log(mission_log, f"✅ SCAN COMPLETE. Found {total_hits} raw records. Sources: {stats}")

        if df.empty:
            self._log(mission_log, "🏁 MISSION END: No records found.")
            return mission_log, artifacts

        # --- PHASE 2: INTELLIGENCE & FILTERING ---
        self._log(mission_log, f"🧠 ANALYZING: Screening top 20 newest records for relevance to '{my_model}'...")
        
        # Filter top 20 to manage tokens/latency
        target_df = df.head(20).copy()
        high_risk_found = False
        
        for index, row in target_df.iterrows():
            # Construct context for the AI
            record_text = f"Product: {row['Product']}\nReason: {row['Reason']}\nFirm: {row['Firm']}"
            my_context = f"My Firm: {my_firm}\nMy Model: {my_model}"
            
            # AI Decision
            try:
                assessment = self.ai.assess_relevance_json(my_context, record_text)
                risk_level = assessment.get("risk", "Low")
                analysis = assessment.get("analysis", "")
                
                if risk_level == "High":
                    high_risk_found = True
                    self._log(mission_log, f"🚨 HIGH RISK DETECTED: {row['Product'][:30]}... ({analysis})")
                    
                    # --- PHASE 3: AUTONOMOUS ACTION ---
                    # Trigger the 'Response Protocol' for high risk items
                    artifact = self._execute_response_protocol(row, analysis)
                    artifacts.append(artifact)
                    
            except Exception as e:
                self._log(mission_log, f"⚠️ ERROR analyzing row {index}: {str(e)}")

        if not high_risk_found:
            self._log(mission_log, "🛡️ STATUS: No immediate high-risk threats detected in sample.")

        self._log(mission_log, f"🏁 MISSION COMPLETE. Generated {len(artifacts)} response packages.")
        return mission_log, artifacts

    def _execute_response_protocol(self, record, analysis):
        """
        Chains tasks to generate CAPA and Email drafts for a high-risk record.
        """
        # Action 1: Draft CAPA
        capa_draft = self._draft_capa_content(record, analysis)
        
        # Action 2: Draft Vendor Email
        email_draft = self._draft_vendor_email(record)
        
        return {
            "source_record": record,
            "risk_analysis": analysis,
            "capa_draft": capa_draft,
            "email_draft": email_draft
        }

    def _draft_capa_content(self, record, analysis):
        """Uses AI to hallucinate a starting point for the CAPA based on the recall."""
        prompt = f"""
        CONTEXT: A high-risk recall was found matching our product type.
        Recall Product: {record['Product']}
        Recall Reason: {record['Reason']}
        AI Analysis: {analysis}
        
        TASK: Draft a JSON object for a CAPA initiation form.
        Fields required: "issue_description", "root_cause_investigation_plan", "containment_action".
        
        Write in technical, medical device quality assurance language (ISO 13485).
        """
        return self.ai._generate_json(prompt, system_instruction="You are a QA Manager drafting a CAPA.")

    def _draft_vendor_email(self, record):
        """Drafts a demand letter to the vendor."""
        prompt = f"""
        CONTEXT: We detected a recall for a product we might distribute or use.
        Product: {record['Product']}
        Firm: {record['Firm']}
        Reason: {record['Reason']}
        
        TASK: Write a professional email to the vendor asking for:
        1. Confirmation if our lots are affected.
        2. Their root cause analysis report.
        3. Timeline for replacement.
        """
        return self.ai._generate_text(prompt)

    def _log(self, log_list, message):
        """Adds a timestamped message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_list.append(f"[{timestamp}] {message}")
