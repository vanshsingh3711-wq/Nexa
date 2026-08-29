import time
from typing import Optional, Dict, Any, Callable

from input.gesture.swipe_detector import SwipeDetector
from core.security.models import StructuredActionRequest
from core.commands.action_router import ActionRouter
from core.feedback.feedback_service import FeedbackService, get_feedback_service

class EventRouter:
    """
    Translates stable gesture inputs into StructuredActionRequests and
    routes them through the PolicyChecker security boundary via ActionRouter.
    
    Also manages top-level Nexa application lifecycle state (Active, Sleep/Idle, Closing).
    """
    def __init__(
        self,
        action_router: Optional[ActionRouter] = None,
        feedback_service: Optional[FeedbackService] = None,
        gesture_manager: Optional[Any] = None,
        start_active: bool = True,
    ):
        self.is_active = False  # Gesture mode state (camera & tracking, False by default)
        self.is_nexa_active = start_active  # Top-level Nexa active state (True by default for voice control)
        self._is_closing = False
        
        self.action_router = action_router if action_router is not None else ActionRouter()
        self.feedback_service = feedback_service if feedback_service is not None else get_feedback_service()
        self.gesture_manager = gesture_manager
        
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

    def wake_nexa(self, speak: bool = True, start_gestures: bool = False) -> bool:
        """
        Wakes Nexa from Sleep/Idle mode.
        Activates Nexa application state and speaks welcome feedback.
        Gestures remain inactive unless explicitly requested.
        """
        self.is_nexa_active = True
        self._is_closing = False
        print(f"\n{'='*40}\n[Nexa] APPLICATION WOKEN UP & ACTIVATED (Voice Ready)\n{'='*40}\n")
        
        # Start gesture pipeline & camera ONLY if explicitly asked
        if start_gestures and self.gesture_manager:
            try:
                self.gesture_manager.start(speak_feedback=False)
            except Exception as e:
                print(f"[EventRouter] Error starting gesture manager on wake: {e}")

        # Speak welcome confirmation
        if speak and self.feedback_service:
            try:
                self.feedback_service.handle_nexa_wake()
            except Exception as e:
                print(f"[EventRouter] Feedback error on wake: {e}")
        return True

    def close_nexa(self, cleanup_fn: Optional[Callable[[], None]] = None, speak: bool = True) -> bool:
        """
        Puts Nexa into Sleep/Idle mode:
        Speaks closing message, stops gesture subsystem & releases camera, sets is_nexa_active = False.
        The voice listener actively continues running in the background waiting for 'Wake up Nexa'.
        """
        self._is_closing = True
        self.is_nexa_active = False
        print(f"\n{'='*40}\n[Nexa] ENTERING SLEEP / IDLE MODE (Camera Released, Voice Active)\n{'='*40}\n")
        
        # 1. Stop gesture subsystem & release camera hardware immediately
        if self.gesture_manager:
            try:
                self.gesture_manager.stop(speak_feedback=False)
            except Exception as e:
                print(f"[EventRouter] Error stopping gesture manager on close: {e}")

        # 2. Speak closing feedback asynchronously
        if speak and self.feedback_service:
            try:
                self.feedback_service.handle_nexa_close(block=False)
            except Exception as e:
                print(f"[EventRouter] Feedback error on close: {e}")

        # 3. Optional hook
        if cleanup_fn:
            try:
                cleanup_fn()
            except Exception as e:
                print(f"[EventRouter] Error in cleanup callback: {e}")

        self._is_closing = False
        return True

    def execute_action(self, action: str, params: Optional[Dict[str, Any]] = None, source: str = "gesture"):
        """Creates a StructuredActionRequest and submits it through the PolicyChecker."""
        if not self.is_nexa_active:
            print(f"[EventRouter] Ignoring '{action}': Nexa is in Sleep mode (Say 'Wake up Nexa' to activate).")
            return None, None
            
        request = StructuredActionRequest(
            action=action,
            params=params or {},
            source=source,
        )
        return self.action_router.dispatch(request)
        
    def set_active(self, is_active: bool, speak: bool = False):
        """Enable or disable gesture control mode specifically."""
        previous_active = self.is_active
        self.is_active = is_active
        self.tab_selection_mode = False
        status = "ACTIVATED (Controlling PC)" if self.is_active else "DEACTIVATED (Idle)"
        print(f"\n{'='*40}\n[Nexa] GESTURE MODE {status}\n{'='*40}\n")
        if not is_active:
            self.palm_swipe_detector.clear()
            self.three_finger_swipe_detector.clear()
            self.peace_swipe_detector.clear()

        # Verbal feedback on gesture state transition if explicitly requested
        if speak and self.feedback_service and (previous_active != is_active):
            try:
                self.feedback_service.handle_gesture_lifecycle(is_active)
            except Exception as e:
                print(f"[EventRouter] Feedback error on gesture mode change: {e}")

    def dispatch(self, gesture_data, previous_gesture_data):
        gesture = gesture_data.get("gesture", "None")
        previous_gesture = previous_gesture_data.get("gesture", "None")
        current_time = time.time()
            
        # If we are in Idle mode or Nexa is not active, do not process any controls
        if not self.is_active or not self.is_nexa_active:
            self.palm_swipe_detector.clear()
            self.three_finger_swipe_detector.clear()
            self.peace_swipe_detector.clear()
            return
            
        # Check tab selection mode expiration
        if self.tab_selection_mode and (current_time - self.last_tab_selection_time > self.tab_selection_timeout):
            self.tab_selection_mode = False
            
        # 2. Mouse Controls & Pinch Entering / Clicking
        if gesture == "Index":
            cx = max(0.0, min(1.0, float(gesture_data.get("cursor_x", 0.0))))
            cy = max(0.0, min(1.0, float(gesture_data.get("cursor_y", 0.0))))
            self.execute_action("move_mouse", {"norm_x": cx, "norm_y": cy})
            
        elif gesture == "Pinch":
            if self.tab_selection_mode:
                # In tab/window selection mode: Pinch confirms and opens the selected tab (Enter)
                if previous_gesture != "Pinch" and (current_time - self.last_click_time > 0.4):
                    print("\n[Nexa] PINCH -> CONFIRM TAB/WINDOW SELECTION (Enter)\n")
                    self.execute_action("confirm_selection")
                    self.tab_selection_mode = False
                    self.last_click_time = current_time
            else:
                # Normal mode: Continue tracking cursor and perform Left Click
                cx = max(0.0, min(1.0, float(gesture_data.get("cursor_x", 0.0))))
                cy = max(0.0, min(1.0, float(gesture_data.get("cursor_y", 0.0))))
                self.execute_action("move_mouse", {"norm_x": cx, "norm_y": cy})
                if previous_gesture != "Pinch" and (current_time - self.last_click_time > 0.4):
                    self.execute_action("left_click")
                    self.last_click_time = current_time
                
        # 3. Media Controls (Closed Fist = Toggle Play/Pause)
        elif gesture == "Closed Fist" and previous_gesture != "Closed Fist":
            if current_time - self.last_media_time > 1.2:
                self.execute_action("toggle_play_pause")
                self.last_media_time = current_time
                
        # 4. Volume Controls (Thumb Up = Vol+, Thumb Down = Vol-)
        elif gesture == "Thumb Up":
            # Allow rapid repeated tapping or continuous slow increment (every 0.35s)
            if (previous_gesture != "Thumb Up") or (current_time - self.last_volume_time > 0.35):
                self.execute_action("volume_up")
                self.last_volume_time = current_time
                
        elif gesture == "Thumb Down":
            if (previous_gesture != "Thumb Down") or (current_time - self.last_volume_time > 0.35):
                self.execute_action("volume_down")
                self.last_volume_time = current_time
                
        # 5. Swipe / Navigation Controls
        # A. Open Palm: Swipe Up -> Open Task View / Tab Switcher (Win + Tab)
        if gesture == "Open Palm":
            if current_time - self.last_swipe_time > 0.45:
                swipe_dir = self.palm_swipe_detector.process(gesture_data["cursor_x"], gesture_data["cursor_y"])
                if swipe_dir == "Swipe Up":
                    print(f"\n--- OPEN PALM SWIPE UP (OPEN TASK VIEW) ---\n")
                    self.last_swipe_time = current_time
                    self.execute_action("open_task_view")
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
                        self.execute_action("browser_back")
                    elif swipe_dir == "Swipe Right":
                        print(f"\n--- 3-FINGER SWIPE RIGHT (BROWSER FORWARD) ---\n")
                        self.last_swipe_time = current_time
                        self.execute_action("browser_forward")
                        
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
                        self.execute_action("select_next_window")
                        self.tab_selection_mode = True
                        self.last_tab_selection_time = current_time
                    elif swipe_dir == "Swipe Left":
                        print(f"\n--- PEACE SWIPE LEFT (PREV TAB) ---\n")
                        self.last_swipe_time = current_time
                        self.execute_action("select_prev_window")
                        self.tab_selection_mode = True
                        self.last_tab_selection_time = current_time
                    elif swipe_dir == "Swipe Down":
                        print(f"\n--- PEACE SWIPE DOWN (CONFIRM / ENTER TAB) ---\n")
                        self.last_swipe_time = current_time
                        self.execute_action("confirm_selection")
                        self.tab_selection_mode = False
        
        # Clear specific swipe buffer if not performing that gesture
        if gesture != "Open Palm":
            self.palm_swipe_detector.clear()
        if gesture != "Three Fingers":
            self.three_finger_swipe_detector.clear()
        if gesture != "Peace":
            self.peace_swipe_detector.clear()
