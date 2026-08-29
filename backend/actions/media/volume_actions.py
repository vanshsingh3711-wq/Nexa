import os
from typing import Optional

try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    AudioUtilities = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

def _get_volume_endpoint():
    """Helper to retrieve Windows Master Audio endpoint volume object."""
    if AudioUtilities is None:
        return None
    try:
        speakers = AudioUtilities.GetSpeakers()
        if speakers is not None:
            return speakers.EndpointVolume
    except Exception as e:
        print(f"[Volume] Error getting audio endpoint: {e}")
    return None

def get_current_volume() -> int:
    """Returns current system master volume percentage (0 to 100)."""
    vol = _get_volume_endpoint()
    if vol is not None:
        try:
            scalar = vol.GetMasterVolumeLevelScalar()
            return int(round(scalar * 100))
        except Exception as e:
            print(f"[Volume] Error reading volume level: {e}")
    return 50

def set_volume(level: int = 50) -> int:
    """Sets master volume directly to an exact target percentage (0 to 100)."""
    target = max(0, min(100, int(level)))
    print(f"Media: SET VOLUME TO {target}%")
    vol = _get_volume_endpoint()
    if vol is not None:
        try:
            vol.SetMasterVolumeLevelScalar(target / 100.0, None)
            print(f"[Volume] Master volume set to: {target}%")
            return target
        except Exception as e:
            print(f"[Volume] Error setting volume via pycaw: {e}")
    return target

def volume_up(step: int = 5) -> int:
    """Increments master volume by a specified step percentage (default 5%)."""
    step_val = max(1, min(100, int(step)))
    print(f"Media: Volume UP (+{step_val}%)")
    vol = _get_volume_endpoint()
    if vol is not None:
        try:
            current = vol.GetMasterVolumeLevelScalar()
            new_scalar = min(1.0, current + (step_val / 100.0))
            vol.SetMasterVolumeLevelScalar(new_scalar, None)
            new_pct = int(round(new_scalar * 100))
            print(f"[Volume] Master volume: {new_pct}%")
            return new_pct
        except Exception as e:
            print(f"[Volume] pycaw volume up error: {e}")

    if pyautogui:
        for _ in range(max(1, step_val // 2)):
            pyautogui.press('volumeup')
    return 0

def volume_down(step: int = 5) -> int:
    """Decrements master volume by a specified step percentage (default 5%)."""
    step_val = max(1, min(100, int(step)))
    print(f"Media: Volume DOWN (-{step_val}%)")
    vol = _get_volume_endpoint()
    if vol is not None:
        try:
            current = vol.GetMasterVolumeLevelScalar()
            new_scalar = max(0.0, current - (step_val / 100.0))
            vol.SetMasterVolumeLevelScalar(new_scalar, None)
            new_pct = int(round(new_scalar * 100))
            print(f"[Volume] Master volume: {new_pct}%")
            return new_pct
        except Exception as e:
            print(f"[Volume] pycaw volume down error: {e}")

    if pyautogui:
        for _ in range(max(1, step_val // 2)):
            pyautogui.press('volumedown')
    return 0

def volume_mute():
    """Toggles master volume mute."""
    print("Media: MUTE / UNMUTE")
    vol = _get_volume_endpoint()
    if vol is not None:
        try:
            is_muted = vol.GetMute()
            vol.SetMute(not is_muted, None)
            print(f"[Volume] Mute toggled: {'Muted' if not is_muted else 'Unmuted'}")
            return
        except Exception as e:
            print(f"[Volume] pycaw mute error: {e}")

    if pyautogui:
        pyautogui.press('volumemute')
