import time
import unittest
from unittest.mock import MagicMock

from core.security.models import (
    RiskLevel,
    PolicyDecision,
    StructuredActionRequest,
    EmptyParams,
)
from core.security.registry import ActionRegistry, ActionDefinition, create_default_registry
from core.security.policy_checker import PolicyChecker
from core.commands.action_router import ActionRouter
from core.commands.event_router import EventRouter
from core.feedback.coordinator import SpeechCoordinator
from core.feedback.speech import SpeechService
from core.feedback.feedback_service import FeedbackService
from core.feedback.messages import (
    LIFECYCLE_FEEDBACK,
    NEXA_ACTIVATED_MESSAGE,
    NEXA_CLOSING_MESSAGE,
    GESTURES_ENABLED_MESSAGE,
    GESTURES_DISABLED_MESSAGE,
    get_action_message,
)

class TestFeedbackSystem(unittest.TestCase):
    def setUp(self):
        self.coordinator = SpeechCoordinator(default_cooldown=0.1)
        self.mock_speech = MagicMock(spec=SpeechService)
        self.mock_speech.coordinator = self.coordinator
        self.feedback_service = FeedbackService(speech_service=self.mock_speech, repeat_debounce_sec=0.1)
        
        self.registry = create_default_registry()
        self.policy_checker = PolicyChecker(registry=self.registry)
        self.action_router = ActionRouter(
            registry=self.registry,
            policy_checker=self.policy_checker,
            feedback_service=self.feedback_service,
        )

    def test_message_mappings_and_silent_actions(self):
        """Verify that all normal desktop actions return None (silent)."""
        for action in ["move_mouse", "scroll", "left_click", "double_click", "media_play", "volume_up", "browser_back", "next_tab"]:
            self.assertIsNone(get_action_message(action), f"Action '{action}' must be silent")

    def test_normal_action_executes_silently(self):
        """Verify that an allowed normal action executes without speaking TTS."""
        mock_handler = MagicMock(return_value=True)
        self.registry.register(ActionDefinition(
            name="test_back",
            description="Test back action",
            param_schema=EmptyParams,
            default_risk=RiskLevel.LOW,
            handler=mock_handler,
        ))

        req = StructuredActionRequest(action="test_back", params={}, source="voice")
        decision, output = self.action_router.dispatch(req)

        self.assertEqual(decision.decision, PolicyDecision.ALLOW)
        mock_handler.assert_called_once()
        self.mock_speech.speak.assert_not_called()

    def test_denied_action_does_not_trigger_feedback(self):
        """Verify that a denied action does NOT execute handler and does NOT trigger speech."""
        req = StructuredActionRequest(action="unregistered_danger", params={}, source="voice")
        decision, output = self.action_router.dispatch(req)

        self.assertEqual(decision.decision, PolicyDecision.DENY)
        self.assertIsNone(output)
        self.mock_speech.speak.assert_not_called()

    def test_confirm_needed_action_prompts_confirmation(self):
        """Verify that high-risk action requiring confirmation does NOT execute handler and prompts for confirmation."""
        req = StructuredActionRequest(action="delete_file", params={"path": "test.txt"}, source="voice")
        decision, output = self.action_router.dispatch(req)

        self.assertEqual(decision.decision, PolicyDecision.CONFIRM_NEEDED)
        self.assertIsNone(output)
        self.mock_speech.speak.assert_called_once_with("Are you sure you want to execute delete_file? Say confirm or yes to proceed.")

    def test_action_handler_failure_does_not_claim_success(self):
        """Verify that an action handler throwing an exception does NOT speak success confirmation."""
        def broken_handler():
            raise RuntimeError("OS Driver Failure")

        self.registry.register(ActionDefinition(
            name="failing_action",
            description="Failing action",
            param_schema=EmptyParams,
            default_risk=RiskLevel.LOW,
            handler=broken_handler,
        ))

        req = StructuredActionRequest(action="failing_action", params={}, source="voice")
        decision, output = self.action_router.dispatch(req)

        self.assertIsNone(output)
        self.mock_speech.speak.assert_not_called()

    def test_speech_coordinator_prevents_voice_self_triggering(self):
        """Verify SpeechCoordinator tracks speaking state and cooldown to isolate microphone."""
        coord = SpeechCoordinator(default_cooldown=0.15)
        
        # 1. Idle state
        self.assertFalse(coord.is_speaking)
        self.assertFalse(coord.is_voice_blocked())

        # 2. Speaking active
        coord.mark_speaking_started()
        self.assertTrue(coord.is_speaking)
        self.assertTrue(coord.is_voice_blocked())

        # 3. Speech finished -> enters cooldown window
        coord.mark_speaking_finished(cooldown=0.15)
        self.assertFalse(coord.is_speaking)
        self.assertTrue(coord.is_voice_blocked(), "Voice should be blocked during cooldown")

        # 4. After cooldown expires
        time.sleep(0.2)
        self.assertFalse(coord.is_voice_blocked(), "Voice should unblock after cooldown expires")

    def test_tts_failure_does_not_fail_action_outcome(self):
        """Verify fail-safe isolation: TTS error does not crash or invalidate successful action execution."""
        mock_handler = MagicMock(return_value="SUCCESS_RESULT")
        self.registry.register(ActionDefinition(
            name="safe_action",
            description="Safe action",
            param_schema=EmptyParams,
            default_risk=RiskLevel.LOW,
            handler=mock_handler,
        ))

        # Mock speech service throwing an error during speak
        self.mock_speech.speak.side_effect = Exception("Audio device lost")

        req = StructuredActionRequest(action="safe_action", params={}, source="voice")
        decision, output = self.action_router.dispatch(req)

        self.assertEqual(decision.decision, PolicyDecision.ALLOW)
        self.assertEqual(output, "SUCCESS_RESULT")
        mock_handler.assert_called_once()

    def test_lifecycle_feedback_methods(self):
        """Verify direct feedback service lifecycle handlers."""
        self.feedback_service.handle_nexa_wake()
        self.mock_speech.speak.assert_called_with("Welcome, Vansh. How can I help you?")

        self.feedback_service.handle_nexa_close(block=True)
        self.mock_speech.speak.assert_called_with("Alright, closing Nexa.", block=True)


        self.feedback_service.handle_gestures_enabled()
        self.mock_speech.speak.assert_called_with("Gesture control enabled.")

        self.feedback_service.handle_gestures_disabled()
        self.mock_speech.speak.assert_called_with("Gesture control disabled.")

if __name__ == "__main__":
    unittest.main()
