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
    - FeedbackService responds: "Verbally confirm execution if successful"
    """
    def __init__(
        self,
        registry: Optional[ActionRegistry] = None,
        policy_checker: Optional[PolicyChecker] = None,
        feedback_service: Optional[FeedbackService] = None,
    ):
        self.registry = registry if registry is not None else get_default_registry()
        self.policy_checker = policy_checker if policy_checker is not None else PolicyChecker(registry=self.registry)
        self.feedback_service = feedback_service if feedback_service is not None else get_feedback_service()

    def dispatch(self, request: StructuredActionRequest) -> Tuple[PolicyDecisionResult, Any]:
        """
        Evaluates the request through the PolicyChecker security boundary.
        If ALLOW, executes the registered handler.
        If CONFIRM_NEEDED or DENY, rejects execution without invoking the handler.
        Verbal feedback is triggered ONLY upon verified successful handler execution.
        """
        # 1. Authorization Step (Policy Check)
        decision_result = self.policy_checker.evaluate(request)

        # 2. Guard Execution
        if decision_result.decision != PolicyDecision.ALLOW:
            return decision_result, None

        # 3. Handler Lookup & Execution
        action_def = self.registry.get(request.action)
        if action_def is None or action_def.handler is None:
            return decision_result, None

        try:
            if request.params:
                execution_output = action_def.handler(**request.params)
            else:
                execution_output = action_def.handler()

            # 4. Feedback Step (Executed ONLY after handler succeeds)
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

