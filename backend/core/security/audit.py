import logging
import json
import time
from typing import Dict, Any, List, Optional, Set, Union
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
    Includes recursive array sanitization, depth limiting to prevent DoS, and dynamic sensitive key sets.
    """
    DEFAULT_SENSITIVE_KEYS: Set[str] = {
        "password", "passwd", "token", "secret", "api_key", "authorization",
        "credential", "credentials", "audio", "raw_audio", "frame", "camera_frame",
        "clipboard", "clipboard_content", "private_key", "pin", "pin_code",
        "credit_card", "cvv", "ssn", "auth", "bearer", "jwt", "session_token"
    }

    MAX_SANITIZATION_DEPTH: int = 5

    def __init__(
        self,
        logger_name: str = "nexa.security.audit",
        extra_sensitive_keys: Optional[Set[str]] = None
    ):
        self.logger = logging.getLogger(logger_name)
        self._history: List[AuditEvent] = []
        self.sensitive_keys: Set[str] = set(self.DEFAULT_SENSITIVE_KEYS)
        if extra_sensitive_keys:
            self.sensitive_keys.update({str(k).lower() for k in extra_sensitive_keys})

    def add_sensitive_keys(self, keys: Set[str]) -> None:
        """Dynamically add sensitive keys to redact."""
        self.sensitive_keys.update({str(k).lower() for k in keys})

    def sanitize_params(
        self,
        data: Any,
        current_depth: int = 0,
        max_depth: Optional[int] = None
    ) -> Any:
        """
        Recursively sanitizes parameter payloads across dictionaries and lists/arrays.
        Includes a depth limiter to prevent recursion stack overflow (DoS).
        """
        depth_limit = max_depth if max_depth is not None else self.MAX_SANITIZATION_DEPTH
        if current_depth > depth_limit:
            return "[TRUNCATED_MAX_DEPTH_EXCEEDED]"

        if not data:
            if isinstance(data, dict):
                return {}
            if isinstance(data, list):
                return []
            return data

        if isinstance(data, dict):
            sanitized_dict: Dict[str, Any] = {}
            for k, v in data.items():
                if isinstance(k, str) and k.lower() in self.sensitive_keys:
                    sanitized_dict[k] = "[REDACTED]"
                elif isinstance(v, dict):
                    sanitized_dict[k] = self.sanitize_params(v, current_depth + 1, depth_limit)
                elif isinstance(v, (list, tuple, set)):
                    sanitized_dict[k] = self.sanitize_params(list(v), current_depth + 1, depth_limit)
                else:
                    sanitized_dict[k] = v
            return sanitized_dict

        if isinstance(data, (list, tuple, set)):
            return [self.sanitize_params(item, current_depth + 1, depth_limit) for item in data]

        return data

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
        sanitized_details = self.sanitize_params(params) if params is not None else None
        event = AuditEvent(
            correlation_id=correlation_id,
            action=action,
            source=source,
            risk_level=risk_level,
            decision=decision,
            reason=reason,
            timestamp=timestamp if timestamp is not None else time.time(),
            details=sanitized_details if isinstance(sanitized_details, dict) else {"payload": sanitized_details}
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
