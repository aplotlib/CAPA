# src/audit_logger.py

import streamlit as st
import pandas as pd
from datetime import datetime

class AuditLogger:
    """
    Logs user actions to the session state for audit trail compliance.
    """
    def __init__(self):
        if 'audit_log' not in st.session_state:
            st.session_state.audit_log = []

    def log_action(self, user: str, action: str, entity: str, details: dict):
        """
        Records an action with a timestamp.
        """
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user,
            "action": action,
            "entity": entity,
            "details": str(details)
        }
        if 'audit_log' in st.session_state:
            st.session_state.audit_log.append(entry)

    def get_audit_log_csv(self) -> str:
        """
        Returns the audit log as a CSV string.
        """
        if 'audit_log' not in st.session_state or not st.session_state.audit_log:
            return "timestamp,user,action,entity,details\n"
        
        df = pd.DataFrame(st.session_state.audit_log)
        return df.to_csv(index=False)
