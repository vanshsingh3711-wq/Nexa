from collections import deque
import math

class GestureStabilityFilter:
    def __init__(self, history_size=7, confidence_threshold=0.6, base_alpha=0.7, ema_alpha=None):
        self.history_size = history_size
        self.confidence_threshold = confidence_threshold
        self.history = deque(maxlen=history_size)
        self.base_alpha = ema_alpha if ema_alpha is not None else base_alpha
        
        # Keep track of smoothed coordinates
        self.smoothed_x = None
        self.smoothed_y = None
        self.last_stable_gesture = "None"
        self.unknown_count = 0

    def get_stable_gesture(self, raw_gesture_data):
        raw_gesture = raw_gesture_data.get("gesture", "None")
        raw_x = raw_gesture_data.get("cursor_x", 0.0)
        raw_y = raw_gesture_data.get("cursor_y", 0.0)
        pinch_dist = raw_gesture_data.get("pinch_dist", 1.0)
        norm_pinch_dist = raw_gesture_data.get("norm_pinch_dist", 1.0)
        
        # Hand not detected at all
        if raw_gesture == "None":
            self.history.clear()
            self.smoothed_x = None
            self.smoothed_y = None
            self.last_stable_gesture = "None"
            self.unknown_count = 0
            return {
                "gesture": "None",
                "cursor_x": 0.0,
                "cursor_y": 0.0,
                "pinch_dist": 1.0,
                "norm_pinch_dist": 1.0
            }
            
        # 1. Responsive & Adaptive Coordinate Smoothing
        if self.smoothed_x is None:
            self.smoothed_x = raw_x
            self.smoothed_y = raw_y
        else:
            # Calculate distance moved in frame
            move_dist = math.hypot(raw_x - self.smoothed_x, raw_y - self.smoothed_y)
            # Adapt alpha: fast movement gets higher alpha (no lag), small movement gets lower alpha (no jitter)
            adaptive_alpha = min(1.0, self.base_alpha + (move_dist * 2.0))
            self.smoothed_x = (adaptive_alpha * raw_x) + ((1.0 - adaptive_alpha) * self.smoothed_x)
            self.smoothed_y = (adaptive_alpha * raw_y) + ((1.0 - adaptive_alpha) * self.smoothed_y)
            
        # 2. Stable Gesture Classification with Dropout Resistance
        self.history.append(raw_gesture)
        
        gesture_counts = {}
        for g in self.history:
            if g not in ("Unknown", "None"):
                gesture_counts[g] = gesture_counts.get(g, 0) + 1
                
        stable_gesture = "Unknown"
        if gesture_counts:
            best_gesture = max(gesture_counts, key=gesture_counts.get)
            votes = gesture_counts[best_gesture]
            total_history = len(self.history)
            
            if votes >= max(2, int(total_history * self.confidence_threshold)):
                stable_gesture = best_gesture
                self.last_stable_gesture = best_gesture
                self.unknown_count = 0
                
        if stable_gesture == "Unknown":
            self.unknown_count += 1
            # Maintain previous stable gesture for up to 3 transitional frames to prevent flickering
            if self.unknown_count <= 3 and self.last_stable_gesture not in ("None", "Unknown"):
                stable_gesture = self.last_stable_gesture
            else:
                self.last_stable_gesture = "Unknown"
                
        return {
            "gesture": stable_gesture,
            "cursor_x": self.smoothed_x,
            "cursor_y": self.smoothed_y,
            "pinch_dist": pinch_dist,
            "norm_pinch_dist": norm_pinch_dist
        }

    def reset(self):
        self.history.clear()
        self.smoothed_x = None
        self.smoothed_y = None
        self.last_stable_gesture = "None"
        self.unknown_count = 0
