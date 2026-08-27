import threading
import time
import cv2
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Import our custom gesture detection modules
from input.gesture.camera import Camera
from input.gesture.landmark_detector import HandLandmarkDetector
from input.gesture.classifier import GestureClassifier
from input.gesture.stability_filter import GestureStabilityFilter
from input.voice.voice_listener import VoiceListener

# Import the Event Router
from core.commands.event_router import EventRouter

# Global state to hold the most recent stable gesture dictionary
current_gesture_data = {"gesture": "None", "cursor_x": 0.0, "cursor_y": 0.0, "pinch_dist": 1.0}
is_running = False

def gesture_recognition_loop():
    """
    Runs continuously in a background thread, reading from the camera
    and updating the global state.
    """
    global current_gesture_data, is_running
    
    # Initialize our pipeline components
    try:
        camera = Camera(camera_index=0)
        detector = HandLandmarkDetector()
        classifier = GestureClassifier()
        stability = GestureStabilityFilter(history_size=7, confidence_threshold=0.6, base_alpha=0.7)
        router = EventRouter()
        voice_listener = VoiceListener(on_mode_change=lambda active, text: router.set_active(active))
        voice_listener.start()
    except Exception as e:
        print(f"Failed to initialize camera or mediapipe: {e}")
        return
        
    previous_gesture_data = {"gesture": "None", "cursor_x": 0.0, "cursor_y": 0.0, "pinch_dist": 1.0, "norm_pinch_dist": 1.0}
    
    print("\n=== CAMERA STARTED: Say 'Hand gesture mode on' to activate! ===\n")
    
    while is_running:
        try:
            # 1. Get frame and flip horizontally for natural mirror behavior
            frame = camera.get_frame()
            frame = cv2.flip(frame, 1)
            
            # 2. Detect hand landmarks
            landmarks = detector.process_frame(frame)
            
            # 3. Classify raw gesture
            raw_gesture_data = {"gesture": "None", "cursor_x": 0.0, "cursor_y": 0.0, "pinch_dist": 1.0, "norm_pinch_dist": 1.0}
            if landmarks and len(landmarks) > 0:
                raw_gesture_data = classifier.classify(landmarks[0])
                
            # 4. Filter for stability and smooth coordinates
            current_gesture_data = stability.get_stable_gesture(raw_gesture_data)
            
            # 5. Route event to action handlers
            router.dispatch(current_gesture_data, previous_gesture_data)
            
            # Save previous state
            previous_gesture_data = current_gesture_data
            
            # --- VISUAL PREVIEW & HUD ---
            if landmarks:
                frame = detector.draw_landmarks(frame, landmarks)
            
            mode_text = "ACTIVE (Say 'Stop Nexa')" if router.is_active else "IDLE (Say 'Start Nexa')"
            color = (0, 255, 0) if router.is_active else (0, 0, 255)
            
            # Background banner for readable text
            cv2.rectangle(frame, (0, 0), (640, 90), (0, 0, 0), -1)
            cv2.putText(frame, f"Mode: {mode_text}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            cv2.putText(frame, f"Gesture: {current_gesture_data['gesture']}", (15, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            
            # Draw cursor crosshair if active and tracking/pinching
            if router.is_active and current_gesture_data["gesture"] in ("Index", "Pinch"):
                h, w, _ = frame.shape
                cx = int(current_gesture_data["cursor_x"] * w)
                cy = int(current_gesture_data["cursor_y"] * h)
                dot_color = (0, 255, 255) if current_gesture_data["gesture"] == "Pinch" else (255, 100, 0)
                cv2.circle(frame, (cx, cy), 10, dot_color, -1)
                cv2.circle(frame, (cx, cy), 14, (255, 255, 255), 2)
            
            cv2.imshow("Nexa Gesture Camera", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
        except Exception as e:
            print(f"Error in gesture loop: {e}")
            break
            
    voice_listener.stop()
    camera.release()
    cv2.destroyAllWindows()

# Lifespan context manager runs code before the server starts and after it stops
@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_running
    is_running = True
    thread = threading.Thread(target=gesture_recognition_loop, daemon=True)
    thread.start()
    yield
    is_running = False
    thread.join(timeout=2.0)

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Hello": "Nexa Backend is Running!"}

@app.get("/gesture")
def get_current_gesture():
    return current_gesture_data
