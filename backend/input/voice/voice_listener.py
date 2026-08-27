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
        Listens for voice commands like 'Hand gesture mode on' / 'Hand gesture mode off'
        using a lightweight background audio stream and speech recognition.
        """
        self.on_mode_change = on_mode_change  # Callback func(is_active: bool, command_text: str)
        self.sample_rate = sample_rate
        self.recognizer = sr.Recognizer() if sr else None
        self.is_running = False
        self.thread = None

    def start(self):
        """Start listening in a background daemon thread."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("\n=== VOICE LISTENER STARTED ===")
        print("Say 'Start Nexa' (or 'Mode On') to activate.")
        print("Say 'Stop Nexa' (or 'Mode Off') to deactivate.\n")

    def stop(self):
        """Stop listening."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        print("[VoiceListener] Stopped.")

    def _listen_loop(self):
        chunk_duration = 0.1  # 100ms chunks
        chunk_samples = int(self.sample_rate * chunk_duration)
        energy_threshold = 250  # More sensitive threshold for clear audio pickup
        silence_limit = 0.6  # Seconds of silence to mark phrase end
        
        audio_buffer = []
        is_speaking = False
        silence_start_time = None
        
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16') as stream:
                while self.is_running:
                    data, overflowed = stream.read(chunk_samples)
                    samples = data.flatten()
                    rms = np.sqrt(np.mean(samples.astype(np.float64)**2))
                    
                    if rms > energy_threshold:
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
                            if len(audio_buffer) >= 4:  # At least ~0.4s of speech
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
            
            # Simple & easy activation phrases
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
                "hand gesture mode on",
                "gesture mode on",
                "gesture on",
                "kesar mode on"  # Common phonetic mishearing of gesture mode on
            ]
            
            # Simple & easy deactivation phrases
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
                "hand gesture mode off",
                "gesture mode off",
                "gesture off",
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
            pass  # Background noise or unrecognizable speech
        except sr.RequestError as e:
            print(f"[VoiceListener] Speech recognition service error: {e}")
        except Exception as e:
            print(f"[VoiceListener] Recognition error: {e}")
