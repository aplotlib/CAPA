# src/services/agent_service.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.services.regulatory_service import RegulatoryService
from src.ai_services import get_ai_service
from src.utils import calculate_fuzzy_similarity

class RecallResponseAgent:
    """
    An autonomous agent that monitors regulatory databases, adverse events, and media.
    Identifies risks and proactively drafts quality documentation.
    """
    
    def __init__(self):
        self.ai = get_ai_service()
        self.regulatory = RegulatoryService()

    def run_batch_mission(self, df_products, start_date, end_date, progress_callback=None):
        """
        Runs the surveillance mission on a batch of products from an uploaded file.
        Uses fuzzy matching to filter results.
        """
        batch_results = []
        total_products = len(df_products)
        
        for idx, row in df_products.iterrows():
            sku = str(row.get('SKU', 'N/A'))
            product_name = str(row.get('Product Name', 'Unknown'))
            
            if progress_callback:
                progress_callback((idx + 1) / total_products, f"Scanning SKU {sku}: {product_name}...")

            # 1. Search Logic
            # We search for the Product Name.
            # We enforce the date range selected by the user.
            results_df, _ = self.regulatory.search_all_sources(product_name, start_date, end_date, limit=20)
            
            if results_df.empty:
                batch_results.append({
                    "SKU": sku, "Product Name": product_name, "Date": "N/A", "Source": "N/A", 
                    "Issue Description": "No records found", "Risk Level": "Low", "Match Score": 0, "Link": "N/A"
                })
                continue
            
            # 2. Fuzzy Match & Filter
            # Iterate through search results and check if they ACTUALLY match the input product
            # This prevents "Infusion Pump" search finding "Pool Pump".
            for _, res in results_df.iterrows():
                title = res.get('Product', '') or res.get('Description', '')
                
                # Calculate Similarity
                score = calculate_fuzzy_similarity(product_name, title)
                
                # Thresholds:
                # - Match Score > 60: Likely relevant
                # - Risk Level: Determine based on Source (Class I Recall = High)
                
                risk = "Low"
                if "Class I" in str(res.get('Reason', '')): risk = "High"
                elif "Death" in str(res.get('Reason', '')): risk = "High"
                elif "Class II" in str(res.get('Reason', '')): risk = "Medium"
                
                # If score is very low, it's likely noise, unless AI overrides (skipped here for speed)
                if score > 45: 
                    batch_results.append({
                        "SKU": sku,
                        "Product Name": product_name,
                        "Date": res['Date'],
                        "Source": res['Source'],
                        "Issue Description": res['Reason'],
                        "Risk Level": risk,
                        "Match Score": int(score),
                        "Link": res['Link']
                    })

        return pd.DataFrame(batch_results)

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
