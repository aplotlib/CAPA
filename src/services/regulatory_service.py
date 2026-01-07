"""
    Unified Regulatory Intelligence Engine.
    Integrates OpenFDA, CPSC, and Google Custom Search (Global Web/Regulators).
    Includes Agentic capabilities to visit and verify links.
    """
    
    # Configuration
    FDA_BASE = "https://api.fda.gov"
    CPSC_BASE = "https://www.saferproducts.gov/RestWebServices/Recall"
    GOOGLE_URL = "https://customsearch.googleapis.com/customsearch/v1"

    # Targeted Domains for "Regulatory" Search Category by Region
    REGIONAL_DOMAINS = {
        "US": [
            "fda.gov",
            "openfda.gov",
            "saferproducts.gov",
            "cpsc.gov",
            "cdc.gov",
        ],
        "UK": [
            "gov.uk",
            "mhra.gov.uk",
            "nhs.uk",
        ],
        "CA": [
            "canada.ca",
            "healthycanadians.gc.ca",
            "recalls-rappels.gc.ca",
            "healthcanada.gc.ca",
        ],
        "EU": [
            "europa.eu",
            "ema.europa.eu",
            "ec.europa.eu",
            "echa.europa.eu",
        ],
        "LATAM": [
            "anvisa.gov.br",
            "cofepris.gob.mx",
            "invima.gov.co",
            "minsalud.gov.co",
        ],
        "APAC": [
            "tga.gov.au",
            "pmda.go.jp",
            "hsa.gov.sg",
        ],
    }

    SANCTIONS_DOMAINS = [
        "treasury.gov",
        "hmt-sanctions.s3.eu-west-2.amazonaws.com",
        "ec.europa.eu",
        "un.org/securitycouncil",
    ]

    SYNONYM_MAP = {
        "bpm": ["blood pressure monitor", "bp monitor", "sphygmomanometer"],
        "blood pressure monitor": ["bpm", "bp monitor", "blood pressure machine"],
        "scooter": ["mobility scooter", "powered scooter", "electric scooter"],
        "pacemaker": ["cardiac pacemaker", "implantable pacemaker"],
        "defibrillator": ["aed", "automated external defibrillator", "icd", "implantable cardioverter defibrillator"],
        "infusion pump": ["iv pump", "syringe pump", "intravenous pump"],
        "insulin pump": ["diabetes pump", "csii pump"],
        "ventilator": ["respirator", "mechanical ventilator"],
@@ -86,51 +91,51 @@ class RegulatoryService:
        regions: list = None,
        start_date=None,
        end_date=None,
        limit: int = 100,
        mode: str = "fast",
        ai_service=None,
        manufacturer: Optional[str] = None,
        vendor_only: bool = False,
        include_sanctions: bool = True,
    ) -> tuple[pd.DataFrame, dict]:
        """
        Main entry point.
        mode: 'fast' (APIs + Snippets) or 'powerful' (Scrape + AI Verify)
        """
        results = []
        status_log = {}

        # Legacy positional safeguard (some callers passed dates as 2nd/3rd args)
        if regions is not None and not isinstance(regions, list) and isinstance(regions, (date, datetime)):
            if isinstance(start_date, (date, datetime)):
                end_date = start_date
            start_date = regions
            regions = None

        if regions is None:
            regions = ["US", "EU", "UK", "CA", "LATAM", "APAC"]

        manufacturer = (manufacturer or "").strip()
        query_term = (query_term or "").strip()
        if not query_term and not manufacturer:
            return pd.DataFrame(), {"Error": 0}

        expanded_terms = RegulatoryService._expand_terms(query_term)
        if not expanded_terms and manufacturer:
            expanded_terms = [manufacturer]

        # --- 1. OFFICIAL APIs (Fast & Structured) ---
        if not vendor_only:
            fda_enf = RegulatoryService._fetch_openfda_enforcement(expanded_terms, limit, start_date, end_date, manufacturer)
            results.extend(fda_enf)
            status_log["FDA Enforcement"] = len(fda_enf)

            fda_recalls = RegulatoryService._fetch_openfda_device_recalls(expanded_terms, limit, start_date, end_date, manufacturer)
            results.extend(fda_recalls)
            status_log["FDA Recalls"] = len(fda_recalls)

            maude_service = AdverseEventService()
            maude_hits = maude_service.search_events(query_term, start_date, end_date, limit=20)
            results.extend(maude_hits)
            status_log["FDA MAUDE"] = len(maude_hits)
