import os
import json
import tempfile
from unittest.mock import MagicMock
from uuid import uuid4

from core.security.models import (
    RiskLevel,
    PolicyDecision,
    StructuredActionRequest,
    MouseMoveParams,
    EmptyParams,
    AppTargetParams,
    FileTargetParams,
)
from core.security.registry import (
    ActionRegistry,
    ActionDefinition,
    get_default_registry,
    create_default_registry,
)
from core.security.policy_config import (
    PolicyConfig,
    PolicyLoader,
    PolicyConfigurationError,
    ActionPolicyRule,
)
from core.security.audit import AuditLogger, AuditEvent
from core.security.policy_checker import PolicyChecker
from core.commands.action_router import ActionRouter

def test_allowed_low_risk_action():
    """1. Registered LOW-risk action with valid params evaluates to ALLOW."""
    checker = PolicyChecker()
    req = StructuredActionRequest(
        action="volume_up",
        params={},
        source="voice",
    )
    result = checker.evaluate(req)
    assert result.decision == PolicyDecision.ALLOW
    assert result.risk_level == RiskLevel.LOW
    print("[PASS] test_allowed_low_risk_action")

def test_unknown_action_denied():
    """2. Unknown / unregistered action evaluates to DENY."""
    checker = PolicyChecker()
    req = StructuredActionRequest(
        action="delete_everything_malicious",
        params={},
        source="ai",
    )
    result = checker.evaluate(req)
    assert result.decision == PolicyDecision.DENY
    assert "not registered" in result.reason
    print("[PASS] test_unknown_action_denied")

def test_invalid_parameters_denied():
    """3. Registered action with invalid / extra / malformed parameters evaluates to DENY."""
    checker = PolicyChecker()
    
    # Extra unexpected parameter on zero-argument action
    req1 = StructuredActionRequest(
        action="volume_up",
        params={"unexpected_flag": True},
        source="gesture",
    )
    res1 = checker.evaluate(req1)
    assert res1.decision == PolicyDecision.DENY
    assert "Parameter validation failed" in res1.reason

    # Out of bounds parameter on mouse_move
    req2 = StructuredActionRequest(
        action="move_mouse",
        params={"norm_x": 1.5, "norm_y": 0.5}, # norm_x > 1.0
        source="gesture",
    )
    res2 = checker.evaluate(req2)
    assert res2.decision == PolicyDecision.DENY
    assert "Parameter validation failed" in res2.reason

    # Missing required parameter on target action
    req3 = StructuredActionRequest(
        action="close_app",
        params={}, # missing 'target'
        source="voice",
    )
    res3 = checker.evaluate(req3)
    assert res3.decision == PolicyDecision.DENY
    assert "Parameter validation failed" in res3.reason
    print("[PASS] test_invalid_parameters_denied")

def test_high_risk_action_confirm_needed():
    """4. HIGH-risk action evaluates to CONFIRM_NEEDED and is never automatically executed."""
    checker = PolicyChecker()
    req = StructuredActionRequest(
        action="delete_file",
        params={"path": "C:/important/file.txt"},
        source="ai",
    )
    result = checker.evaluate(req)
    assert result.decision == PolicyDecision.CONFIRM_NEEDED
    assert result.risk_level == RiskLevel.HIGH
    assert "requires explicit user confirmation" in result.reason
    print("[PASS] test_high_risk_action_confirm_needed")

def test_blocked_action_denied():
    """5. Action on explicit blocked actions list evaluates to DENY."""
    checker = PolicyChecker()
    
    # Register a dangerous action to prove that even if registered, blocked policy overrides
    mock_registry = create_default_registry()
    mock_registry.register(ActionDefinition(
        name="execute_shell",
        description="Shell execution",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW, # Attempting to claim it is low risk
    ))
    custom_checker = PolicyChecker(registry=mock_registry)
    
    req = StructuredActionRequest(
        action="execute_shell",
        params={},
        source="ai",
    )
    result = custom_checker.evaluate(req)
    assert result.decision == PolicyDecision.DENY
    assert result.risk_level == RiskLevel.BLOCKED
    assert "explicitly BLOCKED" in result.reason
    print("[PASS] test_blocked_action_denied")

def test_confirmation_cannot_override_blocked():
    """6. Confirmation must NEVER override a BLOCKED action."""
    checker = PolicyChecker()
    mock_registry = create_default_registry()
    mock_registry.register(ActionDefinition(
        name="format_drive",
        description="Format hard drive",
        param_schema=EmptyParams,
        default_risk=RiskLevel.BLOCKED,
    ))
    custom_checker = PolicyChecker(registry=mock_registry)

    req = StructuredActionRequest(
        action="format_drive",
        params={"user_confirmed": True}, # User claiming confirmation in params
        source="ui",
    )
    result = custom_checker.evaluate(req)
    assert result.decision == PolicyDecision.DENY
    assert result.risk_level == RiskLevel.BLOCKED
    print("[PASS] test_confirmation_cannot_override_blocked")

