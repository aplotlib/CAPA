class AuditLogger:
    """A dummy logger that does nothing, as per user requirements."""
    def __init__(self):
        pass

    def log_action(self, user: str, action: str, entity: str, details: dict):
        pass # No-op

    def get_audit_log_csv(self) -> str:
        return ""
