import os
import shutil
import subprocess
from typing import Optional, List

from core.applications.models import ApplicationDefinition, LaunchResult
from core.applications.registry import ApplicationRegistry, get_default_application_registry

class ApplicationLauncher:
    """
    Secure Application Launcher for Nexa.
    
    Responsibilities:
    1. Resolve validated app_id or alias using the ApplicationRegistry allowlist.
    2. Securely resolve executable paths from pre-configured candidate lists.
    3. Detect application availability without traversing arbitrary filesystem trees.
    4. Launch application process using strictly validated arguments (Zero shell=True).
    5. Return clear, structured LaunchResult objects.
    """
    def __init__(self, registry: Optional[ApplicationRegistry] = None):
        self.registry = registry if registry is not None else get_default_application_registry()

    def resolve_executable(self, app_def: ApplicationDefinition) -> Optional[str]:
        """
        Safely inspects the pre-configured candidate paths in the ApplicationDefinition.
        Returns the first validated executable path found on the system, or None if unavailable.
        """
        if not app_def or not app_def.executable_candidates:
            return None

        for candidate in app_def.executable_candidates:
            # Check if candidate has path separators or environment variables
            if ("\\" in candidate) or ("/" in candidate) or ("%" in candidate):
                expanded = os.path.expandvars(candidate)
                if os.path.isfile(expanded):
                    return os.path.abspath(expanded)
            else:
                # System PATH lookup (e.g. notepad.exe, explorer.exe, code.cmd)
                found = shutil.which(candidate)
                if found and os.path.isfile(found):
                    return os.path.abspath(found)

        return None

    def is_available(self, app_id_or_alias: str) -> bool:
        """
        Checks if an application is registered AND installed / available on this computer.
        """
        app_def = self.registry.resolve(app_id_or_alias)
        if app_def is None:
            return False
        return self.resolve_executable(app_def) is not None

    def launch(self, app_id_or_alias: str) -> LaunchResult:
        """
        Launches an allowlisted application by app_id or alias.
        Fails closed on unknown or unavailable applications.
        """
        # 1. Resolve Application in Registry
        app_def = self.registry.resolve(app_id_or_alias)
        if app_def is None:
            return LaunchResult(
                success=False,
                app_id=app_id_or_alias,
                display_name=app_id_or_alias,
                message=f"Application '{app_id_or_alias}' is not registered in the Application Registry.",
                error="UNREGISTERED_APPLICATION"
            )

        # 2. Resolve Verified Executable Path
        exe_path = self.resolve_executable(app_def)
        if exe_path is None:
            return LaunchResult(
                success=False,
                app_id=app_def.app_id,
                display_name=app_def.display_name,
                message=f"{app_def.display_name} is not installed or available on this computer.",
                error="APPLICATION_UNAVAILABLE"
            )

        # 3. Launch Process Safely
        try:
            cmd: List[str] = [exe_path] + list(app_def.default_args)
            print(f"[ApplicationLauncher] Launching: {app_def.display_name} ({exe_path})")
            
            # Use subprocess.Popen with shell=False and close_fds=True
            subprocess.Popen(
                cmd,
                shell=False,
                close_fds=True,
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
            )

            return LaunchResult(
                success=True,
                app_id=app_def.app_id,
                display_name=app_def.display_name,
                message=f"Successfully launched {app_def.display_name}."
            )
        except Exception as e:
            print(f"[ApplicationLauncher] Error launching {app_def.display_name}: {e}")
            return LaunchResult(
                success=False,
                app_id=app_def.app_id,
                display_name=app_def.display_name,
                message=f"Failed to launch {app_def.display_name}: {e}",
                error="LAUNCH_EXECUTION_ERROR"
            )


# Global singleton instance
_default_launcher: Optional[ApplicationLauncher] = None

def get_application_launcher() -> ApplicationLauncher:
    """Returns the default ApplicationLauncher instance."""
    global _default_launcher
    if _default_launcher is None:
        _default_launcher = ApplicationLauncher()
    return _default_launcher
