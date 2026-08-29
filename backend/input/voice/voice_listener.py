import threading
import time
from typing import Optional, Callable, Dict, Any
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

from core.feedback.coordinator import SpeechCoordinator, get_speech_coordinator
from input.voice.voice_guardrail import VoiceGuardrail, VoiceIntentType, VoiceCommandMatch

class VoiceListener:
    """
    Continuous background voice listener with strict command intent parsing and duplicate prevention guardrails.
    
    Features:
    - Only recognizes registered commands (Lifecycle events & Whitelisted Desktop Actions).
    - Silently ignores casual conversation, chatter, and background speech.
    - Prevents duplicate command execution within a configurable debounce window.
    - Anti-Echo: Ignores incoming microphone audio while Nexa is speaking TTS.
    """
    def __init__(
        self,
        on_nexa_wake: Optional[Callable[[], None]] = None,
        on_nexa_close: Optional[Callable[[], None]] = None,
        on_gesture_mode_change: Optional[Callable[[bool, str], None]] = None,
        on_command: Optional[Callable[[str, Optional[Dict[str, Any]]], None]] = None,
        on_confirm: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        speech_coordinator: Optional[SpeechCoordinator] = None,
        guardrail: Optional[VoiceGuardrail] = None,
        on_mode_change: Optional[Callable[[bool, str], None]] = None, # backward compatibility
    ):
        self.on_nexa_wake = on_nexa_wake
        self.on_nexa_close = on_nexa_close
        self.on_gesture_mode_change = on_gesture_mode_change if on_gesture_mode_change is not None else on_mode_change
        self.on_command = on_command
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.speech_coordinator = speech_coordinator if speech_coordinator is not None else get_speech_coordinator()
        self.guardrail = guardrail if guardrail is not None else VoiceGuardrail()
        
        self.is_running = False
        self.thread = None
        self.recognizer = sr.Recognizer() if sr else None
        self.sample_rate = 16000
        self.energy_threshold = 300.0  # Dynamic calibration baseline

    def start(self):
        """Start listening in a background daemon thread."""
        if self.is_running:
            return
        if not sd:
            print("[VoiceListener] sounddevice not available. Voice commands disabled.")
            return
        if not sr:
            print("[VoiceListener] speech_recognition not available. Voice commands disabled.")
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("\n=== VOICE LISTENER INITIALIZED ===")
        print("🛡️ Guardrail Active: Casual conversation is automatically filtered out.")
        print("🌟 Lifecycle Commands:")
        print("   - 'Wake up Nexa' / 'Wake Nexa' / 'Start Nexa'")
        print("   - 'Close Nexa' / 'Sleep' / 'Go to sleep'")
        print("🖐️ Gesture Lifecycle Commands:")
        print("   - 'Enable gestures' / 'Start gestures' / 'Gesture mode on'")
        print("   - 'Disable gestures' / 'Stop gestures' / 'Gesture mode off'")
        print("🌐 Desktop Voice Commands (Silent execution):")
        print("   - Media: 'Play', 'Pause', 'Play pause', 'Volume up', 'Volume down', 'Mute'")
        print("   - Browser: 'Go back', 'Go forward', 'Next tab', 'Previous tab', 'Close tab', 'Refresh page'")
        print("   - Window: 'Open task view', 'Next window', 'Previous window', 'Select'")
        print("   - System: 'Zoom in', 'Zoom out', 'Reset zoom', 'Take screenshot'\n")

    def stop(self):
        """Stop listening."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        print("[VoiceListener] Stopped.")

    def _listen_loop(self):
        chunk_duration = 0.1  # 100ms chunks
        chunk_samples = int(self.sample_rate * chunk_duration)
        silence_limit = 0.5   # Seconds of silence to mark phrase end
        
        audio_buffer = []
        is_speaking = False
        silence_start_time = None
        
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16') as stream:
                # 1. Ambient noise calibration for 0.5s
                calibration_samples = []
                for _ in range(5):
                    data, _ = stream.read(chunk_samples)
                    samples = data.flatten()
                    calibration_samples.append(np.sqrt(np.mean(samples.astype(np.float64)**2)))
                ambient_rms = float(np.mean(calibration_samples))
                self.energy_threshold = max(25.0, min(120.0, ambient_rms * 2.5 + 15.0))
                print(f"[VoiceListener] Mic calibrated (Ambient: {ambient_rms:.1f}, Trigger Threshold: {self.energy_threshold:.1f})")
                
                # 2. Continuous listening stream
                while self.is_running:
                    data, overflowed = stream.read(chunk_samples)

                    # Discard mic audio when Nexa is speaking or in cooldown window
                    if self.speech_coordinator and self.speech_coordinator.is_voice_blocked():
                        is_speaking = False
                        silence_start_time = None
                        audio_buffer = []
                        continue

                    samples = data.flatten()
                    rms = np.sqrt(np.mean(samples.astype(np.float64)**2))
                    
                    if rms > self.energy_threshold:
                        if not is_speaking:
                            is_speaking = True
                            audio_buffer = []
                        silence_start_time = None
                        audio_buffer.append(data.tobytes())
                    elif is_speaking:
                        audio_buffer.append(data.tobytes())
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time > silence_limit:
                            # Finished speaking phrase
                            is_speaking = False
                            silence_start_time = None
                            if len(audio_buffer) >= 3:  # At least ~0.3s of speech
                                pcm_bytes = b"".join(audio_buffer)
                                threading.Thread(target=self._process_audio, args=(pcm_bytes,), daemon=True).start()
                            audio_buffer = []
        except Exception as e:
            if self.is_running:
                print(f"[VoiceListener] Microphone error: {e}")

    def _process_audio(self, pcm_bytes):
        if not self.recognizer or not sr:
            return

        if self.speech_coordinator and self.speech_coordinator.is_voice_blocked():
            return
            
        try:
            audio_data = sr.AudioData(pcm_bytes, self.sample_rate, 2)
            raw_text = self.recognizer.recognize_google(audio_data).lower().strip()

            if self.speech_coordinator and self.speech_coordinator.is_voice_blocked():
                return

            # 1. Guardrail: Strict Intent Parsing (Filters out casual conversation)
            match = self.guardrail.parse_command(raw_text)
            if match is None:
                # Silently ignore casual chatter / unregistered phrases
                return

            # 2. Guardrail: Duplicate Command & Rate Limiting Check
            allowed, block_reason = self.guardrail.should_execute(match)
            if not allowed:
                print(f"[Voice Guardrail] {block_reason}")
                return

            # 3. Authorized Command Dispatching
            intent = match.intent_type
            
            if intent == VoiceIntentType.LIFECYCLE_CLOSE:
                print(f"\n{'='*48}\n[Nexa] VOICE COMMAND: CLOSE / SLEEP NEXA (Matched: '{match.matched_phrase}')\n{'='*48}\n")
                if self.on_nexa_close:
                    self.on_nexa_close()

            elif intent == VoiceIntentType.LIFECYCLE_WAKE:
                print(f"\n{'='*48}\n[Nexa] VOICE COMMAND: WAKE NEXA (Matched: '{match.matched_phrase}')\n{'='*48}\n")
                if self.on_nexa_wake:
                    self.on_nexa_wake()

            elif intent == VoiceIntentType.GESTURE_DISABLE:
                print(f"\n{'='*48}\n[Nexa] VOICE COMMAND: DISABLE GESTURES (Matched: '{match.matched_phrase}')\n{'='*48}\n")
                if self.on_gesture_mode_change:
                    self.on_gesture_mode_change(False, raw_text)

            elif intent == VoiceIntentType.GESTURE_ENABLE:
                print(f"\n{'='*48}\n[Nexa] VOICE COMMAND: ENABLE GESTURES (Matched: '{match.matched_phrase}')\n{'='*48}\n")
                if self.on_gesture_mode_change:
                    self.on_gesture_mode_change(True, raw_text)

            elif intent == VoiceIntentType.CONFIRM_ACTION:
                print(f"\n{'='*48}\n[Nexa] VOICE COMMAND: CONFIRM ACTION (Matched: '{match.matched_phrase}')\n{'='*48}\n")
                if self.on_confirm:
                    self.on_confirm()

            elif intent == VoiceIntentType.CANCEL_ACTION:
                print(f"\n{'='*48}\n[Nexa] VOICE COMMAND: CANCEL ACTION (Matched: '{match.matched_phrase}')\n{'='*48}\n")
                if self.on_cancel:
                    self.on_cancel()

            elif intent == VoiceIntentType.REGISTERED_ACTION and match.action_name:
                param_str = f" {match.params}" if match.params else ""
                print(f"\n{'='*48}\n[Nexa] VOICE COMMAND: EXECUTING -> {match.action_name.upper()}{param_str} (Matched: '{match.matched_phrase}')\n{'='*48}\n")
                if self.on_command:
                    try:
                        self.on_command(match.action_name, match.params)
                    except TypeError:
                        self.on_command(match.action_name)

        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"[VoiceListener] Speech recognition network error: {e}")
        except Exception as e:
            print(f"[VoiceListener] Recognition error: {e}")
