import unittest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from core.applications.models import ApplicationDefinition, LaunchStrategyType, LaunchResult
from core.applications.registry import ApplicationRegistry, get_default_application_registry
from core.applications.launcher import ApplicationLauncher
from core.security.models import (
    OpenApplicationParams,
    StructuredActionRequest,
    RiskLevel,
    PolicyDecision,
)
from core.security.registry import get_default_registry
from core.security.policy_checker import PolicyChecker
from core.commands.action_router import ActionRouter
from input.voice.voice_guardrail import VoiceGuardrail, VoiceIntentType

class TestApplicationRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = get_default_application_registry()

    def test_registered_apps_exist(self):
        """Verify the 6 initial allowlisted apps exist in default registry."""
        initial_apps = ["chrome", "brave", "vscode", "antigravity", "file_explorer", "notepad"]
        for app_id in initial_apps:
            app = self.registry.get(app_id)
            self.assertIsNotNone(app, f"App '{app_id}' should be registered")
            self.assertEqual(app.app_id, app_id)

    def test_exact_app_id_resolves(self):
        """Verify exact app_id lookup."""
        app = self.registry.resolve("vscode")
        self.assertIsNotNone(app)
        self.assertEqual(app.app_id, "vscode")
        self.assertEqual(app.display_name, "Visual Studio Code")

    def test_alias_resolves_correctly(self):
        """Verify various registered aliases resolve to expected app."""
        test_cases = [
            ("vs code", "vscode"),
            ("Visual Studio Code", "vscode"),
            ("code", "vscode"),
            ("google chrome", "chrome"),
            ("chrome browser", "chrome"),
            ("brave browser", "brave"),
            ("file explorer", "file_explorer"),
            ("explorer", "file_explorer"),
            ("files", "file_explorer"),
            ("my computer", "file_explorer"),
            ("text editor", "notepad"),
            ("note pad", "notepad"),
            ("google antigravity", "antigravity"),
            ("agy", "antigravity"),
        ]
        for alias, expected_id in test_cases:
            app = self.registry.resolve(alias)
            self.assertIsNotNone(app, f"Alias '{alias}' should resolve to '{expected_id}'")
            self.assertEqual(app.app_id, expected_id)

    def test_case_insensitivity_and_whitespace(self):
        """Verify case insensitivity and surrounding whitespace handling."""
        variations = [
            "  VS CODE  ",
            "vIsUaL StUdIo cOdE",
            "   ChRoMe   ",
            "\tNotepad\n",
            "   FILE EXPLORER   "
        ]
        for v in variations:
            app = self.registry.resolve(v)
            self.assertIsNotNone(app, f"Variation '{v}' should resolve")

    def test_unknown_app_returns_none(self):
        """Verify unregistered apps fail closed and return None."""
        unknown_apps = ["spotify", "discord", "steam", "calc.exe", "powershell", "malicious_app", ""]
        for unk in unknown_apps:
            self.assertIsNone(self.registry.resolve(unk))

    def test_duplicate_app_registration_rejected(self):
        """Verify registering duplicate app_id or conflicting alias raises ValueError."""
        custom_registry = ApplicationRegistry()
        app1 = ApplicationDefinition(
            app_id="testapp",
            display_name="Test App",
            aliases=["testy"],
            executable_candidates=["testapp.exe"]
        )
        custom_registry.register(app1)

        # Duplicate app_id
        with self.assertRaises(ValueError):
            custom_registry.register(app1)

        # Conflicting alias
        app2 = ApplicationDefinition(
            app_id="otherapp",
            display_name="Other App",
            aliases=["testy"],
            executable_candidates=["other.exe"]
        )
        with self.assertRaises(ValueError):
            custom_registry.register(app2)


