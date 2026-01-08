import re
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import difflib
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
        df, stats = RegulatoryService.search_all_sources_safe(
            query_term=search_term,
            start_date=start_date,
            end_date=datetime.now(),
            limit=50,
            manufacturer=my_firm,
            include_sanctions=True,
        )
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

    def run_bulk_scan(self, file_obj, start_date, end_date, fuzzy_threshold=0.6, progress_callback=None):
        """
        Runs surveillance on a list of products provided in an Excel/CSV file.
        Format: Col A = SKU, Col B = Product Name.
        """
        try:
            # Parse File
            if file_obj.name.endswith('.csv'):
                df_input = pd.read_csv(file_obj)
            else:
                df_input = pd.read_excel(file_obj)
            
            # Normalize headers (take first two columns regardless of name)
            if len(df_input.columns) < 2:
                return pd.DataFrame(), ["Error: File must have at least 2 columns (SKU, Product Name)."]
            
            # Rename for consistency
            df_input = df_input.iloc[:, :2]
            df_input.columns = ['SKU', 'Product Name']
            df_input = df_input.dropna(subset=['Product Name'])
        except Exception as e:
            return pd.DataFrame(), [f"Error parsing file: {e}"]

        consolidated_results = []
        total_items = len(df_input)
        
        for idx, row in df_input.iterrows():
            sku = str(row['SKU'])
            p_name = str(row['Product Name'])
            cleaned_name = self._clean_product_name(p_name)

            if progress_callback:
                progress = (idx + 1) / total_items
                progress_callback(progress, f"Scanning {idx+1}/{total_items}: {p_name}...")

            search_terms = self._generate_search_terms(cleaned_name)
            hits_frames = []
            for term in search_terms:
                if not term:
                    continue
                hits, _ = RegulatoryService.search_all_sources_safe(
                    query_term=term,
                    start_date=start_date,
                    end_date=end_date,
                    limit=20,
                )
                if not hits.empty:
                    hits = hits.copy()
                    hits["Search Term"] = term
                    hits_frames.append(hits)

            if hits_frames:
                hits = pd.concat(hits_frames, ignore_index=True)
                hits = RegulatoryService._dedupe(hits)
            else:
                hits = pd.DataFrame()
            
            if not hits.empty:
                # 2. FUZZY MATCH FILTERING
                for h_idx, hit in hits.iterrows():
                    hit_product = str(hit.get('Product', '')).lower()
                    target_product = cleaned_name.lower()
                    term_matches = any(term.lower() in hit_product for term in search_terms if term)
                    
                    # Calculate similarity ratio
                    score = self._fuzzy_score(target_product, hit_product)
                    
                    # If score is good OR the product name is explicitly in the hit text
                    if score >= fuzzy_threshold or target_product in hit_product or term_matches:
                        # Append to results
                        consolidated_results.append({
                            "My SKU": sku,
                            "My Product": p_name,
                            "Match Score": f"{score:.2f}",
                            "Source": hit['Source'],
                            "Date": hit['Date'],
                            "Found Product": hit['Product'],
                            "Reason": hit['Reason'],
                            "Risk Level": "High" if score > 0.8 else "Medium",
                            "Link": hit['Link']
                        })

        results_df = pd.DataFrame(consolidated_results)
        if results_df.empty:
            return results_df, ["No results found."]
        return results_df, ["Success"]

    def _fuzzy_score(self, s1, s2):
        """Calculates fuzzy similarity ratio between two strings."""
        if not s1 or not s2: return 0.0
        return difflib.SequenceMatcher(None, s1, s2).ratio()

    def _clean_product_name(self, product_name: str) -> str:
        if not product_name:
            return ""
        cleaned = re.sub(r"\bvive\b", "", product_name, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _generate_search_terms(self, product_name: str) -> list:
        base_name = self._clean_product_name(product_name)
        if not base_name:
            return []

        prompt = (
            "Extract 3-6 short, generic product keywords for regulatory recall searching. "
            "Exclude brand names and vendors. Ignore the word 'Vive' entirely. "
            "Return a comma-separated list only.\n\n"
            f"Product name: {base_name}"
        )
        keywords_text = ""
        try:
            keywords_text = self.ai._generate_text(prompt)
        except Exception:
            keywords_text = ""

        keywords = []
        if keywords_text and "Error:" not in keywords_text:
            keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]

        keywords = [self._clean_product_name(k) for k in keywords if k]
        keywords = [k for k in keywords if k]
        if base_name not in keywords:
            keywords.insert(0, base_name)

        seen = set()
        deduped = []
        for term in keywords:
            lower = term.lower()
            if lower in seen:
                continue
            seen.add(lower)
            deduped.append(term)
        return deduped

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
