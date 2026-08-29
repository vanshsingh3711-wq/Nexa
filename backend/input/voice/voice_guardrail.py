import time
import re
import threading
from typing import Optional, Dict, List, Tuple, Any
from enum import Enum

from core.applications.registry import ApplicationRegistry, get_default_application_registry

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
        params: Optional[Dict[str, Any]] = None,
        matched_phrase: str = "",
        raw_text: str = ""
    ):
        self.intent_type = intent_type
        self.action_name = action_name
        self.params = params or {}
        self.matched_phrase = matched_phrase
        self.raw_text = raw_text

    def __repr__(self):
        return f"<VoiceCommandMatch intent={self.intent_type.value} action={self.action_name} params={self.params} phrase='{self.matched_phrase}'>"

class VoiceGuardrail:
    """
    Guardrail for Nexa Voice Input.
    
    Responsibilities:
    1. Strict Registered Command Recognition:
       Only parses registered lifecycle commands and actions.
       Silently ignores casual conversation, chatter, and background speech.
    2. Precise Volume Voice Control:
       Supports exact volume targets ("volume down to 45", "set volume to 60")
       and delta step adjustments ("volume up by 100", "decrease volume by 20").
    3. Gesture Mode Lifecycle Control:
       Allows toggling gesture mode (camera & tracking) ON/OFF via explicit voice commands.
    4. Duplicate Command Prevention:
       Debounces repeated/duplicate command invocations within a configurable cooldown window.
    5. Global Cooldown Protection:
       Prevents rapid-fire overlapping voice triggers from noisy audio chunks.
    6. Anti-Echo Integration:
       Integrates with SpeechCoordinator to ensure complete silence during Nexa speech output.
    """
    def __init__(
        self,
        default_debounce_sec: float = 1.5,
        volume_debounce_sec: float = 0.35,
        global_min_interval_sec: float = 0.3,
        max_words_in_command: int = 7,
        app_registry: Optional[ApplicationRegistry] = None,
    ):
        self.default_debounce_sec = default_debounce_sec
        self.volume_debounce_sec = volume_debounce_sec
        self.global_min_interval_sec = global_min_interval_sec
        self.max_words_in_command = max_words_in_command
        self.app_registry = app_registry if app_registry is not None else get_default_application_registry()
        
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

        # 3. Gesture Enable (Explicit on-demand commands)
        self.gesture_enable_phrases = [
            "turn on gestures", "turn on gesture", "enable gestures", "start gestures",
            "gesture mode on", "gestures on", "enable gesture", "start gesture",
            "gesture on", "turn on camera", "start camera", "enable camera",
            "camera on", "start hand", "hand on", "hand mode on",
            "turn on hand mode", "activate gestures", "activate gesture"
        ]

        # 4. Gesture Disable (Explicit turn off commands)
        self.gesture_disable_phrases = [
            "turn off gestures", "turn off gesture", "disable gestures", "stop gestures",
            "gesture mode off", "gestures off", "disable gesture", "stop gesture",
            "gesture off", "turn off camera", "stop camera", "disable camera",
            "camera off", "stop hand", "hand off", "hand mode off",
            "turn off hand mode", "deactivate gestures", "deactivate gesture"
        ]

        # 5. Registered Desktop Actions (Ordered from most specific to least specific)
        self.action_commands: List[Tuple[str, str]] = [
            # Media Controls
            ("toggle play pause", "toggle_play_pause"),
            ("toggle play", "toggle_play_pause"),
            ("toggle pause", "toggle_play_pause"),
            ("play pause", "toggle_play_pause"),
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
            ("take a screen shot", "take_screenshot"),
            ("take screenshot", "take_screenshot"),
            ("take screen shot", "take_screenshot"),
            ("capture screenshot", "take_screenshot"),
            ("capture screen", "take_screenshot"),
            ("save screenshot", "take_screenshot"),
            ("screen capture", "take_screenshot"),
            ("screenshot", "take_screenshot"),
            ("screen shot", "take_screenshot"),
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

            # Window & Active Application Closing
            ("close the active application", "close_app"),
            ("close active application", "close_app"),
            ("close the active app", "close_app"),
            ("close active app", "close_app"),
            ("close the current application", "close_app"),
            ("close current application", "close_app"),
            ("close the current app", "close_app"),
            ("close current app", "close_app"),
            ("close the active window", "close_app"),
            ("close active window", "close_app"),
            ("close the current window", "close_app"),
            ("close current window", "close_app"),
            ("close this window", "close_app"),
            ("close this app", "close_app"),
            ("close the window", "close_app"),
            ("close window", "close_app"),
            ("close the application", "close_app"),
            ("close application", "close_app"),
            ("close the app", "close_app"),
            ("close app", "close_app"),
            ("close this", "close_app"),
            ("exit active application", "close_app"),
            ("exit active app", "close_app"),
            ("exit current app", "close_app"),
            ("exit the app", "close_app"),
            ("exit app", "close_app"),
            ("exit application", "close_app"),
            ("exit window", "close_app"),
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

    def _parse_volume_command(self, norm_text: str, raw_text: str) -> Optional[VoiceCommandMatch]:
        """
        Parses precise volume commands including:
        - Target absolute volume: 'volume down to 45', 'volume up to 80', 'set volume to 50', 'volume to 45', 'volume 50 percent'
        - Relative volume UP: 'volume up by 100', 'increase volume by 20', 'volume up 20'
        - Relative volume DOWN: 'volume down by 30', 'decrease volume by 25', 'volume down 30'
        - Default step volume: 'volume up', 'volume down'
        """
        # 1. Target Absolute Volume (e.g. 'volume down to 45', 'volume up to 80', 'set volume to 60', 'volume to 45')
        m_abs = re.search(
            r"\b(?:(?:set|change|turn|adjust)?\s*volume\s*(?:down|up)?\s*to|set\s*(?:the\s*)?volume\s*(?:to)?)\s*(\d{1,3})\s*(?:%|percent)?\b",
            norm_text
        )
        if m_abs:
            val = int(m_abs.group(1))
            return VoiceCommandMatch(
                intent_type=VoiceIntentType.REGISTERED_ACTION,
                action_name="set_volume",
                params={"level": max(0, min(100, val))},
                matched_phrase=m_abs.group(0),
                raw_text=raw_text
            )

        # 2. Target Absolute Volume ('volume 70 percent', 'set volume 50')
        m_abs2 = re.search(r"\b(?:set\s*)?volume\s*(\d{1,3})\s*(?:%|percent)\b", norm_text)
        if m_abs2:
            val = int(m_abs2.group(1))
            return VoiceCommandMatch(
                intent_type=VoiceIntentType.REGISTERED_ACTION,
                action_name="set_volume",
                params={"level": max(0, min(100, val))},
                matched_phrase=m_abs2.group(0),
                raw_text=raw_text
            )

        # 3. Relative Volume UP by delta (e.g. 'volume up by 100', 'increase volume by 20', 'volume up 20')
        m_up = re.search(
            r"\b(?:volume\s*up|increase\s*volume|turn\s*up\s*(?:the\s*)?volume|raise\s*volume)\s*(?:by\s*)?(\d{1,3})\s*(?:%|percent)?\b",
            norm_text
        )
        if m_up:
            val = int(m_up.group(1))
            return VoiceCommandMatch(
                intent_type=VoiceIntentType.REGISTERED_ACTION,
                action_name="volume_up",
                params={"step": max(1, min(100, val))},
                matched_phrase=m_up.group(0),
                raw_text=raw_text
            )

        # 4. Relative Volume DOWN by delta (e.g. 'volume down by 30', 'decrease volume by 15', 'volume down 30')
        m_down = re.search(
            r"\b(?:volume\s*down|decrease\s*volume|turn\s*down\s*(?:the\s*)?volume|lower\s*volume)\s*(?:by\s*)?(\d{1,3})\s*(?:%|percent)?\b",
            norm_text
        )
        if m_down:
            val = int(m_down.group(1))
            return VoiceCommandMatch(
                intent_type=VoiceIntentType.REGISTERED_ACTION,
                action_name="volume_down",
                params={"step": max(1, min(100, val))},
                matched_phrase=m_down.group(0),
                raw_text=raw_text
            )

        # 5. Default Discrete Volume UP ('volume up', 'increase volume')
        if any(self._is_word_boundary_match(p, norm_text) for p in ["volume up", "increase volume", "turn up volume", "raise volume"]):
            return VoiceCommandMatch(
                intent_type=VoiceIntentType.REGISTERED_ACTION,
                action_name="volume_up",
                params={"step": 5},
                matched_phrase="volume up",
                raw_text=raw_text
            )

        # 6. Default Discrete Volume DOWN ('volume down', 'decrease volume')
        if any(self._is_word_boundary_match(p, norm_text) for p in ["volume down", "decrease volume", "turn down volume", "lower volume"]):
            return VoiceCommandMatch(
                intent_type=VoiceIntentType.REGISTERED_ACTION,
                action_name="volume_down",
                params={"step": 5},
                matched_phrase="volume down",
                raw_text=raw_text
            )

        return None

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

        # 5. Check Precise Volume Controls
        volume_match = self._parse_volume_command(norm_text, raw_text)
        if volume_match is not None:
            return volume_match

        # 6. Check Registered Desktop Actions
        for phrase, action_name in self.action_commands:
            if self._is_word_boundary_match(phrase, norm_text):
                return VoiceCommandMatch(
                    intent_type=VoiceIntentType.REGISTERED_ACTION,
                    action_name=action_name,
                    matched_phrase=phrase,
                    raw_text=raw_text
                )

        # 7. Check Allowlisted Application Launch Commands (e.g. 'open vs code', 'launch chrome', 'open notepad')
        app_match = self._parse_application_command(norm_text, raw_text)
        if app_match is not None:
            return app_match

        # Unrecognized speech / casual conversation -> safely ignored
        return None

    def _parse_application_command(self, norm_text: str, raw_text: str) -> Optional[VoiceCommandMatch]:
        """
        Parses application opening voice intents (e.g. 'open vs code', 'launch chrome', 'open notepad').
        Resolves strictly against the ApplicationRegistry allowlist. Returns None if app is not registered.
        """
        m = re.match(r"^(?:open|launch|start)\s+(.+)$", norm_text)
        if m:
            target = m.group(1).strip()
            # Strip common filler words
            target_cleaned = re.sub(r"^(?:the|my)\s+", "", target)
            target_cleaned = re.sub(r"\s+(?:app|application|ide|browser|editor)$", "", target_cleaned).strip()

            app_def = self.app_registry.resolve(target_cleaned) or self.app_registry.resolve(target)
            if app_def:
                return VoiceCommandMatch(
                    intent_type=VoiceIntentType.REGISTERED_ACTION,
                    action_name="open_application",
                    params={"app_id": app_def.app_id},
                    matched_phrase=raw_text,
                    raw_text=raw_text
                )

        # 2. Check 'close <app>' or 'exit <app>' for allowlisted apps (e.g. 'close chrome', 'close vs code')
        m_close = re.match(r"^(?:close|exit)\s+(.+)$", norm_text)
        if m_close:
            target = m_close.group(1).strip()
            # If target is generic keyword, it's handled by lifecycle or action_commands
            generic_keywords = ("nexa", "tab", "current tab", "app", "application", "window", "active app", "active window", "current app", "current window", "this", "this app", "this window")
            if target not in generic_keywords:
                target_cleaned = re.sub(r"^(?:the|my)\s+", "", target)
                target_cleaned = re.sub(r"\s+(?:app|application|ide|browser|editor)$", "", target_cleaned).strip()
                app_def = self.app_registry.resolve(target_cleaned) or self.app_registry.resolve(target)
                if app_def:
                    return VoiceCommandMatch(
                        intent_type=VoiceIntentType.REGISTERED_ACTION,
                        action_name="close_app",
                        params={"target": app_def.app_id},
                        matched_phrase=raw_text,
                        raw_text=raw_text
                    )
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
            if match.action_name in ("volume_up", "volume_down", "set_volume"):
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
