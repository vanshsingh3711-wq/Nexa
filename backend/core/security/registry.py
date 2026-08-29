from typing import Dict, Optional, Type, Callable, Any
from pydantic import BaseModel
from core.security.models import (
    RiskLevel,
    EmptyParams,
    OpenApplicationParams,
    VolumeSetParams,
    VolumeAdjustParams,
    MouseMoveParams,
    ScrollParams,
    AppTargetParams,
    FileTargetParams,
)
from core.applications.launcher import get_application_launcher
from actions.mouse.mouse_actions import move_mouse, left_click, double_click, scroll
from actions.media.media_actions import toggle_play_pause, media_play, media_pause
from actions.media.volume_actions import volume_up, volume_down, volume_mute, set_volume
from actions.system.browser_actions import (
    browser_back, browser_forward, next_tab, prev_tab,
    zoom_in, zoom_out, reset_zoom, take_screenshot,
    close_tab, close_app, refresh_page, open_task_view, select_next_window, select_prev_window, confirm_selection
)




class ActionDefinition(BaseModel):
    """
    Source of truth for an action's contract, schema, default risk, and handler reference.
    Note: The Policy Checker reads metadata from this definition and NEVER invokes the handler.
    """
    model_config = {"arbitrary_types_allowed": True}

    name: str
    description: str
    param_schema: Type[BaseModel] = EmptyParams
    default_risk: RiskLevel = RiskLevel.LOW
    handler: Optional[Callable[..., Any]] = None
    failure_behavior: str = "fail_closed"

class ActionRegistry:
    """
    Centralized repository of all registered desktop actions.
    Ensures that only authorized, documented actions with known schemas can be processed.
    """
    def __init__(self):
        self._actions: Dict[str, ActionDefinition] = {}

    def register(self, definition: ActionDefinition) -> None:
        if definition.name in self._actions:
            raise ValueError(f"Action '{definition.name}' is already registered.")
        self._actions[definition.name] = definition

    def get(self, name: str) -> Optional[ActionDefinition]:
        return self._actions.get(name)

    def is_registered(self, name: str) -> bool:
        return name in self._actions

    def list_actions(self) -> Dict[str, ActionDefinition]:
        return dict(self._actions)

