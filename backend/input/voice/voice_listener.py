import threading
import time
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

class VoiceListener:
    def __init__(self, on_mode_change=None, sample_rate=16000):
        """
        Listens for voice commands like 'Start Nexa' / 'Stop Nexa' or 'Mode On' / 'Mode Off'
        using a lightweight background audio stream and speech recognition.
        """
        self.on_mode_change = on_mode_change  # Callback func(is_active: bool, command_text: str)
        self.sample_rate = sample_rate
        self.recognizer = sr.Recognizer() if sr else None
        self.is_running = False
        self.thread = None
        self.energy_threshold = 40.0

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
        print("🎤 Say 'Start Nexa' or 'Mode On' to activate gesture controls.")
        print("🎤 Say 'Stop Nexa' or 'Mode Off' to deactivate.\n")

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
                # 1. Quick ambient noise calibration for 0.5s
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
                    samples = data.flatten()
                    rms = np.sqrt(np.mean(samples.astype(np.float64)**2))
                    
                    if rms > self.energy_threshold:
                        if not is_speaking:
                            is_speaking = True
                            audio_buffer = []
                            # print("[Voice] Hearing voice...")
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
            
        try:
            audio_data = sr.AudioData(pcm_bytes, self.sample_rate, 2)
            text = self.recognizer.recognize_google(audio_data).lower().strip()
            print(f"[Voice] Recognized: '{text}'")
            
            # Simple & comprehensive activation phrases
            activation_phrases = [
                "start nexa",
                "nexa start",
                "nexa on",
                "mode on",
                "turn on",
                "start hand",
                "hand on",
                "start",
                "activate",
                "enable",
                "hand gesture mode on",
                "gesture mode on",
                "gesture on",
                "hand mode on",
                "start gesture",
                "start next",
                "next on",
                "nexus on",
                "nexus start",
                "alexa on",
                "kesar mode on"
            ]
            
            # Simple & comprehensive deactivation phrases
            deactivation_phrases = [
                "stop nexa",
                "nexa stop",
                "nexa off",
                "mode off",
                "turn off",
                "stop hand",
                "hand off",
                "stop",
                "deactivate",
                "disable",
                "hand gesture mode off",
                "gesture mode off",
                "gesture off",
                "hand mode off",
                "stop gesture",
                "stop next",
                "next off",
                "kesar mode off"
            ]
            
            # Check deactivation first so "stop" takes priority if both match
            if any(phrase in text for phrase in deactivation_phrases):
                print(f"\n{'='*48}\n[Nexa] VOICE COMMAND: DEACTIVATING GESTURE MODE\n{'='*48}\n")
                if self.on_mode_change:
                    self.on_mode_change(False, text)
                    
            elif any(phrase in text for phrase in activation_phrases):
                print(f"\n{'='*48}\n[Nexa] VOICE COMMAND: ACTIVATING GESTURE MODE\n{'='*48}\n")
                if self.on_mode_change:
                    self.on_mode_change(True, text)
                    
        except sr.UnknownValueError:
            # print("[Voice] (Speech was not clear)")
            pass
        except sr.RequestError as e:
            print(f"[VoiceListener] Speech recognition network error: {e}")
        except Exception as e:
            print(f"[VoiceListener] Recognition error: {e}")
