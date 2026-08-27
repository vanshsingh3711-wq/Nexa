import os
try:
    import pyautogui
except ImportError:
    pyautogui = None

def volume_up():
    if pyautogui: 
        print("Media: Volume UP")
        pyautogui.press('volumeup')

def volume_down():
    if pyautogui: 
        print("Media: Volume DOWN")
        pyautogui.press('volumedown')
