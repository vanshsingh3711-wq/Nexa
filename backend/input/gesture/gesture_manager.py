import threading
import time
from typing import Optional, Callable, Dict, Any

from input.gesture.camera import Camera
from input.gesture.landmark_detector import HandLandmarkDetector
from input.gesture.classifier import GestureClassifier
from input.gesture.stability_filter import GestureStabilityFilter
from core.feedback.feedback_service import FeedbackService, get_feedback_service

class GestureManager:

    """
    Manages the complete on-demand lifecycle of the camera and gesture recognition pipeline.
    
    Responsibilities:
    - Lazy Initialization: Camera and MediaPipe are NOT initialized at application startup.
    - On-Demand Start: Opens camera hardware and starts gesture thread only when explicitly enabled.
    - Clean Shutdown: Completely releases cv2.VideoCapture, joins threads, and frees RAM/CPU when disabled.
    - Idempotency & Thread-Safety: Safe against duplicate starts, duplicate stops, and concurrent calls.
    - Fail-Safe Cleanup: Rolls back partial initializations if camera hardware is busy or fails.
    """
    def __init__(
        self,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        model_asset_path: str = 'input/gesture/hand_landmarker.task',
        event_router: Optional[Any] = None,

        feedback_service: Optional[FeedbackService] = None,
        on_frame_callback: Optional[Callable[[Any, Dict[str, Any], Any], None]] = None,
        camera_factory: Optional[Callable[..., Camera]] = None,
        detector_factory: Optional[Callable[..., HandLandmarkDetector]] = None,
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.model_asset_path = model_asset_path
        
        # Dependency injection / factories (enables mocking in unit tests)
        self._camera_factory = camera_factory if camera_factory is not None else Camera
        self._detector_factory = detector_factory if detector_factory is not None else HandLandmarkDetector
        
        if event_router is not None:
            self.router = event_router
        else:
            from core.commands.event_router import EventRouter
            self.router = EventRouter()
            
        self.feedback_service = feedback_service if feedback_service is not None else get_feedback_service()

        self.on_frame_callback = on_frame_callback
        
        # Processing components (lightweight, reusable)
        self.classifier = GestureClassifier()
        self.stability = GestureStabilityFilter(history_size=7, confidence_threshold=0.6, base_alpha=0.7)
        
        # Dynamic hardware resources (created only on demand)
        self.camera: Optional[Camera] = None
        self.detector: Optional[HandLandmarkDetector] = None
        
        # Lifecycle state
        self._is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lifecycle_lock = threading.Lock()
        
        # State tracking for UI / API inspection
        self.current_gesture_data: Dict[str, Any] = {
            "gesture": "None",
            "cursor_x": 0.0,
            "cursor_y": 0.0,
            "pinch_dist": 1.0,
            "norm_pinch_dist": 1.0
        }

    @property
    def is_active(self) -> bool:
        """Returns True if the gesture subsystem and camera are currently operational."""
        with self._lifecycle_lock:
            return self._is_running and (self.camera is not None)

    def start(self, speak_feedback: bool = True) -> bool:
        """
        Starts the camera and gesture recognition pipeline on demand.
        Returns True if the subsystem is fully operational, False otherwise.
        """
        with self._lifecycle_lock:
            if self._is_running and self.camera is not None:
                # Idempotent: already running
                return True

            print("[GestureManager] Starting gesture subsystem on demand...")
            
            # 1. Initialize Camera hardware
            try:
                self.camera = self._camera_factory(
                    camera_index=self.camera_index,
                    width=self.width,
                    height=self.height
                )
            except Exception as e:
                print(f"[GestureManager] Failed to start camera: {e}")
                self._cleanup_resources_locked()
                return False

            # 2. Initialize MediaPipe Detector
            try:
                self.detector = self._detector_factory(
                    model_asset_path=self.model_asset_path
                )
            except Exception as e:
                print(f"[GestureManager] Failed to initialize MediaPipe detector: {e}")
                self._cleanup_resources_locked()
                return False

            # 3. Reset filters and activate router
            self.stability.reset()
            self.router.set_active(True, speak=False)
            self._is_running = True

            # 4. Start background gesture worker thread
            self._worker_thread = threading.Thread(
                target=self._gesture_worker_loop,
                name="Nexa-GesturePipeline-Worker",
                daemon=True
            )
            self._worker_thread.start()
            print("[GestureManager] Gesture subsystem started successfully (Camera ACTIVE).")

        # 5. Verbal feedback (outside lock)
        if speak_feedback and self.feedback_service:
            try:
                self.feedback_service.handle_gesture_lifecycle(True)
            except Exception as e:
                print(f"[GestureManager] Feedback error on start: {e}")

        return True

    def stop(self, speak_feedback: bool = True) -> bool:
        """
        Stops the gesture recognition pipeline and completely releases camera hardware resources.
        Returns True when shutdown completes.
        """
        worker_to_join = None
        with self._lifecycle_lock:
            if not self._is_running and self.camera is None:
                # Idempotent: already stopped
                return True

            print("[GestureManager] Stopping gesture subsystem & releasing camera...")
            self._is_running = False
            self.router.set_active(False, speak=False)
            self.stability.reset()
            
            worker_to_join = self._worker_thread
            self._worker_thread = None

        # 1. Join worker thread outside lock to prevent deadlocks
        if worker_to_join and worker_to_join.is_alive() and threading.current_thread() != worker_to_join:
            worker_to_join.join(timeout=1.5)

        with self._lifecycle_lock:
            # 2. Fully release hardware and resources
            self._cleanup_resources_locked()
            self._reset_state_locked()
            print("[GestureManager] Gesture subsystem stopped and camera resource RELEASED.")

        # 3. Verbal feedback (outside lock)
        if speak_feedback and self.feedback_service:
            try:
                self.feedback_service.handle_gesture_lifecycle(False)
            except Exception as e:
                print(f"[GestureManager] Feedback error on stop: {e}")

        return True

    def _cleanup_resources_locked(self) -> None:
        """Releases camera and detector resources while holding _lifecycle_lock."""
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception as e:
                print(f"[GestureManager] Error releasing camera: {e}")
            self.camera = None

        if self.detector is not None:
            try:
                self.detector.release()
            except Exception as e:
                print(f"[GestureManager] Error releasing detector: {e}")
            self.detector = None

    def _reset_state_locked(self) -> None:
        """Resets tracked gesture values to default idle state."""
        self.current_gesture_data = {
            "gesture": "None",
            "cursor_x": 0.0,
            "cursor_y": 0.0,
            "pinch_dist": 1.0,
            "norm_pinch_dist": 1.0
        }

    def _gesture_worker_loop(self) -> None:
        """
        Main gesture processing worker thread loop.
        Runs continuously while _is_running is True.
        """
        import cv2

        previous_gesture_data = {
            "gesture": "None",
            "cursor_x": 0.0,
            "cursor_y": 0.0,
            "pinch_dist": 1.0,
            "norm_pinch_dist": 1.0
        }
        consecutive_errors = 0

        while True:
            # Check exit condition
            with self._lifecycle_lock:
                if not self._is_running or self.camera is None or self.detector is None:
                    break
                cam = self.camera
                det = self.detector

            try:
                # 1. Fetch latest frame (Zero-Copy)
                frame = cam.get_frame(copy=False)
                frame = cv2.flip(frame, 1)
                consecutive_errors = 0

                # 2. Hand landmark detection
                landmarks = det.process_frame(frame)

                # 3. Classify raw gesture
                raw_gesture_data = {
                    "gesture": "None",
                    "cursor_x": 0.0,
                    "cursor_y": 0.0,
                    "pinch_dist": 1.0,
                    "norm_pinch_dist": 1.0
                }
                if landmarks and len(landmarks) > 0:
                    raw_gesture_data = self.classifier.classify(landmarks[0])

                # 4. Smooth coordinates and filter stability
                current_data = self.stability.get_stable_gesture(raw_gesture_data)
                
                # Check exit condition again before mutating state or routing
                if not self._is_running:
                    break

                self.current_gesture_data = current_data

                # 5. Dispatch event to router
                self.router.dispatch(current_data, previous_gesture_data)
                previous_gesture_data = current_data

                # 6. Optional frame callback for GUI/Preview
                if self.on_frame_callback:
                    try:
                        self.on_frame_callback(frame, current_data, landmarks)
                    except Exception as cb_err:
                        print(f"[GestureManager] on_frame_callback error: {cb_err}")

            except Exception as e:
                if not self._is_running:
                    break
                consecutive_errors += 1
                if consecutive_errors > 15:
                    print(f"[GestureManager] Too many consecutive frame errors ({e}), stopping loop.")
                    break
                time.sleep(0.01)

        print("[GestureManager] Gesture worker loop exited.")

    def get_current_gesture(self) -> Dict[str, Any]:
        """Returns the latest stable gesture data."""
        return dict(self.current_gesture_data)
