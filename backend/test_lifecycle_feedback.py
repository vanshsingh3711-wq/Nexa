
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from core.commands.event_router import EventRouter
from core.commands.action_router import ActionRouter
from core.feedback.feedback_service import FeedbackService
from core.feedback.speech import SpeechService
from core.feedback.coordinator import SpeechCoordinator
from input.gesture.gesture_manager import GestureManager
from input.voice.voice_listener import VoiceListener

class TestSelectiveLifecycleFeedback(unittest.TestCase):
    def setUp(self):
        self.mock_speech_service = MagicMock(spec=SpeechService)
        self.feedback_service = FeedbackService(speech_service=self.mock_speech_service)
        self.event_router = EventRouter(feedback_service=self.feedback_service, start_active=False)

    def test_1_wake_nexa_speaks_welcome(self):
        """Test 1: Wake command activates Nexa and speaks 'Welcome, Vansh. How can I help you?' every time."""
        res1 = self.event_router.wake_nexa(speak=True)
        self.assertTrue(res1)
        self.assertTrue(self.event_router.is_nexa_active)
        self.mock_speech_service.speak.assert_called_with("Welcome, Vansh. How can I help you?")

        # Calling wake again confirms verbally every time
        res2 = self.event_router.wake_nexa(speak=True)
        self.assertTrue(res2)
        self.assertEqual(self.mock_speech_service.speak.call_count, 2)

    def test_2_normal_actions_remain_silent(self):
        """Test 2: Normal desktop actions (e.g. pause, volume up) execute silently without calling TTS."""
        self.event_router.is_nexa_active = True
        
        # Test Action 1: media_pause
        decision, output = self.event_router.execute_action("media_pause", source="voice")
        self.assertEqual(decision.decision.value, "ALLOW")
        self.mock_speech_service.speak.assert_not_called()

        # Test Action 2: volume_up
        decision2, output2 = self.event_router.execute_action("volume_up", source="voice")
        self.assertEqual(decision2.decision.value, "ALLOW")
        self.mock_speech_service.speak.assert_not_called()

        # Test Action 3: next_tab
        decision3, output3 = self.event_router.execute_action("next_tab", source="voice")
        self.assertEqual(decision3.decision.value, "ALLOW")
        self.mock_speech_service.speak.assert_not_called()

    def test_3_gesture_enable_success_speaks_confirmation(self):
        """Test 3: Successful gesture subsystem start speaks 'Gesture control enabled.'."""
        mock_camera = MagicMock()
        mock_camera.get_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_detector = MagicMock()
        mock_detector.process_frame.return_value = []

        manager = GestureManager(
            camera_factory=lambda **kw: mock_camera,
            detector_factory=lambda **kw: mock_detector,
            event_router=self.event_router,
            feedback_service=self.feedback_service
        )

        success = manager.start(speak_feedback=True)
        self.assertTrue(success)
        self.assertTrue(manager.is_active)
        self.mock_speech_service.speak.assert_called_once_with("Gesture control enabled.")
        manager.stop(speak_feedback=False)

    def test_4_gesture_enable_failure_remains_silent(self):
        """Test 4: Failed gesture startup rolls back, remains inactive, and does NOT claim success or speak."""
        failing_camera_factory = MagicMock(side_effect=RuntimeError("Webcam hardware in use"))
        manager = GestureManager(
            camera_factory=failing_camera_factory,
            event_router=self.event_router,
            feedback_service=self.feedback_service
        )

        success = manager.start(speak_feedback=True)
        self.assertFalse(success)
        self.assertFalse(manager.is_active)
        self.mock_speech_service.speak.assert_not_called()

    def test_5_gesture_disable_success_speaks_confirmation(self):
        """Test 5: Successful gesture shutdown releases hardware and speaks 'Gesture control disabled.'."""
        mock_camera = MagicMock()
        mock_camera.get_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_detector = MagicMock()
        mock_detector.process_frame.return_value = []

        manager = GestureManager(
            camera_factory=lambda **kw: mock_camera,
            detector_factory=lambda **kw: mock_detector,
            event_router=self.event_router,
            feedback_service=self.feedback_service
        )

        manager.start(speak_feedback=False)
        self.assertTrue(manager.is_active)

        success = manager.stop(speak_feedback=True)
        self.assertTrue(success)
        self.assertFalse(manager.is_active)
        self.mock_speech_service.speak.assert_called_once_with("Gesture control disabled.")

    def test_6_close_nexa_speaks_closing_and_cleans_up(self):
        """Test 6: Close command speaks 'Alright, closing Nexa.', puts Nexa to sleep, and cleans up."""
        self.event_router.is_nexa_active = True
        cleanup_mock = MagicMock()

        success = self.event_router.close_nexa(cleanup_fn=cleanup_mock, speak=True)
        self.assertTrue(success)
        self.assertFalse(self.event_router.is_nexa_active)
        self.mock_speech_service.speak.assert_called_once_with("Alright, closing Nexa.", block=False)
        cleanup_mock.assert_called_once()

    def test_7_consecutive_close_calls(self):
        """Test 7: Consecutive Close Nexa calls both confirm closing feedback."""
        self.event_router.is_nexa_active = True
        cleanup_mock = MagicMock()

        res1 = self.event_router.close_nexa(cleanup_fn=cleanup_mock, speak=True)
        res2 = self.event_router.close_nexa(cleanup_fn=cleanup_mock, speak=True)

        self.assertTrue(res1)
        self.assertTrue(res2)
        self.assertEqual(self.mock_speech_service.speak.call_count, 2)

    def test_8_self_listening_prevention(self):
        """Test 8: SpeechCoordinator blocks voice recognition during TTS and unblocks afterwards."""
        coordinator = SpeechCoordinator(default_cooldown=0.1)
        self.assertFalse(coordinator.is_voice_blocked())

        # When speech starts, recognition is blocked
        coordinator.mark_speaking_started()
        self.assertTrue(coordinator.is_speaking)
        self.assertTrue(coordinator.is_voice_blocked())

        # When speech finishes, cooldown window applies
        coordinator.mark_speaking_finished(cooldown=0.05)
        self.assertFalse(coordinator.is_speaking)
        self.assertTrue(coordinator.is_voice_blocked(), "Voice should be blocked during cooldown")

        # After cooldown passes, voice is unblocked
        import time
        time.sleep(0.06)
        self.assertFalse(coordinator.is_voice_blocked())

    def test_9_wake_sleep_rewake_cycle(self):
        """Test 9: Full lifecycle cycle: Wake -> Sleep -> Re-Wake replies every time."""
        # 1. Wake
        self.event_router.wake_nexa(speak=True)
        self.assertTrue(self.event_router.is_nexa_active)

        # 2. Sleep / Close
        self.event_router.close_nexa(speak=True)
        self.assertFalse(self.event_router.is_nexa_active)

        # 3. Re-Wake
        self.event_router.wake_nexa(speak=True)
        self.assertTrue(self.event_router.is_nexa_active)

        # 4. Re-Close
        self.event_router.close_nexa(speak=True)
        self.assertFalse(self.event_router.is_nexa_active)

        self.assertEqual(self.mock_speech_service.speak.call_count, 4)

if __name__ == "__main__":
    unittest.main()
