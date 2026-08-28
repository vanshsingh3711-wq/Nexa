import os

try:
    import pyautogui
except ImportError:
    pyautogui = None

def toggle_play_pause() -> bool:
    """
    Simulates a 'Media Play/Pause' keystroke using pyautogui for cross-platform compatibility.
    Returns True if the action was successfully triggered, False otherwise.
    """
    if pyautogui is None:
        print("Error: pyautogui is not installed. Please run: pip install pyautogui")
        return False
        
    try:
        pyautogui.press('playpause')
        return True
    except Exception as e:
        print(f"Failed to trigger OS play/pause: {e}")
        return False
