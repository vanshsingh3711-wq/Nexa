import time
from typing import Optional
from pydantic import ValidationError

from core.security.models import (
    RiskLevel,
    PolicyDecision,
    StructuredActionRequest,
    PolicyDecisionResult,
)
from core.security.registry import ActionRegistry, get_default_registry
from core.security.policy_config import PolicyConfig, PolicyLoader
from core.security.audit import AuditLogger, get_default_audit_logger

class PolicyChecker:
    """
    Centralized security boundary / decision engine for Nexa.
    Decides whether a structured action intent is ALLOW, CONFIRM_NEEDED, or DENY.
    
    Invariants:
    1. Authorization ONLY: Contains zero OS execution logic.
    2. Fail-Closed: Unknown actions, schema errors, and blocked actions are always DENIED.
    3. Source Invariance: AI, voice, gesture, and API intents are all subject to identical rules.
    4. Deterministic: Given the same request and policy, the decision is always identical.
    """
    def __init__(
        self,
        registry: Optional[ActionRegistry] = None,
        policy_config: Optional[PolicyConfig] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.registry = registry if registry is not None else get_default_registry()
        self.policy_config = policy_config if policy_config is not None else PolicyLoader.load_from_file()
        self.audit_logger = audit_logger if audit_logger is not None else get_default_audit_logger()

    def evaluate(self, request: StructuredActionRequest) -> PolicyDecisionResult:
        """
        Evaluates an untrusted action request against the Action Registry and Policy Configuration.
        Produces a deterministic authorization decision and logs an audit event.
        """
        now = time.time()

        # 1. Structural Request Validation
        if not isinstance(request, StructuredActionRequest):
            try:
                request = StructuredActionRequest.model_validate(request)
            except Exception as e:
                result = PolicyDecisionResult(
                    decision=PolicyDecision.DENY,
                    risk_level=RiskLevel.BLOCKED,
                    reason=f"Malformed request structure: {e}",
                    correlation_id=getattr(request, "correlation_id", None) or request.get("correlation_id", None) or None,
                    timestamp=now,
                )
                return result

        action_name = request.action
        correlation_id = request.correlation_id
        source = request.source
        params = request.params

        # 2. Check Action Registry
        action_def = self.registry.get(action_name)
        if action_def is None:
            reason = f"Action '{action_name}' is not registered in the Action Registry."
            self.audit_logger.record(
                correlation_id=correlation_id,
                action=action_name,
                source=source,
                risk_level=RiskLevel.BLOCKED,
                decision=PolicyDecision.DENY,
                reason=reason,
                params=params,
                timestamp=now,
            )
            return PolicyDecisionResult(
                decision=PolicyDecision.DENY,
                risk_level=RiskLevel.BLOCKED,
                reason=reason,
                correlation_id=correlation_id,
                timestamp=now,
            )

        # 3. Parameter Schema Validation
        if action_def.param_schema is not None:
            try:
                action_def.param_schema.model_validate(params)
            except ValidationError as e:
                reason = f"Parameter validation failed for action '{action_name}': {e.errors()}"
                self.audit_logger.record(
                    correlation_id=correlation_id,
                    action=action_name,
                    source=source,
                    risk_level=RiskLevel.BLOCKED,
                    decision=PolicyDecision.DENY,
                    reason=reason,
                    params=params,
                    timestamp=now,
                )
                return PolicyDecisionResult(
                    decision=PolicyDecision.DENY,
                    risk_level=RiskLevel.BLOCKED,
                    reason=reason,
                    correlation_id=correlation_id,
                    timestamp=now,
                )
            except Exception as e:
                reason = f"Invalid parameters for action '{action_name}': {e}"
                self.audit_logger.record(
                    correlation_id=correlation_id,
                    action=action_name,
                    source=source,
                    risk_level=RiskLevel.BLOCKED,
                    decision=PolicyDecision.DENY,
                    reason=reason,
                    params=params,
                    timestamp=now,
                )
                return PolicyDecisionResult(
                    decision=PolicyDecision.DENY,
                    risk_level=RiskLevel.BLOCKED,
                    reason=reason,
                    correlation_id=correlation_id,
                    timestamp=now,
                )

        # 4. Check Explicit Blocked Actions List
        if self.policy_config.is_blocked(action_name):
            reason = f"Action '{action_name}' is explicitly BLOCKED by security policy."
            self.audit_logger.record(
                correlation_id=correlation_id,
                action=action_name,
                source=source,
                risk_level=RiskLevel.BLOCKED,
                decision=PolicyDecision.DENY,
                reason=reason,
                params=params,
                timestamp=now,
            )
            return PolicyDecisionResult(
                decision=PolicyDecision.DENY,
                risk_level=RiskLevel.BLOCKED,
                reason=reason,
                correlation_id=correlation_id,
                timestamp=now,
            )

        # 5. Determine Risk Level
        risk_level = self.policy_config.get_action_risk(action_name, default=action_def.default_risk)

        # 6. Apply Policy Decision
        if risk_level == RiskLevel.BLOCKED:
            decision = PolicyDecision.DENY
            reason = f"Action '{action_name}' has BLOCKED risk level and cannot be executed."
        elif risk_level == RiskLevel.HIGH:
            decision = PolicyDecision.CONFIRM_NEEDED
            reason = f"Action '{action_name}' has HIGH risk and requires explicit user confirmation."
        elif risk_level == RiskLevel.MEDIUM:
            decision = PolicyDecision.ALLOW
            reason = f"Action '{action_name}' permitted under MEDIUM risk policy."
        elif risk_level == RiskLevel.LOW:
            decision = PolicyDecision.ALLOW
            reason = f"Action '{action_name}' permitted under LOW risk policy."
        else:
            # Defensive default for unrecognized risk levels
            decision = PolicyDecision.DENY
            reason = f"Action '{action_name}' has unknown risk level '{risk_level}' (failing closed)."

        # 7. Record Audit Event
        self.audit_logger.record(
            correlation_id=correlation_id,
            action=action_name,
            source=source,
            risk_level=risk_level,
            decision=decision,
            reason=reason,
            params=params,
            timestamp=now,
        )

        # 8. Return Decision Result
        return PolicyDecisionResult(
            decision=decision,
            risk_level=risk_level,
            reason=reason,
            correlation_id=correlation_id,
            timestamp=now,
        )
