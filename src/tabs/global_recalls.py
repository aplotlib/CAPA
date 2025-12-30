import streamlit as st
from src.ai_services import get_ai_service

def display_recalls_tab():
    st.header("🌍 Global Regulatory Intelligence & Recalls")
    st.caption("Screen your device against FDA, EUDAMED, MHRA, TGA, and Health Canada alerts.")

    ai = get_ai_service()
    if not ai:
        st.warning("⚠️ AI Service not initialized. Please check API Key in settings or sidebar.")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🛡️ Product Screening")
        
        # Use SKU/Name from global sidebar if available
        default_desc = ""
        if 'product_info' in st.session_state:
            p_name = st.session_state.product_info.get('name', '')
            p_sku = st.session_state.product_info.get('sku', '')
            if p_name or p_sku:
                default_desc = f"{p_name} {p_sku}"
            
        device_query = st.text_area(
            "Device Description for Analysis", 
            value=default_desc,
            placeholder="e.g., Class II Infusion Pump with wifi connectivity...",
            height=150
        )
        
        if st.button("Run Global Hazard Screen", type="primary", icon="🔍"):
            if not device_query.strip():
                st.error("Please enter a device description.")
            else:
                with st.spinner("Consulting Global Regulatory Databases (Simulated via AI)..."):
                    report = ai.screen_recalls(device_query)
                    st.session_state.recall_report = report

        if 'recall_report' in st.session_state:
            st.markdown("### 📋 Screening Report")
            st.markdown(st.session_state.recall_report)
            
            st.download_button(
                "Download Report",
                st.session_state.recall_report,
                file_name="regulatory_screen.md"
            )

    with col2:
        st.subheader("🔗 Official Verification Sources")
        st.info("The AI provides intelligence, but you must verify against official databases.")
        
        sources = [
            {
                "region": "🇺🇸 USA (FDA)", 
                "name": "Recalls, Market Withdrawals & Safety Alerts", 
                "url": "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts"
            },
            {
                "region": "🇪🇺 EU (EUDAMED)", 
                "name": "Vigilance & Post-Market Surveillance", 
                "url": "https://ec.europa.eu/tools/eudamed"
            },
            {
                "region": "🇬🇧 UK (MHRA)", 
                "name": "Drug and Device Alerts", 
                "url": "https://www.gov.uk/drug-device-alerts"
            },
            {
                "region": "🇦🇺 Australia (TGA)", 
                "name": "Database of Recalls (SARA/DRAC)", 
                "url": "https://apps.tga.gov.au/PROD/DRAC/arn-entry.aspx"
            },
            {
                "region": "🇨🇦 Canada (Health Canada)", 
                "name": "Recalls and Safety Alerts", 
                "url": "https://recalls-rappels.canada.ca/en"
            },
            {
                "region": "🇯🇵 Japan (PMDA)", 
                "name": "Medical Safety Information", 
                "url": "https://www.pmda.go.jp/english/safety/info-services/safety-information/0001.html"
            }
        ]
        
        for source in sources:
            with st.expander(f"{source['region']} - {source['name']}"):
                st.markdown(f"**Direct Link:** [{source['url']}]({source['url']})")
                st.caption(f"Search this database for: *{device_query if device_query else 'Your Device'}*")
