import os
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

def zoom_out():
    if pyautogui:
        print("Browser: ZOOM OUT")
        pyautogui.hotkey('ctrl', '-')

def close_tab():
    if pyautogui:
        print("Browser: CLOSE TAB")
        pyautogui.hotkey('ctrl', 'w')

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
