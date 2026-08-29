import time
import unittest

from input.voice.voice_guardrail import VoiceGuardrail, VoiceIntentType, VoiceCommandMatch

class TestVoiceGuardrail(unittest.TestCase):
    def setUp(self):
        self.guardrail = VoiceGuardrail(
            default_debounce_sec=0.5,
            volume_debounce_sec=0.2,
            global_min_interval_sec=0.1,
            max_words_in_command=7
        )

    def test_casual_conversation_is_ignored(self):
        """Verify casual speech, random phrases, and chatter return None (ignored)."""
        casual_phrases = [
            "khana hi nahin khai hai",
            "shivani khana hi nahin khai hai tu",
            "namaste closed",
            "hello how are you doing today",
            "what is the weather outside",
            "yesterday we went to the market",
            "tell me a joke please",
            "this is just random chatter in the room"
        ]
        for phrase in casual_phrases:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNone(match, f"Casual phrase '{phrase}' must be ignored as None")

    def test_accidental_substrings_do_not_trigger(self):
        """Verify embedded substrings like 'display' or 'playback' do not trigger 'play'."""
        sub_phrases = [
            "we should display the chart",
            "the playback has finished",
            "i am going to back up my files",
            "sleeping beauty",
        ]
        for phrase in sub_phrases:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNone(match, f"Phrase '{phrase}' must not trigger accidental substring command")

    def test_registered_lifecycle_commands_recognized(self):
        """Verify exact and alias lifecycle commands are correctly matched."""
        # Wake commands
        for phrase in ["wake up nexa", "wake nexa", "start nexa", "wake up nexon", "nexa wake"]:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match")
            self.assertEqual(match.intent_type, VoiceIntentType.LIFECYCLE_WAKE)

        # Close / Sleep commands
        for phrase in ["close nexa", "exit nexa", "go to sleep", "sleep", "nexa stop"]:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match")
            self.assertEqual(match.intent_type, VoiceIntentType.LIFECYCLE_CLOSE)

        # Gesture commands
        for phrase in ["enable gestures", "start gestures", "gesture mode on"]:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match")
            self.assertEqual(match.intent_type, VoiceIntentType.GESTURE_ENABLE)

        for phrase in ["disable gestures", "stop gestures", "gesture mode off"]:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match")
            self.assertEqual(match.intent_type, VoiceIntentType.GESTURE_DISABLE)

    def test_registered_desktop_actions_recognized(self):
        """Verify desktop action commands match appropriate action names."""
        test_cases = [
            ("play", "media_play"),
            ("pause", "media_pause"),
            ("play pause", "toggle_play_pause"),
            ("volume up", "volume_up"),
            ("increase volume", "volume_up"),
            ("volume down", "volume_down"),
            ("mute", "volume_mute"),
            ("open task view", "open_task_view"),
            ("next window", "select_next_window"),
            ("select", "confirm_selection"),
            ("take screenshot", "take_screenshot"),
            ("next tab", "next_tab"),
            ("previous tab", "prev_tab"),
            ("close tab", "close_tab"),
            ("refresh page", "refresh_page"),
            ("go back", "browser_back"),
            ("go forward", "browser_forward"),
            ("zoom in", "zoom_in"),
            ("zoom out", "zoom_out"),
            ("reset zoom", "reset_zoom"),
        ]
        for phrase, expected_action in test_cases:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match")
            self.assertEqual(match.intent_type, VoiceIntentType.REGISTERED_ACTION)
            self.assertEqual(match.action_name, expected_action)

    def test_precise_volume_commands(self):
        """Verify absolute target volume and delta step voice commands parse correctly with params."""
        # 1. Target absolute volume
        abs_cases = [
            ("volume down to 45", "set_volume", {"level": 45}),
            ("volume up to 80", "set_volume", {"level": 80}),
            ("set volume to 60", "set_volume", {"level": 60}),
            ("set volume 50 percent", "set_volume", {"level": 50}),
            ("volume to 25", "set_volume", {"level": 25}),
            ("volume 75 percent", "set_volume", {"level": 75}),
        ]
        for phrase, expected_act, expected_params in abs_cases:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match")
            self.assertEqual(match.action_name, expected_act)
            self.assertEqual(match.params, expected_params)

        # 2. Relative delta volume
        rel_cases = [
            ("volume up by 100", "volume_up", {"step": 100}),
            ("volume up by 20", "volume_up", {"step": 20}),
            ("increase volume by 15", "volume_up", {"step": 15}),
            ("volume down by 30", "volume_down", {"step": 30}),
            ("decrease volume by 25", "volume_down", {"step": 25}),
            ("volume up", "volume_up", {"step": 5}),
            ("volume down", "volume_down", {"step": 5}),
        ]
        for phrase, expected_act, expected_params in rel_cases:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match")
            self.assertEqual(match.action_name, expected_act)
            self.assertEqual(match.params, expected_params)

    def test_duplicate_command_prevention_and_debounce(self):
        """Verify identical commands in rapid succession are blocked by debounce guardrail."""
        match_wake = self.guardrail.parse_command("wake up nexa")
        
        # First execution allowed
        allowed1, reason1 = self.guardrail.should_execute(match_wake)
        self.assertTrue(allowed1)
        self.assertIsNone(reason1)

        # Immediate duplicate execution within 0.5s debounce blocked
        allowed2, reason2 = self.guardrail.should_execute(match_wake)
        self.assertFalse(allowed2)
        self.assertIn("Blocked duplicate command", reason2)

        # After debounce window expires, command is allowed again
        time.sleep(0.55)
        allowed3, reason3 = self.guardrail.should_execute(match_wake)
        self.assertTrue(allowed3)

    def test_rapid_fire_global_interval_protection(self):
        """Verify rapid-fire different commands within 0.1s are blocked."""
        match_play = self.guardrail.parse_command("play")
        match_pause = self.guardrail.parse_command("pause")

        allowed_play, _ = self.guardrail.should_execute(match_play)
        self.assertTrue(allowed_play)

        # Immediate different command within global_min_interval_sec (0.1s)
        allowed_pause, reason = self.guardrail.should_execute(match_pause)
        self.assertFalse(allowed_pause)
        self.assertIn("Rapid fire interval", reason)

        # After interval expires, command succeeds
        time.sleep(0.15)
        allowed_pause_later, _ = self.guardrail.should_execute(match_pause)
        self.assertTrue(allowed_pause_later)

if __name__ == "__main__":
    unittest.main()
