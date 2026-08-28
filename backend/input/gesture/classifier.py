import math

class GestureClassifier:
    def __init__(self):
        pass
        
    def classify(self, hand_landmarks):
        """
        Returns a dictionary containing the detected gesture and useful coordinates.
        Calculations are scale-invariant based on the palm size.
        """
        if not hand_landmarks:
            return {
                "gesture": "None",
                "cursor_x": 0.0,
                "cursor_y": 0.0,
                "pinch_dist": 1.0,
                "norm_pinch_dist": 1.0
            }
            
        wrist = hand_landmarks[0]
        middle_mcp = hand_landmarks[9]
        
        # Palm scale reference (distance between wrist and middle MCP)
        palm_size = math.hypot(middle_mcp.x - wrist.x, middle_mcp.y - wrist.y)
        if palm_size < 0.01:
            palm_size = 0.01
            
        thumb_tip = hand_landmarks[4]
        thumb_ip = hand_landmarks[3]
        thumb_mcp = hand_landmarks[2]
        index_mcp = hand_landmarks[5]
        index_pip = hand_landmarks[6]
        index_tip = hand_landmarks[8]
        middle_tip = hand_landmarks[12]
        ring_tip = hand_landmarks[16]
        pinky_tip = hand_landmarks[20]
        pinky_mcp = hand_landmarks[17]
        
        # 1. Non-thumb finger extension detection (rotation-tolerant)
        finger_tip_ids = [8, 12, 16, 20]
        finger_pip_ids = [6, 10, 14, 18]
        finger_mcp_ids = [5, 9, 13, 17]
        
        extended = []
        for tip_id, pip_id, mcp_id in zip(finger_tip_ids, finger_pip_ids, finger_mcp_ids):
            tip = hand_landmarks[tip_id]
            pip = hand_landmarks[pip_id]
            mcp = hand_landmarks[mcp_id]
            
            dist_wrist_tip = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
            dist_wrist_pip = math.hypot(pip.x - wrist.x, pip.y - wrist.y)
            dist_mcp_tip = math.hypot(tip.x - mcp.x, tip.y - mcp.y)
            dist_mcp_pip = math.hypot(pip.x - mcp.x, pip.y - mcp.y)
            
            # A finger is extended if tip is further from wrist/mcp than pip
            is_ext = (dist_wrist_tip > dist_wrist_pip * 1.03) and (dist_mcp_tip > dist_mcp_pip * 1.03)
            extended.append(is_ext)
            
        is_index_ext, is_middle_ext, is_ring_ext, is_pinky_ext = extended
        
        # 2. Thumb extension detection
        dist_thumb_index_mcp = math.hypot(thumb_tip.x - index_mcp.x, thumb_tip.y - index_mcp.y)
        dist_thumb_pinky = math.hypot(thumb_tip.x - pinky_mcp.x, thumb_tip.y - pinky_mcp.y)
        
        is_thumb_ext = (dist_thumb_index_mcp > palm_size * 0.6) and (dist_thumb_pinky > palm_size * 0.75)
        
        # 3. Pinch Detection (scale normalized)
        raw_pinch_dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
        norm_pinch_dist = raw_pinch_dist / palm_size
        is_pinching = norm_pinch_dist < 0.35
        
        # 4. Cursor coordinates (from index fingertip)
        cursor_x = index_tip.x
        cursor_y = index_tip.y
        
        # 5. Gesture Classification
        gesture = "Unknown"
        num_ext = sum(1 for e in extended if e)
        
        # Priority A: Closed Fist / Thumbs Up / Thumbs Down (all 4 fingers curled tight into palm)
        if num_ext == 0:
            if is_thumb_ext and dist_thumb_index_mcp > palm_size * 0.65:
                # Distinguish Thumb Up vs Thumb Down by vertical position relative to MCP and wrist
                if thumb_tip.y < thumb_mcp.y - palm_size * 0.15 and thumb_tip.y < wrist.y:
                    gesture = "Thumb Up"
                elif thumb_tip.y > thumb_mcp.y + palm_size * 0.15 and thumb_tip.y > wrist.y:
                    gesture = "Thumb Down"
                else:
                    gesture = "Closed Fist"
            else:
                gesture = "Closed Fist"
                
        # Priority B: Pinch (thumb and index touching, but not a closed fist)
        elif is_pinching:
            gesture = "Pinch"
            
        # Priority C: Open Palm (All 4 non-thumb fingers extended)
        elif is_index_ext and is_middle_ext and is_ring_ext and is_pinky_ext:
            gesture = "Open Palm"
            
        # Priority D: Three Fingers (Index + Middle + Ring extended, Pinky curled)
        elif is_index_ext and is_middle_ext and is_ring_ext and not is_pinky_ext:
            gesture = "Three Fingers"
            
        # Priority E: Peace / V-Sign (Index + Middle extended, Ring/Pinky curled)
        elif is_index_ext and is_middle_ext and not (is_ring_ext and is_pinky_ext):
            gesture = "Peace"
            
        # Priority F: Index Finger Only (Mouse Tracking)
        elif is_index_ext and not is_middle_ext:
            gesture = "Index"
            
        # Coordinates mapping for displacement tracking
        if gesture == "Open Palm":
            cursor_x = (wrist.x + middle_mcp.x) / 2.0
            cursor_y = (wrist.y + middle_mcp.y) / 2.0
        elif gesture == "Three Fingers":
            cursor_x = (index_tip.x + middle_tip.x + ring_tip.x) / 3.0
            cursor_y = (index_tip.y + middle_tip.y + ring_tip.y) / 3.0
        elif gesture == "Peace":
            cursor_x = (index_tip.x + middle_tip.x) / 2.0
            cursor_y = (index_tip.y + middle_tip.y) / 2.0
            
        return {
            "gesture": gesture,
            "cursor_x": cursor_x,
            "cursor_y": cursor_y,
            "pinch_dist": raw_pinch_dist,
            "norm_pinch_dist": norm_pinch_dist
        }