class TestOpenApplicationValidation(unittest.TestCase):
    def test_valid_open_app_params(self):
        """Verify valid app_id is accepted."""
        params = OpenApplicationParams(app_id="vscode")
        self.assertEqual(params.app_id, "vscode")

    def test_blank_app_id_rejected(self):
        """Verify empty or blank app_id is rejected by schema validator."""
        with self.assertRaises(ValidationError):
            OpenApplicationParams(app_id="")

    def test_extra_parameters_rejected(self):
        """Verify unexpected extra keys are rejected (strict extra='forbid')."""
        with self.assertRaises(ValidationError):
            OpenApplicationParams.model_validate({"app_id": "vscode", "extra_key": "injected"})

    def test_arbitrary_path_or_command_parameters_rejected(self):
        """Verify attempts to pass arbitrary 'path' or 'command' are rejected by the schema."""
        with self.assertRaises(ValidationError):
            OpenApplicationParams.model_validate({"path": "C:\\Windows\\System32\\cmd.exe"})

        with self.assertRaises(ValidationError):
            OpenApplicationParams.model_validate({"command": "powershell -Command calc"})


class TestApplicationLauncher(unittest.TestCase):
    def setUp(self):
        self.launcher = ApplicationLauncher()

    def test_unknown_app_cannot_launch(self):
        """Verify unknown application returns failed LaunchResult."""
        result = self.launcher.launch("non_existent_app_123")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "UNREGISTERED_APPLICATION")
        self.assertIn("not registered", result.message)

    def test_unavailable_app_returns_safe_failure(self):
        """Verify registered app with nonexistent executable returns safe failure without crashing."""
        custom_registry = ApplicationRegistry()
        custom_registry.register(ApplicationDefinition(
            app_id="phantom_app",
            display_name="Phantom App",
            aliases=["phantom"],
            executable_candidates=[r"C:\NonExistentDirectory987\phantom.exe"]
        ))
        launcher = ApplicationLauncher(registry=custom_registry)
        
        self.assertFalse(launcher.is_available("phantom_app"))
        result = launcher.launch("phantom_app")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "APPLICATION_UNAVAILABLE")
        self.assertIn("not installed or available", result.message)

    @patch("subprocess.Popen")
    def test_registered_app_launches_safely(self, mock_popen):
        """Verify registered app uses safe subprocess.Popen with shell=False."""
        mock_popen.return_value = MagicMock()
        
        # Test launching notepad (guaranteed available on Windows)
        result = self.launcher.launch("notepad")
        self.assertTrue(result.success)
        self.assertEqual(result.app_id, "notepad")
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        self.assertEqual(kwargs.get("shell"), False)
        self.assertTrue(kwargs.get("close_fds"))


class TestSecurityIntegration(unittest.TestCase):
    def setUp(self):
        self.action_registry = get_default_registry()
        self.policy_checker = PolicyChecker(registry=self.action_registry)
        self.router = ActionRouter(registry=self.action_registry, policy_checker=self.policy_checker)

    def test_open_application_action_registered(self):
        """Verify open_application is registered in the ActionRegistry with MEDIUM risk."""
        self.assertTrue(self.action_registry.is_registered("open_application"))
        action_def = self.action_registry.get("open_application")
        self.assertEqual(action_def.default_risk, RiskLevel.MEDIUM)
        self.assertEqual(action_def.param_schema, OpenApplicationParams)

    def test_policy_checker_authorizes_valid_request(self):
        """Verify PolicyChecker returns ALLOW for valid open_application request."""
        req = StructuredActionRequest(
            action="open_application",
            params={"app_id": "vscode"},
            source="voice"
        )
        decision_result = self.policy_checker.evaluate(req)
        self.assertEqual(decision_result.decision, PolicyDecision.ALLOW)
        self.assertEqual(decision_result.risk_level, RiskLevel.MEDIUM)

    def test_policy_checker_denies_invalid_params(self):
        """Verify PolicyChecker returns DENY when invalid parameters are supplied."""
        req = StructuredActionRequest(
            action="open_application",
            params={"path": "C:\\danger.exe"},
            source="voice"
        )
        decision_result = self.policy_checker.evaluate(req)
        self.assertEqual(decision_result.decision, PolicyDecision.DENY)

    @patch("subprocess.Popen")
    def test_action_router_executes_authorized_app_launch(self, mock_popen):
        """Verify ActionRouter dispatches to open_application handler when authorized."""
        mock_popen.return_value = MagicMock()
        req = StructuredActionRequest(
            action="open_application",
            params={"app_id": "notepad"},
            source="voice"
        )
        decision, output = self.router.dispatch(req)
        self.assertEqual(decision.decision, PolicyDecision.ALLOW)
        self.assertIsNotNone(output)
        self.assertTrue(output.get("success"))
        self.assertEqual(output.get("app_id"), "notepad")


    @patch("actions.system.browser_actions.pyautogui")
    def test_action_router_executes_close_app(self, mock_pyautogui):
        """Verify ActionRouter dispatches close_app successfully."""
        req = StructuredActionRequest(
            action="close_app",
            params={"target": "active"},
            source="voice"
        )
        decision, output = self.router.dispatch(req)
        self.assertEqual(decision.decision, PolicyDecision.ALLOW)
        self.assertTrue(output)


