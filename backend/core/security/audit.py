import logging
import json
import time
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from core.security.models import RiskLevel, PolicyDecision

class AuditEvent(BaseModel):
    """
    Structured security audit event recording every authorization decision.
    """
    correlation_id: UUID
    action: str
    source: str
    risk_level: RiskLevel
    decision: PolicyDecision
    reason: str
    timestamp: float = Field(default_factory=time.time)
    details: Optional[Dict[str, Any]] = None

class AuditLogger:
    """
    Structured, sanitized security audit logger.
    Emits structured security events and maintains an event history for security verification.
    """
    # Sensitive keys that must NEVER be recorded in audit logs
    SENSITIVE_KEYS = {
        "password", "passwd", "token", "secret", "api_key", "authorization",
        "credential", "credentials", "audio", "raw_audio", "frame", "camera_frame",
        "clipboard", "clipboard_content", "private_key"
    }

    def __init__(self, logger_name: str = "nexa.security.audit"):
        self.logger = logging.getLogger(logger_name)
        self._history: List[AuditEvent] = []

    def sanitize_params(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Removes or masks any sensitive parameter keys."""
        if not params:
            return {}
        sanitized = {}
        for k, v in params.items():
            if k.lower() in self.SENSITIVE_KEYS:
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, dict):
                sanitized[k] = self.sanitize_params(v)
            else:
                sanitized[k] = v
        return sanitized

    def record(
        self,
        correlation_id: UUID,
        action: str,
        source: str,
        risk_level: RiskLevel,
        decision: PolicyDecision,
        reason: str,
        params: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None
    ) -> AuditEvent:
        event = AuditEvent(
            correlation_id=correlation_id,
            action=action,
            source=source,
            risk_level=risk_level,
            decision=decision,
            reason=reason,
            timestamp=timestamp if timestamp is not None else time.time(),
            details=self.sanitize_params(params) if params else None
        )
        self._history.append(event)

        # Emit structured log output
        log_payload = {
            "audit_type": "security_policy_decision",
            "correlation_id": str(event.correlation_id),
            "action": event.action,
            "source": event.source,
            "risk_level": event.risk_level.value,
            "decision": event.decision.value,
            "reason": event.reason,
            "timestamp": event.timestamp,
        }

        if event.decision == PolicyDecision.ALLOW:
            self.logger.info(json.dumps(log_payload))
        elif event.decision == PolicyDecision.CONFIRM_NEEDED:
            self.logger.warning(json.dumps(log_payload))
        else:
            self.logger.warning(json.dumps(log_payload))

        return event

    def get_events(self) -> List[AuditEvent]:
        """Returns recorded audit history."""
        return list(self._history)

    def clear(self) -> None:
        """Clears audit history buffer."""
        self._history.clear()

_default_audit_logger: Optional[AuditLogger] = None

def get_default_audit_logger() -> AuditLogger:
    global _default_audit_logger
    if _default_audit_logger is None:
        _default_audit_logger = AuditLogger()
    return _default_audit_logger
