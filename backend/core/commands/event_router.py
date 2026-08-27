import time
from actions.mouse.mouse_actions import move_mouse, left_click
from actions.media.media_actions import toggle_play_pause
from actions.media.volume_actions import volume_up, volume_down
from actions.system.browser_actions import (
    browser_back, browser_forward, next_tab, prev_tab, zoom_out, close_tab,
    open_task_view, select_next_window, select_prev_window, confirm_selection
)
from input.gesture.swipe_detector import SwipeDetector

class EventRouter:
    def __init__(self):
        self.is_active = False
        
        # Dedicated debounce timestamps for each action type
        self.last_toggle_time = 0.0
        self.palm_toggle_locked = False
        self.last_click_time = 0.0
        self.last_media_time = 0.0
        self.last_volume_time = 0.0
        self.last_swipe_time = 0.0
        
        # Swipe detector initialized with sensitive displacement threshold
        self.swipe_detector = SwipeDetector(history_size=7, swipe_threshold=0.12)
        
    def set_active(self, is_active: bool):
        """Enable or disable gesture control mode (e.g. via voice command)."""
        self.is_active = is_active
        status = "ACTIVATED (Controlling PC)" if self.is_active else "DEACTIVATED (Idle)"
        print(f"\n{'='*40}\n[Nexa] GESTURE MODE {status}\n{'='*40}\n")
        if not is_active:
            self.swipe_detector.clear()

    def dispatch(self, gesture_data, previous_gesture_data):
        gesture = gesture_data.get("gesture", "None")
        previous_gesture = previous_gesture_data.get("gesture", "None")
        current_time = time.time()
            
        # If we are in Idle mode, do not process any controls
        if not self.is_active:
            self.swipe_detector.clear()
            return
            
        # 2. Mouse Controls (Cursor tracking & Pinch clicking)
        if gesture == "Index":
            move_mouse(gesture_data["cursor_x"], gesture_data["cursor_y"])
            
        elif gesture == "Pinch":
            # Continue tracking cursor during pinch
            move_mouse(gesture_data["cursor_x"], gesture_data["cursor_y"])
            # Trigger click on first pinch transition or after debounce
            if previous_gesture != "Pinch" and (current_time - self.last_click_time > 0.4):
                left_click()
                self.last_click_time = current_time
                
        # 3. Media Controls (Closed Fist = Toggle Play/Pause)
        elif gesture == "Closed Fist" and previous_gesture != "Closed Fist":
            if current_time - self.last_media_time > 1.2:
                toggle_play_pause()
                self.last_media_time = current_time
                
        # 4. Volume Controls (Thumb Up = Vol+, Thumb Down = Vol-)
        elif gesture == "Thumb Up":
            # Allow rapid repeated tapping or continuous slow increment (every 0.35s)
            if (previous_gesture != "Thumb Up") or (current_time - self.last_volume_time > 0.35):
                volume_up()
                self.last_volume_time = current_time
                
        elif gesture == "Thumb Down":
            if (previous_gesture != "Thumb Down") or (current_time - self.last_volume_time > 0.35):
                volume_down()
                self.last_volume_time = current_time
                
        # 5. Swipe / Navigation Controls
        # A. Open Palm: Right -> Forward, Left -> Back, Down -> Close Tab, Up -> Open Task View
        if gesture == "Open Palm":
            if current_time - self.last_swipe_time > 0.8:
                swipe_dir = self.swipe_detector.process(gesture_data["cursor_x"], gesture_data["cursor_y"])
                if swipe_dir:
                    print(f"\n--- OPEN PALM {swipe_dir.upper()} DETECTED ---\n")
                    self.last_swipe_time = current_time
                    if swipe_dir == "Swipe Up":
                        open_task_view()
                    elif swipe_dir == "Swipe Right":
                        browser_forward()
                    elif swipe_dir == "Swipe Left":
                        browser_back()
                    elif swipe_dir == "Swipe Down":
                        close_tab()
                        
        # B. Peace Sign: Helper to select tabs/windows: Right -> Next Window, Left -> Prev Window, Down -> Confirm (Enter), Up -> Task View
        elif gesture == "Peace":
            if current_time - self.last_swipe_time > 0.6:
                swipe_dir = self.swipe_detector.process(gesture_data["cursor_x"], gesture_data["cursor_y"])
                if swipe_dir:
                    print(f"\n--- PEACE {swipe_dir.upper()} DETECTED ---\n")
                    self.last_swipe_time = current_time
                    if swipe_dir == "Swipe Right":
                        select_next_window()
                    elif swipe_dir == "Swipe Left":
                        select_prev_window()
                    elif swipe_dir == "Swipe Down":
                        confirm_selection()
                    elif swipe_dir == "Swipe Up":
                        open_task_view()
        else:
            # Clear swipe buffer immediately when not in Open Palm / Peace gesture
            self.swipe_detector.clear()