def create_default_registry() -> ActionRegistry:
    """Initializes and registers all standard Nexa actions."""
    registry = ActionRegistry()

    # 1. Mouse Actions (LOW risk)
    registry.register(ActionDefinition(
        name="move_mouse",
        description="Moves mouse cursor to normalized screen coordinates (x, y)",
        param_schema=MouseMoveParams,
        default_risk=RiskLevel.LOW,
        handler=move_mouse,
    ))
    registry.register(ActionDefinition(
        name="left_click",
        description="Performs mouse left click at current cursor position",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=left_click,
    ))
    registry.register(ActionDefinition(
        name="double_click",
        description="Performs mouse double click at current cursor position",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=double_click,
    ))
    registry.register(ActionDefinition(
        name="scroll",
        description="Performs vertical mouse wheel scroll",
        param_schema=ScrollParams,
        default_risk=RiskLevel.LOW,
        handler=scroll,
    ))

    # 2. Media Actions (LOW risk)
    registry.register(ActionDefinition(
        name="toggle_play_pause",
        description="Toggles system media playback (Play/Pause)",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=toggle_play_pause,
    ))
    registry.register(ActionDefinition(
        name="media_play",
        description="Plays system media playback",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=media_play,
    ))
    registry.register(ActionDefinition(
        name="media_pause",
        description="Pauses system media playback",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=media_pause,
    ))
    registry.register(ActionDefinition(
        name="volume_up",
        description="Increments system audio volume",
        param_schema=VolumeAdjustParams,
        default_risk=RiskLevel.LOW,
        handler=volume_up,
    ))
    registry.register(ActionDefinition(
        name="volume_down",
        description="Decrements system audio volume",
        param_schema=VolumeAdjustParams,
        default_risk=RiskLevel.LOW,
        handler=volume_down,
    ))
    registry.register(ActionDefinition(
        name="set_volume",
        description="Sets system audio volume to a specific target level (0-100)",
        param_schema=VolumeSetParams,
        default_risk=RiskLevel.LOW,
        handler=set_volume,
    ))
    registry.register(ActionDefinition(
        name="volume_mute",
        description="Toggles system audio mute / unmute",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=volume_mute,
    ))


    # 3. Browser & Navigation Actions (LOW / MEDIUM risk)
    registry.register(ActionDefinition(
        name="browser_back",
        description="Navigates to previous web page in browser history",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=browser_back,
    ))
    registry.register(ActionDefinition(
        name="browser_forward",
        description="Navigates to next web page in browser history",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=browser_forward,
    ))
    registry.register(ActionDefinition(
        name="next_tab",
        description="Switches to next browser tab",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=next_tab,
    ))
    registry.register(ActionDefinition(
        name="prev_tab",
        description="Switches to previous browser tab",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=prev_tab,
    ))
    registry.register(ActionDefinition(
        name="zoom_in",
        description="Increases zoom level in browser or active app",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=zoom_in,
    ))
    registry.register(ActionDefinition(
        name="zoom_out",
        description="Decreases zoom level in browser or active app",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=zoom_out,
    ))
    registry.register(ActionDefinition(
        name="reset_zoom",
        description="Resets zoom level to default (100%) in browser or active app",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=reset_zoom,
    ))
    registry.register(ActionDefinition(
        name="take_screenshot",
        description="Captures and saves a full screen screenshot to Pictures/Screenshots",
        param_schema=EmptyParams,
        default_risk=RiskLevel.MEDIUM,
        handler=take_screenshot,
    ))
    registry.register(ActionDefinition(
        name="open_task_view",
        description="Opens Windows Task View / Window Switcher",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=open_task_view,
    ))
    registry.register(ActionDefinition(
        name="select_next_window",
        description="Navigates selection to next window in Task View",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=select_next_window,
    ))
    registry.register(ActionDefinition(
        name="select_prev_window",
        description="Navigates selection to previous window in Task View",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=select_prev_window,
    ))
    registry.register(ActionDefinition(
        name="confirm_selection",
        description="Confirms and activates selected window in Task View",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=confirm_selection,
    ))
    registry.register(ActionDefinition(
        name="close_tab",
        description="Closes the active browser tab",
        param_schema=EmptyParams,
        default_risk=RiskLevel.MEDIUM,
        handler=close_tab,
    ))
    registry.register(ActionDefinition(
        name="refresh_page",
        description="Refreshes or reloads the active browser web page",
        param_schema=EmptyParams,
        default_risk=RiskLevel.LOW,
        handler=refresh_page,
    ))



    def _handle_open_application(app_id: str) -> Dict[str, Any]:
        launcher = get_application_launcher()
        res = launcher.launch(app_id)
        return res.model_dump()

    registry.register(ActionDefinition(
        name="open_application",
        description="Securely launches an allowlisted desktop application by app_id or alias",
        param_schema=OpenApplicationParams,
        default_risk=RiskLevel.MEDIUM,
        handler=_handle_open_application,
    ))

    # 4. Extended Example Actions for High-Risk & Target Operations
    registry.register(ActionDefinition(
        name="close_app",
        description="Closes the active or specified application window (Requires confirmation)",
        param_schema=AppTargetParams,
        default_risk=RiskLevel.HIGH,
        handler=close_app,
    ))
    registry.register(ActionDefinition(
        name="delete_file",
        description="Deletes a file at the specified path (Requires confirmation)",
        param_schema=FileTargetParams,
        default_risk=RiskLevel.HIGH,
        handler=None,
    ))

    return registry

_default_registry: Optional[ActionRegistry] = None

def get_default_registry() -> ActionRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = create_default_registry()
    return _default_registry