def test_source_invariance_ai_and_others():
    """7 & 8. No source (AI, Voice, Gesture, API, UI) receives special bypass privileges."""
    checker = PolicyChecker()
    sources = ["ai", "voice", "gesture", "api", "ui", "task_planner", "external"]

    for src in sources:
        # HIGH-risk action must always return CONFIRM_NEEDED regardless of source
        high_req = StructuredActionRequest(
            action="delete_file",
            params={"path": "test.txt"},
            source=src,
        )
        high_res = checker.evaluate(high_req)
        assert high_res.decision == PolicyDecision.CONFIRM_NEEDED, f"Source '{src}' bypassed HIGH risk check!"

        # BLOCKED action must always return DENY regardless of source
        blocked_req = StructuredActionRequest(
            action="run_powershell",
            params={},
            source=src,
        )
        blocked_res = checker.evaluate(blocked_req)
        assert blocked_res.decision == PolicyDecision.DENY, f"Source '{src}' bypassed BLOCKED check!"
    print("[PASS] test_source_invariance_ai_and_others")

def test_malformed_policy_fails_closed():
    """9. Malformed policy configuration fails closed during initialization."""
    # 1. Invalid JSON
    failed = False
    try:
        PolicyLoader.load_from_json_string("INVALID_JSON_CONTENT {{{")
    except PolicyConfigurationError as e:
        failed = True
        assert "Invalid JSON" in str(e)
    assert failed, "Expected PolicyConfigurationError on invalid JSON"

    # 2. Malformed schema (missing version or invalid risk level)
    failed = False
    try:
        PolicyLoader.load_from_dict({"name": "Test", "actions": {"vol": {"risk": "SUPER_SAFE_NOT_REAL"}}})
    except PolicyConfigurationError as e:
        failed = True
        assert "Malformed policy configuration" in str(e)
    assert failed, "Expected PolicyConfigurationError on malformed schema"

    # 3. Non-existent file path
    failed = False
    try:
        PolicyLoader.load_from_file("/non/existent/policy.json")
    except PolicyConfigurationError as e:
        failed = True
        assert "not found" in str(e)
    assert failed, "Expected PolicyConfigurationError on missing policy file"
    print("[PASS] test_malformed_policy_fails_closed")

def test_no_execution_by_policy_checker():
    """10. PolicyChecker NEVER invokes OS action handlers."""
    mock_handler = MagicMock()
    mock_registry = ActionRegistry()
    mock_registry.register(ActionDefinition(
        name="test_action",
        description="Test Action",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=mock_handler,
    ))
    checker = PolicyChecker(registry=mock_registry)
    req = StructuredActionRequest(action="test_action", params={}, source="gesture")
    
    decision = checker.evaluate(req)
    assert decision.decision == PolicyDecision.ALLOW
    # The handler must NOT have been called!
    assert mock_handler.call_count == 0
    print("[PASS] test_no_execution_by_policy_checker")

def test_action_router_execution_gate():
    """11. ActionRouter only executes handlers when PolicyChecker returns ALLOW."""
    mock_handler = MagicMock(return_value="executed_successfully")
    mock_registry = ActionRegistry()
    mock_registry.register(ActionDefinition(
        name="safe_action",
        description="Safe Action",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=mock_handler,
    ))
    mock_registry.register(ActionDefinition(
        name="dangerous_action",
        description="Dangerous Action",
        param_schema=EmptyParams,
        default_risk=RiskLevel.HIGH,
        handler=mock_handler,
    ))
    
    checker = PolicyChecker(registry=mock_registry)
    router = ActionRouter(registry=mock_registry, policy_checker=checker)

    # 1. ALLOW -> Executes handler
    req_allow = StructuredActionRequest(action="safe_action", params={}, source="voice")
    decision, out = router.dispatch(req_allow)
    assert decision.decision == PolicyDecision.ALLOW
    assert out == "executed_successfully"
    assert mock_handler.call_count == 1

    # 2. HIGH RISK (CONFIRM_NEEDED) -> Handler NOT called
    mock_handler.reset_mock()
    req_high = StructuredActionRequest(action="dangerous_action", params={}, source="ai")
    decision, out = router.dispatch(req_high)
    assert decision.decision == PolicyDecision.CONFIRM_NEEDED
    assert out is None
    assert mock_handler.call_count == 0

    # 3. UNKNOWN / DENIED -> Handler NOT called
    mock_handler.reset_mock()
    req_unknown = StructuredActionRequest(action="unknown_action", params={}, source="api")
    decision, out = router.dispatch(req_unknown)
    assert decision.decision == PolicyDecision.DENY
    assert out is None
    assert mock_handler.call_count == 0
    print("[PASS] test_action_router_execution_gate")

def test_audit_logging():
    """12. Structured audit logs are recorded with sanitized parameters."""
    audit_logger = AuditLogger()
    mock_registry = create_default_registry()
    checker = PolicyChecker(registry=mock_registry, audit_logger=audit_logger)

    cid = uuid4()
    req = StructuredActionRequest(
        action="volume_up",
        params={},
        source="gesture",
        correlation_id=cid,
    )
    checker.evaluate(req)

    events = audit_logger.get_events()
    assert len(events) == 1
    event = events[0]
    assert event.correlation_id == cid
    assert event.action == "volume_up"
    assert event.source == "gesture"
    assert event.decision == PolicyDecision.ALLOW
    print("[PASS] test_audit_logging")

def run_all():
    test_allowed_low_risk_action()
    test_unknown_action_denied()
    test_invalid_parameters_denied()
    test_high_risk_action_confirm_needed()
    test_blocked_action_denied()
    test_confirmation_cannot_override_blocked()
    test_source_invariance_ai_and_others()
    test_malformed_policy_fails_closed()
    test_no_execution_by_policy_checker()
    test_action_router_execution_gate()
    test_audit_logging()
    print("\nALL POLICY CHECKER & DECISION ENGINE TESTS PASSED!")

if __name__ == "__main__":
    run_all()
