import time
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from input.gesture.gesture_manager import GestureManager
from core.commands.event_router import EventRouter
from core.feedback.feedback_service import FeedbackService

class TestGestureLifecycle(unittest.TestCase):
    def setUp(self):
        self.mock_camera = MagicMock()
        self.mock_camera.get_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        self.mock_camera_factory = MagicMock(return_value=self.mock_camera)

        self.mock_detector = MagicMock()
        self.mock_detector.process_frame.return_value = []
        self.mock_detector_factory = MagicMock(return_value=self.mock_detector)

        self.mock_feedback = MagicMock(spec=FeedbackService)
        self.event_router = EventRouter()

        self.manager = GestureManager(
            camera_factory=self.mock_camera_factory,
            detector_factory=self.mock_detector_factory,
            event_router=self.event_router,
            feedback_service=self.mock_feedback
        )

    def tearDown(self):
        self.manager.stop(speak_feedback=False)

    def test_1_startup_does_not_initialize_camera(self):
        """Test 1: Application/Manager initialization does NOT initialize camera or MediaPipe."""
        self.assertFalse(self.manager.is_active)
        self.assertIsNone(self.manager.camera)
        self.assertIsNone(self.manager.detector)
        self.mock_camera_factory.assert_not_called()
        self.mock_detector_factory.assert_not_called()

    def test_2_enable_gestures_initializes_camera_and_worker(self):
        """Test 2: Starting gestures initializes camera, detector, and sets state to ACTIVE."""
        success = self.manager.start(speak_feedback=True)
        
        self.assertTrue(success)
        self.assertTrue(self.manager.is_active)
        self.assertIsNotNone(self.manager.camera)
        self.assertIsNotNone(self.manager.detector)
        self.mock_camera_factory.assert_called_once()
        self.mock_detector_factory.assert_called_once()
        self.mock_feedback.handle_gesture_lifecycle.assert_called_once_with(True)

    def test_3_disable_gestures_releases_resources(self):
        """Test 3: Stopping gestures releases camera hardware, closes detector, and sets state to INACTIVE."""
        self.manager.start(speak_feedback=False)
        self.assertTrue(self.manager.is_active)

        success = self.manager.stop(speak_feedback=True)

        self.assertTrue(success)
        self.assertFalse(self.manager.is_active)
        self.assertIsNone(self.manager.camera)
        self.assertIsNone(self.manager.detector)
        self.mock_camera.release.assert_called_once()
        self.mock_detector.release.assert_called_once()
        self.mock_feedback.handle_gesture_lifecycle.assert_called_with(False)

    def test_4_double_start_is_idempotent(self):
        """Test 4: Consecutive start() calls are idempotent and do NOT create duplicate resources."""
        res1 = self.manager.start(speak_feedback=False)
        res2 = self.manager.start(speak_feedback=False)

        self.assertTrue(res1)
        self.assertTrue(res2)
        self.assertTrue(self.manager.is_active)
        # Should only call factories once
        self.assertEqual(self.mock_camera_factory.call_count, 1)
        self.assertEqual(self.mock_detector_factory.call_count, 1)

    def test_5_double_stop_is_idempotent(self):
        """Test 5: Consecutive stop() calls are safe, idempotent, and do not crash."""
        self.manager.start(speak_feedback=False)
        res1 = self.manager.stop(speak_feedback=False)
        res2 = self.manager.stop(speak_feedback=False)

        self.assertTrue(res1)
        self.assertTrue(res2)
        self.assertFalse(self.manager.is_active)
        self.assertEqual(self.mock_camera.release.call_count, 1)

    def test_6_camera_startup_failure_handling(self):
        """Test 6: Camera hardware initialization failure cleanly rolls back resources and remains INACTIVE."""
        failing_camera_factory = MagicMock(side_effect=RuntimeError("Camera device busy in another app"))
        manager = GestureManager(
            camera_factory=failing_camera_factory,
            detector_factory=self.mock_detector_factory,
            event_router=self.event_router,
            feedback_service=self.mock_feedback
        )

        success = manager.start(speak_feedback=True)

        self.assertFalse(success)
        self.assertFalse(manager.is_active)
        self.assertIsNone(manager.camera)
        self.assertIsNone(manager.detector)
        # Should not claim gestures are enabled on failure
        self.mock_feedback.handle_gesture_lifecycle.assert_not_called()

    def test_7_stop_start_restart_cycle(self):
        """Test 7: Subsystem cleanly supports stopping and restarting multiple times."""
        # Cycle 1: Start -> Stop
        self.manager.start(speak_feedback=False)
        self.assertTrue(self.manager.is_active)
        self.manager.stop(speak_feedback=False)
        self.assertFalse(self.manager.is_active)

        # Cycle 2: Start -> Stop
        self.manager.start(speak_feedback=False)
        self.assertTrue(self.manager.is_active)
        self.manager.stop(speak_feedback=False)
        self.assertFalse(self.manager.is_active)

        self.assertEqual(self.mock_camera_factory.call_count, 2)
        self.assertEqual(self.mock_camera.release.call_count, 2)

    def test_8_no_actions_after_shutdown(self):
        """Test 8: After shutdown, event router is inactive and no stale gestures are processed."""
        self.manager.start(speak_feedback=False)
        self.assertTrue(self.event_router.is_active)

        self.manager.stop(speak_feedback=False)
        self.assertFalse(self.event_router.is_active)

        # Dispatching gesture while inactive must not trigger any action
        mock_action_router = MagicMock()
        self.event_router.action_router = mock_action_router
        self.event_router.dispatch({"gesture": "Index", "cursor_x": 0.5, "cursor_y": 0.5}, {"gesture": "None"})
        
        mock_action_router.dispatch.assert_not_called()

if __name__ == "__main__":
    unittest.main()
