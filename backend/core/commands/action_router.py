import time
from typing import Optional, Tuple, Any
from core.security.models import (
    PolicyDecision,
    StructuredActionRequest,
    PolicyDecisionResult,
)
from core.security.registry import ActionRegistry, get_default_registry
from core.security.policy_checker import PolicyChecker
from core.feedback.feedback_service import FeedbackService, get_feedback_service

class ActionRouter:
    """
    Executes desktop actions ONLY when authorized by the PolicyChecker.
    Maintains clear separation of concerns:
    - PolicyChecker authorizes: "Is this action permitted?"
    - ActionRouter executes: "How do I invoke the registered handler?"
    - FeedbackService responds: "Verbally confirm execution if successful / prompt for confirmation"
    """
    def __init__(
        self,
        registry: Optional[ActionRegistry] = None,
        policy_checker: Optional[PolicyChecker] = None,
        feedback_service: Optional[FeedbackService] = None,
        confirmation_timeout_sec: float = 15.0,
    ):
        self.registry = registry if registry is not None else get_default_registry()
        self.policy_checker = policy_checker if policy_checker is not None else PolicyChecker(registry=self.registry)
        self.feedback_service = feedback_service if feedback_service is not None else get_feedback_service()
        self.confirmation_timeout_sec = confirmation_timeout_sec
        
        self.pending_request: Optional[StructuredActionRequest] = None
        self.pending_request_time: float = 0.0

    def dispatch(self, request: StructuredActionRequest) -> Tuple[PolicyDecisionResult, Any]:
        """
        Evaluates the request through the PolicyChecker security boundary.
        If ALLOW, executes the registered handler.
        If CONFIRM_NEEDED, stores request and prompts user verbally for confirmation.
        If DENY, rejects execution without invoking the handler.
        """
        # 1. Authorization Step (Policy Check)
        decision_result = self.policy_checker.evaluate(request)

        # 2. Check Confirmation Needed
        if decision_result.decision == PolicyDecision.CONFIRM_NEEDED:
            print(f"\n[ActionRouter] CONFIRMATION REQUIRED for '{request.action}' (Risk: {decision_result.risk_level.value})")
            self.pending_request = request
            self.pending_request_time = time.time()
            
            if self.feedback_service is not None:
                try:
                    target = request.params.get("target") if request.params else None
                    self.feedback_service.handle_confirmation_needed(request.action, target=target)
                except Exception as fb_err:
                    print(f"[ActionRouter] Feedback confirmation error: {fb_err}")
            return decision_result, None

        # 3. Guard Execution if DENIED
        if decision_result.decision != PolicyDecision.ALLOW:
            return decision_result, None

        # 4. Handler Lookup & Execution
        return self._execute_request(request, decision_result)

    def _execute_request(self, request: StructuredActionRequest, decision_result: PolicyDecisionResult) -> Tuple[PolicyDecisionResult, Any]:
        action_def = self.registry.get(request.action)
        if action_def is None or action_def.handler is None:
            return decision_result, None

        try:
            if request.params:
                execution_output = action_def.handler(**request.params)
            else:
                execution_output = action_def.handler()

            # Feedback Step (Executed ONLY after handler succeeds)
            if self.feedback_service is not None:
                try:
                    self.feedback_service.handle_action_success(
                        action=request.action,
                        params=request.params,
                        source=request.source,
                    )
                except Exception as fb_err:
                    print(f"[ActionRouter] Feedback error ignored (action succeeded): {fb_err}")

            return decision_result, execution_output
        except Exception as e:
            print(f"[ActionRouter] Error executing handler for '{request.action}': {e}")
            return decision_result, None

    def confirm_pending(self) -> Optional[Any]:
        """
        Executes a pending action that was previously paused waiting for confirmation.
        """
        if not self.pending_request:
            print("[ActionRouter] No pending action to confirm.")
            return None

        # Check timeout
        if time.time() - self.pending_request_time > self.confirmation_timeout_sec:
            print("[ActionRouter] Pending confirmation timed out.")
            self.pending_request = None
            if self.feedback_service is not None:
                self.feedback_service.handle_confirmation_cancelled()
            return None

        req = self.pending_request
        self.pending_request = None
        print(f"[ActionRouter] Executing confirmed action: '{req.action}'")

        if self.feedback_service is not None:
            try:
                self.feedback_service.handle_confirmation_confirmed()
            except Exception:
                pass

        action_def = self.registry.get(req.action)
        if action_def and action_def.handler:
            try:
                if req.params:
                    return action_def.handler(**req.params)
                else:
                    return action_def.handler()
            except Exception as e:
                print(f"[ActionRouter] Error executing confirmed handler '{req.action}': {e}")
        return None

    def cancel_pending(self) -> bool:
        """
        Cancels a pending action that was waiting for confirmation.
        """
        if not self.pending_request:
            return False

        req = self.pending_request
        self.pending_request = None
        print(f"[ActionRouter] Cancelled pending action: '{req.action}'")

        if self.feedback_service is not None:
            try:
                self.feedback_service.handle_confirmation_cancelled()
            except Exception:
                pass
        return True
