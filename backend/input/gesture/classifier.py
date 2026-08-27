import math

class GestureClassifier:
    def __init__(self):
        pass
        
    def classify(self, hand_landmarks):
        """
        Takes a single hand's landmarks and classifies the gesture.
        Optimized for detecting an 'Open Palm'.
        """
        if not hand_landmarks:
            return "None"
            
        fingers_up = self._get_fingers_up(hand_landmarks)
        
        # Open Palm: All 5 fingers are up
        if sum(fingers_up) == 5:
            return "Open Palm"
            
        # Closed Fist: 0 fingers up
        elif sum(fingers_up) == 0:
            return "Closed Fist"
            
        return "Unknown"

    def _get_fingers_up(self, landmarks):
        """
        Determines which fingers are extended.
        Returns a list of 5 integers (1 for up, 0 for down) for [Thumb, Index, Middle, Ring, Pinky].
        """
        fingers = []
        
        # Indices for Finger Tips and PIP (Proximal Interphalangeal) joints
        finger_tip_ids = [8, 12, 16, 20]
        finger_pip_ids = [6, 10, 14, 18]
        
        # 1. Thumb (Special Case)
        wrist = landmarks[0]
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        
        dist_wrist_tip = math.hypot(thumb_tip.x - wrist.x, thumb_tip.y - wrist.y)
        dist_wrist_ip = math.hypot(thumb_ip.x - wrist.x, thumb_ip.y - wrist.y)
        
        if dist_wrist_tip > dist_wrist_ip:
            fingers.append(1)
        else:
            fingers.append(0)

        # 2. Other 4 fingers
        for tip_id, pip_id in zip(finger_tip_ids, finger_pip_ids):
            if landmarks[tip_id].y < landmarks[pip_id].y:
                fingers.append(1)
            else:
                fingers.append(0)
                
        return fingers
