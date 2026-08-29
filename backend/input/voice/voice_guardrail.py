import time
import re
import threading
from typing import Optional, Dict, List, Tuple
from enum import Enum

class VoiceIntentType(str, Enum):
    LIFECYCLE_WAKE = "LIFECYCLE_WAKE"
    LIFECYCLE_CLOSE = "LIFECYCLE_CLOSE"
    GESTURE_ENABLE = "GESTURE_ENABLE"
    GESTURE_DISABLE = "GESTURE_DISABLE"
    REGISTERED_ACTION = "REGISTERED_ACTION"
    UNKNOWN = "UNKNOWN"

class VoiceCommandMatch:
    """Represents a successfully parsed, authorized voice command match."""
    def __init__(
        self,
        intent_type: VoiceIntentType,
        action_name: Optional[str] = None,
        matched_phrase: str = "",
        raw_text: str = ""
    ):
        self.intent_type = intent_type
        self.action_name = action_name
        self.matched_phrase = matched_phrase
        self.raw_text = raw_text

    def __repr__(self):
        return f"<VoiceCommandMatch intent={self.intent_type.value} action={self.action_name} phrase='{self.matched_phrase}'>"

class VoiceGuardrail:
    """
    Guardrail for Nexa Voice Input.
    
    Responsibilities:
    1. Strict Registered Command Recognition:
       Only parses registered lifecycle commands and actions.
       Silently ignores casual conversation, chatter, and background speech.
    2. Duplicate Command Prevention:
       Debounces repeated/duplicate command invocations within a configurable cooldown window.
    3. Global Cooldown Protection:
       Prevents rapid-fire overlapping voice triggers from noisy audio chunks.
    4. Anti-Echo Integration:
       Integrates with SpeechCoordinator to ensure complete silence during Nexa speech output.
    """
    def __init__(
        self,
        default_debounce_sec: float = 1.5,
        volume_debounce_sec: float = 0.35,
        global_min_interval_sec: float = 0.3,
        max_words_in_command: int = 7
    ):
        self.default_debounce_sec = default_debounce_sec
        self.volume_debounce_sec = volume_debounce_sec
        self.global_min_interval_sec = global_min_interval_sec
        self.max_words_in_command = max_words_in_command
        
        self._lock = threading.Lock()
        self._last_command_time: Dict[str, float] = {}
        self._last_any_command_time: float = 0.0
        
        # Pre-compile registered command dictionaries and regexes
        self._init_registered_command_patterns()

    def _init_registered_command_patterns(self):
        # 1. Lifecycle Wake
        self.wake_phrases = [
            "wake up nexa", "wake nexa", "start nexa", "wake up",
            "wake up nexon", "wake nexon", "start nexon", "nexa start",
            "nexa wake", "nexa on", "nexus on", "nexus start", "activate nexa"
        ]

        # 2. Lifecycle Close / Sleep
        self.close_phrases = [
            "close nexa", "exit nexa", "go to sleep", "stop nexa",
            "nexa stop", "nexa sleep", "nexa close", "sleep", "deactivate nexa"
        ]

        # 3. Gesture Enable
        self.gesture_enable_phrases = [
            "enable gestures", "start gestures", "gesture mode on",
            "gestures on", "enable gesture", "start gesture", "gesture on",
            "start hand", "hand on", "start camera", "enable camera"
        ]

        # 4. Gesture Disable
        self.gesture_disable_phrases = [
            "disable gestures", "stop gestures", "gesture mode off",
            "gestures off", "disable gesture", "stop gesture", "gesture off",
            "stop hand", "hand off", "stop camera", "disable camera"
        ]

        # 5. Registered Desktop Actions (Ordered from most specific to least specific)
        self.action_commands: List[Tuple[str, str]] = [
            # Media Controls
            ("toggle play pause", "toggle_play_pause"),
            ("toggle play", "toggle_play_pause"),
            ("toggle pause", "toggle_play_pause"),
            ("play pause", "toggle_play_pause"),
            ("increase volume", "volume_up"),
            ("volume up", "volume_up"),
            ("decrease volume", "volume_down"),
            ("volume down", "volume_down"),
            ("toggle mute", "volume_mute"),
            ("unmute", "volume_mute"),
            ("mute", "volume_mute"),
            ("play media", "media_play"),
            ("play music", "media_play"),
            ("play video", "media_play"),
            ("resume", "media_play"),
            ("play", "media_play"),
            ("pause media", "media_pause"),
            ("pause video", "media_pause"),
            ("pause music", "media_pause"),
            ("pause", "media_pause"),

            # Window Management
            ("open task view", "open_task_view"),
            ("task view", "open_task_view"),
            ("select next window", "select_next_window"),
            ("next window", "select_next_window"),
            ("select previous window", "select_prev_window"),
            ("previous window", "select_prev_window"),
            ("prev window", "select_prev_window"),
            ("confirm selection", "confirm_selection"),
            ("confirm window", "confirm_selection"),
            ("select window", "confirm_selection"),
            ("select", "confirm_selection"),

            # System / Utilities
            ("take a screenshot", "take_screenshot"),
            ("take screenshot", "take_screenshot"),
            ("capture screen", "take_screenshot"),
            ("screenshot", "take_screenshot"),
            ("reset zoom", "reset_zoom"),
            ("default zoom", "reset_zoom"),
            ("normal zoom", "reset_zoom"),
            ("zoom reset", "reset_zoom"),
            ("zoom into", "zoom_in"),
            ("zoom in", "zoom_in"),
            ("magnify", "zoom_in"),
            ("zoom back", "zoom_out"),
            ("zoom out", "zoom_out"),

            # Browser Navigation
            ("close current tab", "close_tab"),
            ("close tab", "close_tab"),
            ("refresh page", "refresh_page"),
            ("reload page", "refresh_page"),
            ("refresh", "refresh_page"),
            ("reload", "refresh_page"),
            ("next browser tab", "next_tab"),
            ("next tab", "next_tab"),
            ("previous browser tab", "prev_tab"),
            ("previous tab", "prev_tab"),
            ("prev tab", "prev_tab"),
            ("browser forward", "browser_forward"),
            ("forward page", "browser_forward"),
            ("go forward", "browser_forward"),
            ("browser back", "browser_back"),
            ("back page", "browser_back"),
            ("go back", "browser_back"),
        ]

    def _normalize_text(self, text: str) -> str:
        """Cleans and normalizes recognized audio text."""
        if not text:
            return ""
        # Remove punctuation, convert to lowercase, normalize whitespace
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(cleaned.split())

    def _is_word_boundary_match(self, phrase: str, text: str) -> bool:
        """Checks if phrase appears in text with strict word boundaries."""
        pattern = r"\b" + re.escape(phrase) + r"\b"
        return bool(re.search(pattern, text))

    def parse_command(self, raw_text: str) -> Optional[VoiceCommandMatch]:
        """
        Parses recognized speech text strictly against registered commands.
        Returns VoiceCommandMatch if text is a registered command; returns None if it is casual conversation.
        """
        norm_text = self._normalize_text(raw_text)
        if not norm_text:
            return None

        words = norm_text.split()
        # Guardrail: If utterance is too long (e.g. casual conversation/story), ignore it
        if len(words) > self.max_words_in_command:
            # Check if it explicitly starts with 'nexa' or 'hey nexa' command prefix
            if not norm_text.startswith("nexa ") and not norm_text.startswith("hey nexa "):
                return None

        # 1. Check Lifecycle: Close / Sleep Nexa
        for phrase in self.close_phrases:
            if self._is_word_boundary_match(phrase, norm_text):
                return VoiceCommandMatch(
                    intent_type=VoiceIntentType.LIFECYCLE_CLOSE,
                    matched_phrase=phrase,
                    raw_text=raw_text
                )

        # 2. Check Lifecycle: Wake Nexa
        for phrase in self.wake_phrases:
            if self._is_word_boundary_match(phrase, norm_text):
                return VoiceCommandMatch(
                    intent_type=VoiceIntentType.LIFECYCLE_WAKE,
                    matched_phrase=phrase,
                    raw_text=raw_text
                )

        # 3. Check Gesture Lifecycle: Disable Gestures
        for phrase in self.gesture_disable_phrases:
            if self._is_word_boundary_match(phrase, norm_text):
                return VoiceCommandMatch(
                    intent_type=VoiceIntentType.GESTURE_DISABLE,
                    matched_phrase=phrase,
                    raw_text=raw_text
                )

        # 4. Check Gesture Lifecycle: Enable Gestures
        for phrase in self.gesture_enable_phrases:
            if self._is_word_boundary_match(phrase, norm_text):
                return VoiceCommandMatch(
                    intent_type=VoiceIntentType.GESTURE_ENABLE,
                    matched_phrase=phrase,
                    raw_text=raw_text
                )

        # 5. Check Registered Desktop Actions
        for phrase, action_name in self.action_commands:
            if self._is_word_boundary_match(phrase, norm_text):
                return VoiceCommandMatch(
                    intent_type=VoiceIntentType.REGISTERED_ACTION,
                    action_name=action_name,
                    matched_phrase=phrase,
                    raw_text=raw_text
                )

        # Unrecognized speech / casual conversation -> safely ignored
        return None

    def should_execute(self, match: VoiceCommandMatch) -> Tuple[bool, Optional[str]]:
        """
        Applies duplicate command prevention and debounce guardrails.
        Returns (True, None) if allowed to execute; (False, reason) if blocked.
        """
        now = time.time()
        with self._lock:
            # 1. Command-Specific Duplicate Debounce
            cmd_key = match.action_name if match.action_name else match.intent_type.value
            last_time = self._last_command_time.get(cmd_key, 0.0)

            # Determine cooldown period for this command
            if match.action_name in ("volume_up", "volume_down"):
                cooldown = self.volume_debounce_sec
            else:
                cooldown = self.default_debounce_sec

            if now - last_time < cooldown:
                return False, f"Blocked duplicate command '{cmd_key}' (debounced within {cooldown}s)"

            # 2. Global Rapid-Fire Guardrail across different commands
            if now - self._last_any_command_time < self.global_min_interval_sec:
                return False, f"Blocked: Rapid fire interval (< {self.global_min_interval_sec}s)"

            # Update timestamps
            self._last_command_time[cmd_key] = now
            self._last_any_command_time = now
            return True, None

    def reset_cooldowns(self):
        """Resets all debounce timestamps."""
        with self._lock:
            self._last_command_time.clear()
            self._last_any_command_time = 0.0
