from datetime import datetime
from typing import Dict, Any, Optional

class AuditLog:
    """Model for tracking file operations and system events."""

    def __init__(self, event_type: str, resource: str, user: str = "system"):
        self.event_type = event_type
        self.resource = resource
        self.user = user
        self.timestamp = datetime.utcnow()
        self.details: Dict[str, Any] = {}
        self.ip_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "resource": self.resource,
            "user": self.user,
            "timestamp": self.timestamp,
            "details": self.details,
            "ip_address": self.ip_address,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLog":
        audit_log = cls(
            event_type=data["event_type"],
            resource=data["resource"],
            user=data.get("user", "system")
        )
        audit_log.timestamp = data.get("timestamp", datetime.utcnow())
        audit_log.details = data.get("details", {})
        audit_log.ip_address = data.get("ip_address")
        return audit_log