class TestVoiceGuardrailAppCommands(unittest.TestCase):
    def setUp(self):
        self.guardrail = VoiceGuardrail()

    def test_voice_commands_parse_allowlisted_apps(self):
        """Verify natural voice phrases match open_application with resolved app_id."""
        test_cases = [
            ("open vs code", "vscode"),
            ("open vscode", "vscode"),
            ("launch visual studio code", "vscode"),
            ("open chrome", "chrome"),
            ("launch google chrome", "chrome"),
            ("open brave browser", "brave"),
            ("open file explorer", "file_explorer"),
            ("open explorer", "file_explorer"),
            ("open notepad", "notepad"),
            ("launch notepad", "notepad"),
            ("open antigravity", "antigravity"),
            ("launch antigravity", "antigravity"),
        ]
        for phrase, expected_app_id in test_cases:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match")
            self.assertEqual(match.intent_type, VoiceIntentType.REGISTERED_ACTION)
            self.assertEqual(match.action_name, "open_application")
            self.assertEqual(match.params, {"app_id": expected_app_id})

    def test_voice_commands_parse_close_active_app(self):
        """Verify voice phrases to close active application and window match close_app."""
        close_phrases = [
            "close app",
            "close active app",
            "close current app",
            "close application",
            "close active application",
            "close window",
            "close active window",
            "close current window",
            "close this window",
            "close this app",
            "close this",
            "exit app",
            "exit window",
        ]
        for phrase in close_phrases:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match close_app")
            self.assertEqual(match.intent_type, VoiceIntentType.REGISTERED_ACTION)
            self.assertEqual(match.action_name, "close_app")

    def test_voice_commands_parse_close_named_app(self):
        """Verify 'close <app>' for allowlisted apps matches close_app with target param."""
        named_cases = [
            ("close chrome", "chrome"),
            ("close vs code", "vscode"),
            ("close notepad", "notepad"),
            ("close brave", "brave"),
            ("close file explorer", "file_explorer"),
        ]
        for phrase, expected_target in named_cases:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNotNone(match, f"Phrase '{phrase}' should match close_app for '{expected_target}'")
            self.assertEqual(match.intent_type, VoiceIntentType.REGISTERED_ACTION)
            self.assertEqual(match.action_name, "close_app")
            self.assertEqual(match.params.get("target"), expected_target)

    def test_unregistered_app_voice_commands_ignored(self):
        """Verify requests to open unregistered apps are ignored by guardrail."""
        unregistered = [
            "open spotify",
            "launch discord",
            "start steam",
            "open powershell",
            "open cmd",
            "open random software"
        ]
        for phrase in unregistered:
            match = self.guardrail.parse_command(phrase)
            self.assertIsNone(match, f"Phrase '{phrase}' must be ignored")

if __name__ == "__main__":
    unittest.main()
