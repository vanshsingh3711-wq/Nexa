from collections import deque

class SwipeDetector:
    def __init__(self, history_size=15, swipe_threshold=0.3):
        self.history_size = history_size
        self.swipe_threshold = swipe_threshold
        self.history = deque(maxlen=history_size)
        
    def process(self, x, y):
        self.history.append((x, y))
        
        if len(self.history) < self.history_size:
            return None
            
        oldest_x, oldest_y = self.history[0]
        current_x, current_y = self.history[-1]
        
        dx = current_x - oldest_x
        dy = current_y - oldest_y
        
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        
        # Check if the overall displacement is enough to be considered a swipe
        if max(abs_dx, abs_dy) < self.swipe_threshold:
            return None
            
        # Determine dominant axis
        if abs_dx > abs_dy * 1.5:  # Horizontal
            self.history.clear() # Reset to prevent multi-trigger
            if dx > 0:
                return "Swipe Right"
            else:
                return "Swipe Left"
        elif abs_dy > abs_dx * 1.5: # Vertical
            self.history.clear()
            if dy > 0:
                return "Swipe Down"
            else:
                return "Swipe Up"
                
        return None
        
    def clear(self):
        self.history.clear()
