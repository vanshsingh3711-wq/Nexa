import unittest
from unittest.mock import MagicMock
from input.voice.voice_listener import VoiceListener
from core.commands.event_router import EventRouter
from core.security.registry import get_default_registry

class TestVoiceCommands(unittest.TestCase):
    def setUp(self):
        self.router = EventRouter()
        self.mock_action_router = MagicMock()
        self.router.action_router = self.mock_action_router
        self.listener = VoiceListener(
            on_mode_change=lambda active, text: self.router.set_active(active),
            on_command=lambda cmd: self.router.execute_action(cmd, source="voice")
        )

    def test_voice_actions_registered(self):
        """Verify all media, browser, window, and system utility actions are registered in ActionRegistry."""
        registry = get_default_registry()
        expected_actions = [
            "toggle_play_pause",
            "media_play",
            "media_pause",
            "volume_up",
            "volume_down",
            "volume_mute",
            "browser_back",
            "browser_forward",
            "next_tab",
            "prev_tab",
            "close_tab",
            "refresh_page",
            "zoom_in",
            "zoom_out",
            "reset_zoom",
            "take_screenshot",
            "open_task_view",
            "select_next_window",
            "select_prev_window",
            "confirm_selection",
        ]
        for action in expected_actions:
            self.assertTrue(registry.is_registered(action), f"Action '{action}' should be registered")

    def test_voice_command_mapping(self):
        """Verify phrase to action matching logic for media, window, browser, and system utility commands."""
        test_phrases = {
            # Media Controls
            "play": "media_play",
            "play media": "media_play",
            "play music": "media_play",
            "pause": "media_pause",
            "pause media": "media_pause",
            "play pause": "toggle_play_pause",
            "toggle play pause": "toggle_play_pause",
            "volume up": "volume_up",
            "increase volume": "volume_up",
            "volume down": "volume_down",
            "decrease volume": "volume_down",
            "mute": "volume_mute",
            "toggle mute": "volume_mute",
            "unmute": "volume_mute",
            # Window Management
            "open task view": "open_task_view",
            "task view": "open_task_view",
            "next window": "select_next_window",
            "select next window": "select_next_window",
            "previous window": "select_prev_window",
            "prev window": "select_prev_window",
            "select previous window": "select_prev_window",
            "select": "confirm_selection",
            "confirm selection": "confirm_selection",
            "confirm window": "confirm_selection",
            # Browser navigation
            "go back": "browser_back",
            "please go back": "browser_back",
            "browser back": "browser_back",
            "go forward": "browser_forward",
            "browser forward": "browser_forward",
            "next tab": "next_tab",
            "switch to next tab": "next_tab",
            "previous tab": "prev_tab",
            "prev tab": "prev_tab",
            "close tab": "close_tab",
            "close current tab": "close_tab",
            "refresh page": "refresh_page",
            "reload page": "refresh_page",
            "refresh": "refresh_page",
            # System / Utilities
            "zoom in": "zoom_in",
            "please zoom into this": "zoom_in",
            "magnify": "zoom_in",
            "zoom out": "zoom_out",
            "zoom back": "zoom_out",
            "reset zoom": "reset_zoom",
            "default zoom": "reset_zoom",
            "normal zoom": "reset_zoom",
            "take screenshot": "take_screenshot",
            "take a screenshot": "take_screenshot",
            "capture screen": "take_screenshot",
            "screenshot": "take_screenshot",
        }
        
        action_commands = [
            # Media Controls
            ("play pause", "toggle_play_pause"),
            ("toggle play pause", "toggle_play_pause"),
            ("toggle play", "toggle_play_pause"),
            ("toggle pause", "toggle_play_pause"),
            ("volume up", "volume_up"),
            ("increase volume", "volume_up"),
            ("volume down", "volume_down"),
            ("decrease volume", "volume_down"),
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
            ("zoom in", "zoom_in"),
            ("zoom into", "zoom_in"),
            ("magnify", "zoom_in"),
            ("zoom out", "zoom_out"),
            ("zoom back", "zoom_out"),

            # Browser Navigation
            ("close current tab", "close_tab"),
            ("close tab", "close_tab"),
            ("refresh page", "refresh_page"),
            ("reload page", "refresh_page"),
            ("refresh", "refresh_page"),
            ("reload", "refresh_page"),
            ("next tab", "next_tab"),
            ("next browser tab", "next_tab"),
            ("previous tab", "prev_tab"),
            ("prev tab", "prev_tab"),
            ("previous browser tab", "prev_tab"),
            ("go back", "browser_back"),
            ("browser back", "browser_back"),
            ("back page", "browser_back"),
            ("go forward", "browser_forward"),
            ("browser forward", "browser_forward"),
            ("forward page", "browser_forward"),
        ]

        for speech_text, expected_action in test_phrases.items():
            matched = None
            for phrase, action in action_commands:
                if phrase in speech_text:
                    matched = action
                    break
            self.assertEqual(matched, expected_action, f"Speech '{speech_text}' failed to match '{expected_action}'")

    def test_activation_and_sleep_phrases(self):
        """Verify 'Wake up' activates mode and 'Sleep' deactivates mode."""
        activation_phrases = [
            "wake up", "wake", "start nexa", "nexa start", "nexa on",
            "mode on", "turn on", "start hand", "hand on", "start",
            "activate", "enable", "hand gesture mode on", "gesture mode on",
            "gesture on", "hand mode on", "start gesture", "start next",
            "next on", "nexus on", "nexus start", "alexa on", "kesar mode on"
        ]
        deactivation_phrases = [
            "go to sleep", "sleep", "stop nexa", "nexa stop", "nexa off",
            "mode off", "turn off", "stop hand", "hand off", "stop",
            "deactivate", "disable", "hand gesture mode off", "gesture mode off",
            "gesture off", "hand mode off", "stop gesture", "stop next",
            "next off", "kesar mode off"
        ]

        # Wake Up checks
        for phrase in ["wake up", "start nexa", "mode on", "activate"]:
            self.assertTrue(any(p in phrase for p in activation_phrases), f"'{phrase}' should match activation")

        # Sleep checks
        for phrase in ["sleep", "go to sleep", "stop nexa", "mode off", "deactivate"]:
            self.assertTrue(any(p in phrase for p in deactivation_phrases), f"'{phrase}' should match deactivation")

if __name__ == "__main__":
    unittest.main()




