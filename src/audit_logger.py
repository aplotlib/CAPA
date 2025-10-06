# src/audit_logger.py

import pandas as pd
from datetime import datetime
import streamlit as st
from io import StringIO

class AuditLogger:
    """A class to log audit trail events and export them as a CSV."""

    def __init__(self):
        if 'audit_log' not in st.session_state:
            st.session_state.audit_log = []

    def log_action(self, user: str, action: str, entity: str, details: dict):
        """Logs an audit trail event."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'action': action,
            'entity': entity,
            'details': str(details),
        }
        st.session_state.audit_log.append(entry)

    def get_audit_log_csv(self) -> str:
        """Returns the audit log as a CSV string."""
        if not st.session_state.audit_log:
            return ""
        df = pd.DataFrame(st.session_state.audit_log)
        output = StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()
