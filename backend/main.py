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

# Import the new media actions
from actions.media.media_actions import toggle_play_pause

# Global state to hold the most recent stable gesture
current_gesture = "None"
is_running = False

def gesture_recognition_loop():
    """
    Runs continuously in a background thread, reading from the camera
    and updating the global `current_gesture` state.
    """
    global current_gesture, is_running
    
    # Initialize our pipeline components
    try:
        camera = Camera(camera_index=0)
        detector = HandLandmarkDetector()
        classifier = GestureClassifier()
        stability = GestureStabilityFilter(history_size=10, confidence_threshold=0.7)
    except Exception as e:
        print(f"Failed to initialize camera or mediapipe: {e}")
        return
        
    previous_gesture = "None"
    last_action_time = 0.0
    
    print("\n=== CAMERA STARTED: Hold up your Open Palm! ===\n")
    
    while is_running:
        try:
            # 1. Get frame
            frame = camera.get_frame()
            
            # 2. Detect hand landmarks
            landmarks = detector.process_frame(frame)
            
            # 3. Classify raw gesture (using the first hand detected)
            raw_gesture = "None"
            if landmarks and len(landmarks) > 0:
                raw_gesture = classifier.classify(landmarks[0])
                
            # 4. Filter for stability
            current_gesture = stability.get_stable_gesture(raw_gesture)
            
            # 5. Trigger Actions based on gesture
            current_time = time.time()
            # We only trigger when transitioning into "Open Palm", with a 2-second cooldown to prevent spamming
            if current_gesture == "Open Palm" and previous_gesture != "Open Palm":
                if current_time - last_action_time > 2.0:
                    print("Open Palm Detected: Toggling OS Play/Pause")
                    toggle_play_pause()
                    last_action_time = current_time
                    previous_gesture = current_gesture
            elif current_gesture != "Open Palm":
                previous_gesture = current_gesture
            
            # --- VISUAL PREVIEW ---
            # Draw the hand dots so you can see it working
            if landmarks:
                frame = detector.draw_landmarks(frame, landmarks)
            
            cv2.putText(frame, f"Gesture: {current_gesture}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
            cv2.imshow("Nexa Gesture Camera", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
        except Exception as e:
            print(f"Error in gesture loop: {e}")
            break
            
    camera.release()
    cv2.destroyAllWindows()

# Lifespan context manager runs code before the server starts and after it stops
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global is_running
    is_running = True
    
    # Run the blocking OpenCV/MediaPipe loop in a separate background thread
    # so it doesn't block the FastAPI web server from handling requests.
    thread = threading.Thread(target=gesture_recognition_loop, daemon=True)
    thread.start()
    
    yield
    
    # Shutdown
    is_running = False
    thread.join(timeout=2.0)

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Hello": "Nexa Backend is Running!"}

@app.get("/gesture")
def get_current_gesture():
    """
    Frontend clients can call this endpoint to get the current gesture.
    """
    return {"gesture": current_gesture}
