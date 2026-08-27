import os
try:
    import pyautogui
    # Disable fail-safe during testing to prevent crashes when touching screen corners
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

def move_mouse(norm_x, norm_y):
    if not pyautogui: return
    screen_width, screen_height = pyautogui.size()
    
    # Map normalized coordinates (0.0 to 1.0) to screen size
    target_x = int(norm_x * screen_width)
    target_y = int(norm_y * screen_height)
    
    # Clamp values to screen bounds to be safe
    target_x = max(0, min(screen_width - 1, target_x))
    target_y = max(0, min(screen_height - 1, target_y))
    
    pyautogui.moveTo(target_x, target_y)

def left_click():
    if pyautogui: 
        print("Mouse: Left Click!")
        pyautogui.click()

def double_click():
    if pyautogui: pyautogui.doubleClick()

def scroll(amount):
    if pyautogui: pyautogui.scroll(amount)
