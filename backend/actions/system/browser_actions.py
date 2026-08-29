import os
import time
import ctypes
from typing import Optional
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = False  # Avoid crashing when gesture moves mouse to corner (0, 0)
except ImportError:
    pyautogui = None

def browser_back():
    if pyautogui:
        print("Browser: BACK")
        pyautogui.hotkey('alt', 'left')

def browser_forward():
    if pyautogui:
        print("Browser: FORWARD")
        pyautogui.hotkey('alt', 'right')

def next_tab():
    if pyautogui:
        print("Browser: NEXT TAB")
        pyautogui.hotkey('ctrl', 'tab')

def prev_tab():
    if pyautogui:
        print("Browser: PREVIOUS TAB")
        pyautogui.hotkey('ctrl', 'shift', 'tab')

def zoom_in():
    if pyautogui:
        print("Browser/System: ZOOM IN")
        pyautogui.hotkey('ctrl', '+')

def zoom_out():
    if pyautogui:
        print("Browser/System: ZOOM OUT")
        pyautogui.hotkey('ctrl', '-')

def reset_zoom():
    if pyautogui:
        print("Browser/System: RESET ZOOM")
        pyautogui.hotkey('ctrl', '0')


def take_screenshot():
    r"""
    Captures a full-screen screenshot on Windows.
    1. Uses native Windows keyboard event (Win + PrtScn) which automatically saves to Pictures\Screenshots.
    2. Falls back to pyautogui.screenshot() / hotkeys if applicable.
    """
    print("System: TAKE SCREENSHOT")
    
    # 1. Trigger native Windows OS Win + PrintScreen (0x5B + 0x2C)
    try:
        VK_LWIN = 0x5B
        VK_SNAPSHOT = 0x2C
        KEYEVENTF_KEYUP = 0x0002

        user32 = ctypes.windll.user32
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(VK_SNAPSHOT, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(VK_SNAPSHOT, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        print("[Nexa] Screenshot captured via Windows Win+PrtScn (Saved to Pictures\\Screenshots)")
        return "screenshot_captured"
    except Exception as e:
        print(f"[Nexa] Native keybd_event error: {e}")

    # 2. Secondary fallback via PyAutoGUI if available
    if pyautogui:
        try:
            save_dir = Path.home() / "Pictures" / "Screenshots"
            save_dir.mkdir(parents=True, exist_ok=True)
            filename = f"nexa_screenshot_{int(time.time())}.png"
            filepath = save_dir / filename
            shot = pyautogui.screenshot()
            shot.save(str(filepath))
            print(f"[Nexa] Screenshot saved to: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"[Nexa] PyAutoGUI screenshot error: {e}")
            try:
                pyautogui.hotkey('win', 'printscreen')
            except Exception:
                pass


def close_tab():
    if pyautogui:
        print("Browser: CLOSE TAB")
        pyautogui.hotkey('ctrl', 'w')

def close_app(target: Optional[str] = "active"):
    """
    Closes the currently active foreground application window.
    Sends Windows WM_CLOSE to foreground window and triggers Alt + F4.
    """
    print(f"System: CLOSE APPLICATION (Target: {target or 'active'})")
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            WM_CLOSE = 0x0010
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    except Exception as e:
        print(f"[System] Error sending WM_CLOSE: {e}")

    if pyautogui:
        pyautogui.hotkey('alt', 'f4')
    return True

def refresh_page():
    if pyautogui:
        print("Browser: REFRESH PAGE")
        pyautogui.hotkey('ctrl', 'r')


def open_task_view():
    if pyautogui:
        print("System: OPEN TASK VIEW (Win + Tab)")
        pyautogui.hotkey('win', 'tab')

def select_next_window():
    if pyautogui:
        print("System: SELECT NEXT WINDOW")
        pyautogui.press('right')

def select_prev_window():
    if pyautogui:
        print("System: SELECT PREVIOUS WINDOW")
        pyautogui.press('left')

def confirm_selection():
    if pyautogui:
        print("System: CONFIRM WINDOW (Enter)")
        pyautogui.press('enter')
