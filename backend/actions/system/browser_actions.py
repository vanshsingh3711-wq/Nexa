import os
import time
from pathlib import Path

try:
    import pyautogui
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
    if pyautogui:
        print("System: TAKE SCREENSHOT")
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
            print(f"[Nexa] Screenshot direct save error ({e}), triggering Win+PrtScn")
            pyautogui.hotkey('win', 'printscreen')


def close_tab():
    if pyautogui:
        print("Browser: CLOSE TAB")
        pyautogui.hotkey('ctrl', 'w')

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
