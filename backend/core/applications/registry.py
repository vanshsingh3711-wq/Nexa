from typing import Dict, List, Optional
from core.applications.models import ApplicationDefinition, LaunchStrategyType

class ApplicationRegistry:
    """
    Registry of allowed applications permitted to be launched by Nexa.
    
    Security & Operational Guarantees:
    - Pure metadata & lookup repository (does NOT perform OS process launching).
    - Strict allowlist: Only explicitly registered applications are permitted.
    - Case-insensitive & trimmed alias resolution.
    - Fail-closed: Returns None on unregistered applications or ambiguous input.
    """
    def __init__(self):
        self._apps: Dict[str, ApplicationDefinition] = {}
        self._alias_map: Dict[str, str] = {}

    def register(self, app_def: ApplicationDefinition) -> None:
        """
        Registers an application definition in the registry.
        Raises ValueError if app_id or any alias collides with an existing registration.
        """
        if not isinstance(app_def, ApplicationDefinition):
            raise TypeError(f"Expected ApplicationDefinition, got {type(app_def).__name__}")

        app_id = app_def.app_id
        if app_id in self._apps:
            raise ValueError(f"Application with app_id '{app_id}' is already registered.")

        # Check alias collisions
        all_aliases = set(app_def.aliases)
        all_aliases.add(app_id)
        all_aliases.add(app_def.display_name.strip().lower())

        for alias in all_aliases:
            if alias in self._alias_map and self._alias_map[alias] != app_id:
                existing_id = self._alias_map[alias]
                raise ValueError(f"Alias '{alias}' conflicts with already registered app '{existing_id}'.")

        # Register app
        self._apps[app_id] = app_def
        for alias in all_aliases:
            self._alias_map[alias] = app_id

    def get(self, app_id: str) -> Optional[ApplicationDefinition]:
        """Exact lookup by unique app_id."""
        if not app_id:
            return None
        return self._apps.get(app_id.strip().lower())

    def resolve(self, name_or_alias: str) -> Optional[ApplicationDefinition]:
        """
        Resolves a user-provided name, spoken alias, or app_id to an ApplicationDefinition.
        Returns None if unrecognized (fail closed).
        """
        if not name_or_alias:
            return None
        cleaned = name_or_alias.strip().lower()
        if not cleaned:
            return None

        # 1. Check direct alias index
        resolved_id = self._alias_map.get(cleaned)
        if resolved_id:
            return self._apps.get(resolved_id)

        # 2. Check direct app_id match
        return self._apps.get(cleaned)

    def is_registered(self, app_id_or_alias: str) -> bool:
        """Returns True if the application or alias is registered in the allowlist."""
        return self.resolve(app_id_or_alias) is not None

    def list_applications(self) -> List[ApplicationDefinition]:
        """Returns a list of all registered application definitions."""
        return list(self._apps.values())


# Global singleton instance
_default_app_registry: Optional[ApplicationRegistry] = None

def get_default_application_registry() -> ApplicationRegistry:
    """Returns the pre-configured default ApplicationRegistry with the initial 6 allowlisted applications."""
    global _default_app_registry
    if _default_app_registry is None:
        registry = ApplicationRegistry()

        # 1. Google Chrome
        registry.register(ApplicationDefinition(
            app_id="chrome",
            display_name="Google Chrome",
            aliases=["chrome", "google chrome", "google chrome browser", "chrome browser"],
            strategy_type=LaunchStrategyType.DISCOVERABLE_EXECUTABLE,
            executable_candidates=[
                "chrome.exe",
                r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
                r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
                r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
            ],
            description="Google Chrome web browser."
        ))

        # 2. Brave Browser
        registry.register(ApplicationDefinition(
            app_id="brave",
            display_name="Brave Browser",
            aliases=["brave", "brave browser"],
            strategy_type=LaunchStrategyType.DISCOVERABLE_EXECUTABLE,
            executable_candidates=[
                "brave.exe",
                r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"
            ],
            description="Brave web browser."
        ))

        # 3. Visual Studio Code
        registry.register(ApplicationDefinition(
            app_id="vscode",
            display_name="Visual Studio Code",
            aliases=["vscode", "vs code", "visual studio code", "code"],
            strategy_type=LaunchStrategyType.DISCOVERABLE_EXECUTABLE,
            executable_candidates=[
                "code.cmd",
                "code.exe",
                r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
                r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
                r"%PROGRAMFILES(X86)%\Microsoft VS Code\Code.exe"
            ],
            description="Microsoft Visual Studio Code IDE."
        ))

        # 4. Google Antigravity
        registry.register(ApplicationDefinition(
            app_id="antigravity",
            display_name="Antigravity",
            aliases=["antigravity", "google antigravity", "agy"],
            strategy_type=LaunchStrategyType.DISCOVERABLE_EXECUTABLE,
            executable_candidates=[
                "antigravity.exe",
                "agy.cmd",
                "agy.exe",
                r"%LOCALAPPDATA%\Programs\Antigravity\Antigravity.exe",
                r"%APPDATA%\..\Local\Programs\Antigravity\Antigravity.exe"
            ],
            description="Google Antigravity Agentic IDE."
        ))

        # 5. Windows File Explorer
        registry.register(ApplicationDefinition(
            app_id="file_explorer",
            display_name="File Explorer",
            aliases=["file explorer", "explorer", "files", "my computer", "this pc", "folder", "folders", "file manager"],
            strategy_type=LaunchStrategyType.SHELL_TARGET,
            executable_candidates=[
                "explorer.exe",
                r"%WINDIR%\explorer.exe"
            ],
            description="Windows File Explorer."
        ))

        # 6. Windows Notepad
        registry.register(ApplicationDefinition(
            app_id="notepad",
            display_name="Notepad",
            aliases=["notepad", "text editor", "notes", "note pad"],
            strategy_type=LaunchStrategyType.SYSTEM_PATH,
            executable_candidates=[
                "notepad.exe",
                r"%WINDIR%\notepad.exe",
                r"%WINDIR%\System32\notepad.exe"
            ],
            description="Windows Notepad text editor."
        ))

        _default_app_registry = registry

    return _default_app_registry
