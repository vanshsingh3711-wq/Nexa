from typing import Dict, Optional

# Centralized spoken feedback messages for Nexa Lifecycle Events
# Normal desktop actions are completely silent.
LIFECYCLE_FEEDBACK: Dict[str, str] = {
    "nexa_activated": "Welcome, Vansh. How can I help you?",
    "nexa_closing": "Alright, closing Nexa.",
    "gestures_enabled": "Gesture control enabled.",
    "gestures_disabled": "Gesture control disabled.",
}

# Explicit aliases for convenience
NEXA_ACTIVATED_MESSAGE = LIFECYCLE_FEEDBACK["nexa_activated"]
NEXA_CLOSING_MESSAGE = LIFECYCLE_FEEDBACK["nexa_closing"]
GESTURES_ENABLED_MESSAGE = LIFECYCLE_FEEDBACK["gestures_enabled"]
GESTURES_DISABLED_MESSAGE = LIFECYCLE_FEEDBACK["gestures_disabled"]

# Backward compatibility constants
MODE_ACTIVE_MESSAGE = NEXA_ACTIVATED_MESSAGE
MODE_IDLE_MESSAGE = NEXA_CLOSING_MESSAGE

# Normal actions must remain completely silent
ACTION_FEEDBACK: Dict[str, str] = {}
SILENT_ACTIONS = set()

def get_action_message(action: str) -> Optional[str]:
    """
    Normal desktop actions are completely silent.
    Returns None for all action names.
    """
    return None
