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
        
        # Tab / Window selection session tracking
        self.tab_selection_mode = False
        self.last_tab_selection_time = 0.0
        self.tab_selection_timeout = 6.0 # seconds before automatically reverting to normal mouse mode
        
        # Dedicated swipe detectors initialized with sensitive displacement threshold
        self.palm_swipe_detector = SwipeDetector(history_size=15, swipe_threshold=0.08, time_window=0.5)
        self.three_finger_swipe_detector = SwipeDetector(history_size=15, swipe_threshold=0.075, time_window=0.5)
        self.peace_swipe_detector = SwipeDetector(history_size=15, swipe_threshold=0.075, time_window=0.5)
        self.swipe_detector = self.palm_swipe_detector # Backward compatibility
        
    def set_active(self, is_active: bool):
        """Enable or disable gesture control mode (e.g. via voice command)."""
        self.is_active = is_active
        self.tab_selection_mode = False
        status = "ACTIVATED (Controlling PC)" if self.is_active else "DEACTIVATED (Idle)"
        print(f"\n{'='*40}\n[Nexa] GESTURE MODE {status}\n{'='*40}\n")
        if not is_active:
            self.palm_swipe_detector.clear()
            self.three_finger_swipe_detector.clear()
            self.peace_swipe_detector.clear()

    def dispatch(self, gesture_data, previous_gesture_data):
        gesture = gesture_data.get("gesture", "None")
        previous_gesture = previous_gesture_data.get("gesture", "None")
        current_time = time.time()
            
        # If we are in Idle mode, do not process any controls
        if not self.is_active:
            self.palm_swipe_detector.clear()
            self.three_finger_swipe_detector.clear()
            self.peace_swipe_detector.clear()
            return
            
        # Check tab selection mode expiration
        if self.tab_selection_mode and (current_time - self.last_tab_selection_time > self.tab_selection_timeout):
            self.tab_selection_mode = False
            
        # 2. Mouse Controls & Pinch Entering / Clicking
        if gesture == "Index":
            move_mouse(gesture_data["cursor_x"], gesture_data["cursor_y"])
            
        elif gesture == "Pinch":
            if self.tab_selection_mode:
                # In tab/window selection mode: Pinch confirms and opens the selected tab (Enter)
                if previous_gesture != "Pinch" and (current_time - self.last_click_time > 0.4):
                    print("\n[Nexa] PINCH -> CONFIRM TAB/WINDOW SELECTION (Enter)\n")
                    confirm_selection()
                    self.tab_selection_mode = False
                    self.last_click_time = current_time
            else:
                # Normal mode: Continue tracking cursor and perform Left Click
                move_mouse(gesture_data["cursor_x"], gesture_data["cursor_y"])
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
        # A. Open Palm: Swipe Up -> Open Task View / Tab Switcher (Win + Tab)
        if gesture == "Open Palm":
            if current_time - self.last_swipe_time > 0.45:
                swipe_dir = self.palm_swipe_detector.process(gesture_data["cursor_x"], gesture_data["cursor_y"])
                if swipe_dir == "Swipe Up":
                    print(f"\n--- OPEN PALM SWIPE UP (OPEN TASK VIEW) ---\n")
                    self.last_swipe_time = current_time
                    open_task_view()
                    self.tab_selection_mode = True
                    self.last_tab_selection_time = current_time
                    
        # B. Three Fingers: Swipe Left -> Browser Back, Swipe Right -> Browser Forward
        elif gesture == "Three Fingers":
            if current_time - self.last_swipe_time > 0.40:
                swipe_dir = self.three_finger_swipe_detector.process(gesture_data["cursor_x"], gesture_data["cursor_y"])
                if swipe_dir:
                    if swipe_dir == "Swipe Left":
                        print(f"\n--- 3-FINGER SWIPE LEFT (BROWSER BACK) ---\n")
                        self.last_swipe_time = current_time
                        browser_back()
                    elif swipe_dir == "Swipe Right":
                        print(f"\n--- 3-FINGER SWIPE RIGHT (BROWSER FORWARD) ---\n")
                        self.last_swipe_time = current_time
                        browser_forward()
                        
        # C. Peace Sign (2 Fingers): Tab / Window Navigation
        #    Right -> Next Tab/Window, Left -> Previous Tab/Window
        #    Down or Pinch -> Confirm / Enter Selected Tab
        elif gesture == "Peace":
            if current_time - self.last_swipe_time > 0.35:
                swipe_dir = self.peace_swipe_detector.process(gesture_data["cursor_x"], gesture_data["cursor_y"])
                if swipe_dir:
                    if swipe_dir == "Swipe Right":
                        print(f"\n--- PEACE SWIPE RIGHT (NEXT TAB) ---\n")
                        self.last_swipe_time = current_time
                        select_next_window()
                        self.tab_selection_mode = True
                        self.last_tab_selection_time = current_time
                    elif swipe_dir == "Swipe Left":
                        print(f"\n--- PEACE SWIPE LEFT (PREV TAB) ---\n")
                        self.last_swipe_time = current_time
                        select_prev_window()
                        self.tab_selection_mode = True
                        self.last_tab_selection_time = current_time
                    elif swipe_dir == "Swipe Down":
                        print(f"\n--- PEACE SWIPE DOWN (CONFIRM / ENTER TAB) ---\n")
                        self.last_swipe_time = current_time
                        confirm_selection()
                        self.tab_selection_mode = False
        
        # Clear specific swipe buffer if not performing that gesture
        if gesture != "Open Palm":
            self.palm_swipe_detector.clear()
        if gesture != "Three Fingers":
            self.three_finger_swipe_detector.clear()
        if gesture != "Peace":
            self.peace_swipe_detector.clear()
