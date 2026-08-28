import time
from collections import deque

class SwipeDetector:
    def __init__(self, history_size=15, swipe_threshold=0.075, time_window=0.5):
        self.history_size = history_size
        self.swipe_threshold = swipe_threshold
        self.time_window = time_window  # Max seconds to look back for swipe motion
        self.history = deque(maxlen=history_size)
        
    def process(self, x, y):
        now = time.time()
        self.history.append((x, y, now))
        
        # Remove points older than the time window
        while self.history and (now - self.history[0][2] > self.time_window):
            self.history.popleft()
            
        if len(self.history) < 3:
            return None
            
        # 1. Compare current point against the oldest point in the active window
        current_x, current_y, _ = self.history[-1]
        oldest_x, oldest_y, _ = self.history[0]
        
        dx = current_x - oldest_x
        dy = current_y - oldest_y
        
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        
        # 2. If the net displacement reaches threshold, check peak in buffer
        if max(abs_dx, abs_dy) < self.swipe_threshold:
            # Check maximum span within buffer to catch rapid flick peaks
            max_dx = 0.0
            max_dy = 0.0
            for hx, hy, _ in self.history:
                cur_dx = current_x - hx
                cur_dy = current_y - hy
                if abs(cur_dx) > abs(max_dx):
                    max_dx = cur_dx
                if abs(cur_dy) > abs(max_dy):
                    max_dy = cur_dy
                    
            if max(abs(max_dx), abs(max_dy)) >= self.swipe_threshold:
                dx, dy = max_dx, max_dy
                abs_dx, abs_dy = abs(dx), abs(dy)
            else:
                return None
            
        # 3. Determine dominant axis with natural human arc tolerance (1.05x)
        if abs_dx > abs_dy * 1.05:  # Horizontal Swipe
            self.history.clear()    # Reset to prevent multi-trigger
            if dx > 0:
                return "Swipe Right"
            else:
                return "Swipe Left"
        elif abs_dy > abs_dx * 1.05: # Vertical Swipe
            self.history.clear()
            if dy > 0:
                return "Swipe Down"
            else:
                return "Swipe Up"
                
        return None
        
    def clear(self):
        self.history.clear()
