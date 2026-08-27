from collections import deque

class GestureStabilityFilter:
    def __init__(self, history_size=10, confidence_threshold=0.7):
        """
        Initializes the stability filter.
        
        :param history_size: Number of previous frames to keep in memory.
        :param confidence_threshold: Ratio of frames that must contain the same gesture 
                                     to be considered "stable" (e.g., 0.7 means 70% of frames).
        """
        self.history_size = history_size
        self.confidence_threshold = confidence_threshold
        self.history = deque(maxlen=history_size)
        
    def get_stable_gesture(self, current_gesture):
        """
        Takes the raw gesture detected in the current frame and returns a stable gesture 
        if it meets the threshold. Otherwise, returns 'Unknown'.
        """
        # Add the newest gesture to our sliding window (automatically removes oldest if full)
        self.history.append(current_gesture)
        
        # Wait until we have enough frames to make a reasonable decision
        if len(self.history) < self.history_size // 2:
            return "Unknown"
            
        # Count occurrences of all gestures currently in the sliding window
        gesture_counts = {}
        for gesture in self.history:
            # Ignore 'Unknown' or 'None' when calculating majority votes for actual gestures
            if gesture not in ("Unknown", "None"):
                gesture_counts[gesture] = gesture_counts.get(gesture, 0) + 1
                
        # If there are no real gestures in the history, return what we got
        if not gesture_counts:
            return current_gesture if current_gesture in ("Unknown", "None") else "Unknown"
            
        # Find the gesture that appeared the most in the recent frames
        best_gesture = max(gesture_counts, key=gesture_counts.get)
        best_count = gesture_counts[best_gesture]
        
        # Check if the most common gesture meets the threshold
        required_count = len(self.history) * self.confidence_threshold
        
        if best_count >= required_count:
            return best_gesture
            
        return "Unknown"
        
    def reset(self):
        """
        Clears the history. Useful if there is a long break between detections.
        """
        self.history.clear()
