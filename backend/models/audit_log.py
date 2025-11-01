from datetime import datetime
from typing import Dict, Any

class AuditLog:
    """Model for tracking file operations and system events"""
    
    def __init__(self, event_type: str, resource: str, user: str = "system"):
        self.event_type = event_type  # upload, delete, download, preview, analyze, sync
        self.resource = resource  # filename or resource name
        self.user = user
        self.timestamp = datetime.utcnow()
        self.details: Dict[str, Any] = {}
        self.ip_address: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        return {
            "event_type": self.event_type,
            "resource": self.resource,
            "user": self.user,
            "timestamp": self.timestamp,
            "details": self.details,
            "ip_address": self.ip_address
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AuditLog':
        """Create AuditLog from dictionary"""
        audit_log = cls(
            event_type=data["event_type"],
            resource=data["resource"],
            user=data.get("user", "system")
        )
        audit_log.timestamp = data.get("timestamp", datetime.utcnow())
        audit_log.details = data.get("details", {})
        audit_log.ip_address = data.get("ip_address")
        return audit_log