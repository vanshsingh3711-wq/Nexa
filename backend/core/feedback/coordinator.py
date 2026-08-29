import time
import threading
from typing import Optional

class SpeechCoordinator:
    """
    Thread-safe coordinator for tracking voice synthesis activity and cooldown periods.
    Prevents the microphone and speech recognizer from picking up and responding to Nexa's own TTS output.
    """
    def __init__(self, default_cooldown: float = 0.5):
        self._lock = threading.Lock()
        self._is_speaking = False
        self._speech_end_time = 0.0
        self._default_cooldown = default_cooldown

    @property
    def is_speaking(self) -> bool:
        """Returns True if the TTS engine is currently outputting audio."""
        with self._lock:
            return self._is_speaking

    def mark_speaking_started(self) -> None:
        """Called immediately before the TTS engine starts audio synthesis."""
        with self._lock:
            self._is_speaking = True

    def mark_speaking_finished(self, cooldown: Optional[float] = None) -> None:
        """Called immediately after the TTS engine finishes audio synthesis."""
        cooldown_period = cooldown if cooldown is not None else self._default_cooldown
        with self._lock:
            self._is_speaking = False
            self._speech_end_time = time.time() + max(0.0, cooldown_period)

    def is_voice_blocked(self) -> bool:
        """
        Returns True if Nexa is currently speaking or in the post-speech cooldown window.
        When True, incoming microphone speech recognition must ignore detected audio.
        """
        with self._lock:
            if self._is_speaking:
                return True
            return time.time() < self._speech_end_time

    def reset(self) -> None:
        """Resets coordinator state to unblocked."""
        with self._lock:
            self._is_speaking = False
            self._speech_end_time = 0.0

_default_coordinator: Optional[SpeechCoordinator] = None
_coordinator_lock = threading.Lock()

def get_speech_coordinator() -> SpeechCoordinator:
    """Returns the shared singleton instance of SpeechCoordinator."""
    global _default_coordinator
    with _coordinator_lock:
        if _default_coordinator is None:
            _default_coordinator = SpeechCoordinator()
        return _default_coordinator
