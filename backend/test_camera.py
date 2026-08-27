import time
import cv2
from input.gesture.camera import Camera
from input.gesture.landmark_detector import HandLandmarkDetector
from input.gesture.classifier import GestureClassifier
from input.gesture.stability_filter import GestureStabilityFilter
from actions.media.media_actions import toggle_play_pause

def run():
    print("Initializing camera and mediapipe...")
    try:
        camera = Camera(camera_index=0)
        detector = HandLandmarkDetector()
        classifier = GestureClassifier()
        stability = GestureStabilityFilter(history_size=10, confidence_threshold=0.7)
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return

    previous_gesture = "None"
    last_action_time = 0.0

    print("\n=== CAMERA STARTED: Hold up your Open Palm! ===")
    print("Press 'q' in the camera window to quit.\n")

    while True:
        try:
            frame = camera.get_frame()
            landmarks = detector.process_frame(frame)
            
            raw_gesture = "None"
            if landmarks and len(landmarks) > 0:
                raw_gesture = classifier.classify(landmarks[0])
                
            current_gesture = stability.get_stable_gesture(raw_gesture)
            
            current_time = time.time()
            if current_gesture == "Open Palm" and previous_gesture != "Open Palm":
                if current_time - last_action_time > 2.0:
                    print("--> OPEN PALM DETECTED! Toggling Play/Pause")
                    toggle_play_pause()
                    last_action_time = current_time
                    previous_gesture = current_gesture
            elif current_gesture != "Open Palm":
                previous_gesture = current_gesture
            
            if landmarks:
                frame = detector.draw_landmarks(frame, landmarks)
            
            cv2.putText(frame, f"Gesture: {current_gesture}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
            cv2.imshow("Nexa Gesture Camera", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        except Exception as e:
            print(f"Error during execution: {e}")
            break

    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run()
