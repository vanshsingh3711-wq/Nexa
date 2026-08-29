import time
import threading
from typing import Dict, Any, Optional
from core.feedback.messages import (
    LIFECYCLE_FEEDBACK,
    NEXA_ACTIVATED_MESSAGE,
    NEXA_CLOSING_MESSAGE,
    GESTURES_ENABLED_MESSAGE,
    GESTURES_DISABLED_MESSAGE,
    get_action_message,
)
from core.feedback.speech import SpeechService, get_speech_service

class FeedbackService:
    """
    Coordinates selective verbal feedback for application and gesture lifecycle events.
    
    Principles:
    - Normal desktop control actions are completely SILENT.
    - Spoken feedback is strictly reserved for Lifecycle Events (Wake, Close, Enable/Disable Gestures).
    - Lifecycle messages are spoken ONLY after the state operation successfully completes.
    - Thread-safe and fail-safe: TTS errors never roll back application state.
    """
    def __init__(
        self,
        speech_service: Optional[SpeechService] = None,
        repeat_debounce_sec: float = 0.5
    ):
        self.speech_service = speech_service if speech_service is not None else get_speech_service()
        self.repeat_debounce_sec = repeat_debounce_sec
        self._last_spoken_action: Optional[str] = None
        self._last_spoken_time: float = 0.0
        self._lock = threading.Lock()

    def handle_nexa_wake(self) -> str:
        """Verbally confirms Nexa application activation."""
        message = NEXA_ACTIVATED_MESSAGE
        with self._lock:
            self._last_spoken_action = "nexa_activated"
            self._last_spoken_time = time.time()

        self.speech_service.speak(message)
        return message

    def handle_nexa_close(self, block: bool = True) -> str:
        """Verbally confirms Nexa application shutdown."""
        message = NEXA_CLOSING_MESSAGE
        with self._lock:
            self._last_spoken_action = "nexa_closing"
            self._last_spoken_time = time.time()

        self.speech_service.speak(message, block=block)
        return message

    def handle_gestures_enabled(self) -> str:
        """Verbally confirms successful start of the gesture subsystem."""
        message = GESTURES_ENABLED_MESSAGE
        with self._lock:
            self._last_spoken_action = "gestures_enabled"
            self._last_spoken_time = time.time()

        self.speech_service.speak(message)
        return message

    def handle_gestures_disabled(self) -> str:
        """Verbally confirms successful release of the gesture subsystem."""
        message = GESTURES_DISABLED_MESSAGE
        with self._lock:
            self._last_spoken_action = "gestures_disabled"
            self._last_spoken_time = time.time()

        self.speech_service.speak(message)
        return message

    def handle_gesture_lifecycle(self, enabled: bool) -> str:
        """Convenience dispatcher for gesture lifecycle state transitions."""
        if enabled:
            return self.handle_gestures_enabled()
        else:
            return self.handle_gestures_disabled()

    def handle_mode_change(self, is_active: bool) -> str:
        """Backward compatibility for mode toggles."""
        if is_active:
            return self.handle_nexa_wake()
        else:
            return self.handle_nexa_close(block=False)

    def handle_confirmation_needed(self, action: str, target: Optional[str] = None) -> str:
        """Asks the user for verbal confirmation before executing high-risk action."""
        if action == "close_app":
            if target and target != "active":
                app_name = target.replace("_", " ").title()
                try:
                    from core.applications.registry import get_default_application_registry
                    app_def = get_default_application_registry().resolve(target)
                    if app_def:
                        name_map = {
                            "chrome": "Chrome",
                            "brave": "Brave",
                            "vscode": "VS Code",
                            "antigravity": "Antigravity",
                            "file_explorer": "File Explorer",
                            "notepad": "Notepad",
                        }
                        app_name = name_map.get(app_def.app_id, app_def.display_name)
                except Exception:
                    pass
                message = f"Are you sure you want to close {app_name} application? Say confirm or yes to proceed."
            else:
                message = "Are you sure you want to close the active application? Say confirm or yes to proceed."
        else:
            message = f"Are you sure you want to execute {action}? Say confirm or yes to proceed."
            
        with self._lock:
            self._last_spoken_action = "confirm_needed"
            self._last_spoken_time = time.time()

        self.speech_service.speak(message)
        return message

    def handle_confirmation_cancelled(self) -> str:
        """Verbally confirms action cancellation."""
        message = "Cancelled."
        with self._lock:
            self._last_spoken_action = "action_cancelled"
            self._last_spoken_time = time.time()

        self.speech_service.speak(message)
        return message

    def handle_confirmation_confirmed(self, target: Optional[str] = None) -> str:
        """Verbally confirms proceeding with action."""
        if target and target != "active":
            app_name = target.replace("_", " ").title()
            try:
                from core.applications.registry import get_default_application_registry
                app_def = get_default_application_registry().resolve(target)
                if app_def:
                    name_map = {
                        "chrome": "Chrome",
                        "brave": "Brave",
                        "vscode": "VS Code",
                        "antigravity": "Antigravity",
                        "file_explorer": "File Explorer",
                        "notepad": "Notepad",
                    }
                    app_name = name_map.get(app_def.app_id, app_def.display_name)
            except Exception:
                pass
            message = f"Closing {app_name} application."
        else:
            message = "Closing application."

        with self._lock:
            self._last_spoken_action = "action_confirmed"
            self._last_spoken_time = time.time()

        self.speech_service.speak(message)
        return message

    def handle_action_success(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        source: str = "unknown"
    ) -> Optional[str]:
        """
        Normal desktop control actions must remain completely SILENT.
        Always returns None without triggering speech synthesis.
        """
        return None

_default_feedback_service: Optional[FeedbackService] = None
_feedback_lock = threading.Lock()

def get_feedback_service() -> FeedbackService:
    """Returns the shared singleton instance of FeedbackService."""
    global _default_feedback_service
    with _feedback_lock:
        if _default_feedback_service is None:
            _default_feedback_service = FeedbackService()
        return _default_feedback_service
