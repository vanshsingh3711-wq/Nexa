import os

try:
    import pyautogui
except ImportError:
    pyautogui = None

def toggle_play_pause() -> bool:
    """
    Simulates a 'Media Play/Pause' keystroke using pyautogui for maximum compatibility.
    Returns True if the action was successfully triggered, False otherwise.
    """
    if os.name != 'nt':
        print("Error: toggle_play_pause is only supported on Windows.")
        return False
        
    if pyautogui is None:
        print("Error: pyautogui is not installed. Please run: pip install pyautogui")
        return False
        
    try:
        # pyautogui automatically handles the complex Windows SendInput structures,
        # scan codes, and extended key flags for media keys.
        pyautogui.press('playpause')
        return True
    except Exception as e:
        print(f"Failed to trigger OS play/pause: {e}")
        return False
