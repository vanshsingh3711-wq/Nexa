import time
import queue
import threading
from typing import Optional

try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None
    pythoncom = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

from core.feedback.coordinator import SpeechCoordinator, get_speech_coordinator

class SpeechService:
    """
    Asynchronous, non-blocking Text-to-Speech service for verbal feedback.
    
    Features:
    - Runs completely offline on local Windows SAPI5 via native COM / pyttsx3.
    - Single persistent background daemon worker with a bounded task queue.
    - Zero interference with real-time gesture tracking and camera loop.
    - Coordinates with SpeechCoordinator to prevent microphone self-triggering.
    - Thread-safe and fail-safe: errors in TTS never affect action outcomes.
    """
    def __init__(
        self,
        coordinator: Optional[SpeechCoordinator] = None,
        speech_rate: int = 185,
        volume: float = 1.0,
        max_queue_size: int = 10
    ):
        self.coordinator = coordinator if coordinator is not None else get_speech_coordinator()
        self.speech_rate = speech_rate
        self.volume = volume
        self.max_queue_size = max_queue_size
        
        self._queue: queue.Queue = queue.Queue(maxsize=self.max_queue_size)
        self._worker_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._lock = threading.Lock()
        
        self._start_worker()

    def _start_worker(self) -> None:
        with self._lock:
            if not self._is_running:
                self._is_running = True
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    name="Nexa-TTS-Worker",
                    daemon=True
                )
                self._worker_thread.start()

    def _worker_loop(self) -> None:
        """Dedicated worker loop that speaks queued utterances reliably."""
        if pythoncom:
            try:
                pythoncom.CoInitialize()
            except Exception:
                pass

        speaker = None
        # 1. Primary: Native Windows SAPI.SpVoice (most reliable on Windows)
        if win32com:
            try:
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                # SAPI rate ranges from -10 to 10
                speaker.Rate = max(-10, min(10, int((self.speech_rate - 185) / 15)))
                speaker.Volume = max(0, min(100, int(self.volume * 100)))
            except Exception:
                speaker = None

        # 2. Fallback: pyttsx3
        if speaker is None and pyttsx3:
            try:
                speaker = pyttsx3.init()
                speaker.setProperty("rate", self.speech_rate)
                speaker.setProperty("volume", self.volume)
            except Exception:
                speaker = None

        while self._is_running:
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if text is None: # Sentinel to terminate
                self._queue.task_done()
                break

            try:
                # 1. Notify coordinator that speech is beginning (mutes mic)
                self.coordinator.mark_speaking_started()
                print(f"[Nexa Speech] Speaking: \"{text}\"")

                # 2. Output speech via native SAPI or fallback
                if speaker is not None:
                    if hasattr(speaker, "Speak"):
                        speaker.Speak(text)
                    elif hasattr(speaker, "say"):
                        speaker.say(text)
                        speaker.runAndWait()
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"[SpeechService] Error during TTS synthesis: {e}")
            finally:
                # 3. Mark speech finished and start cooldown
                self.coordinator.mark_speaking_finished()
                self._queue.task_done()

        if pythoncom:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def speak(self, text: str, block: bool = False) -> None:
        """
        Enqueues text to be spoken asynchronously.
        If block is True, blocks until the queue finishes processing the speech.
        """
        if not text or not text.strip():
            return
            
        clean_text = text.strip()

        if not self._is_running:
            return

        try:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except (queue.Empty, ValueError):
                    pass
            self._queue.put(clean_text, timeout=0.5)
            if block:
                self._queue.join()
        except Exception as e:
            print(f"[SpeechService] Error enqueuing speech: {e}")

    def stop(self, timeout: float = 1.0) -> None:
        """Gracefully stops the worker thread."""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False

        try:
            self._queue.put_nowait(None)
        except (queue.Full, Exception):
            pass

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

_default_speech_service: Optional[SpeechService] = None
_speech_lock = threading.Lock()

def get_speech_service() -> SpeechService:
    """Returns the shared singleton instance of SpeechService."""
    global _default_speech_service
    with _speech_lock:
        if _default_speech_service is None:
            _default_speech_service = SpeechService()
        return _default_speech_service
