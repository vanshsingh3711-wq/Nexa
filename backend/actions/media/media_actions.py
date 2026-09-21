import os
import sys

try:
    import pyautogui
except ImportError:
    pyautogui = None

def toggle_play_pause() -> bool:
    """
    Simulates a 'Media Play/Pause' keystroke using pyautogui for cross-platform compatibility.
    Returns True if the action was successfully triggered, False otherwise.
    """
    try:
        print("Media: TOGGLE PLAY / PAUSE")
        if os.name == 'posix' and sys.platform != 'darwin':
            # Use dbus for Linux
            import subprocess
            out = subprocess.check_output(
                ["dbus-send", "--session", "--dest=org.freedesktop.DBus", 
                 "--type=method_call", "--print-reply", "/org/freedesktop/DBus", 
                 "org.freedesktop.DBus.ListNames"], text=True
            )
            players = [line.split('"')[1] for line in out.splitlines() if "org.mpris.MediaPlayer2" in line]
            
            if players:
                for player in players:
                    subprocess.run([
                        "dbus-send", "--session", f"--dest={player}",
                        "--type=method_call", "/org/mpris/MediaPlayer2",
                        "org.mpris.MediaPlayer2.Player.PlayPause"
                    ], check=False)
                return True
            else:
                print("No MPRIS media players found.")
                return False
        else:
            if pyautogui:
                pyautogui.press('playpause')
                return True
            else:
                print("Error: pyautogui is not installed.")
                return False
    except Exception as e:
        print(f"Failed to trigger OS play/pause: {e}")
        return False

def media_play() -> bool:
    """Plays media stream."""
    return toggle_play_pause()

def media_pause() -> bool:
    """Pauses media stream."""
    return toggle_play_pause()

