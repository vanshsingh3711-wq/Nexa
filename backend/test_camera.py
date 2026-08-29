import cv2
import time
import threading
from input.gesture.gesture_manager import GestureManager
from input.voice.voice_listener import VoiceListener
from core.commands.event_router import EventRouter

def main():
    print("\n" + "="*55)
    print("🚀 NEXA GESTURE & VOICE CONTROL SYSTEM")
    print("="*55)
    
    # Start initially in Sleep / Idle mode (Camera OFF)
    # The user says "Wake up Nexa" to activate and turn on the camera!
    router = EventRouter(start_active=False)
    
    last_frame_lock = threading.Lock()
    last_frame_info = {"frame": None, "gesture_data": None, "landmarks": None}
    
    def on_frame(frame, current_gesture_data, landmarks):
        with last_frame_lock:
            last_frame_info["frame"] = frame.copy()
            last_frame_info["gesture_data"] = current_gesture_data
            last_frame_info["landmarks"] = landmarks

    gesture_manager = GestureManager(
        event_router=router,
        on_frame_callback=on_frame
    )
    router.gesture_manager = gesture_manager

    voice_listener = VoiceListener(
        on_nexa_wake=lambda: router.wake_nexa(speak=True, start_gestures=True),
        on_nexa_close=lambda: router.close_nexa(speak=True),
        on_gesture_mode_change=lambda active, text: gesture_manager.start() if active else gesture_manager.stop(),
        on_command=lambda cmd: router.execute_action(cmd, source="voice")
    )
    voice_listener.start()

    print("\n" + "-"*55)
    print("😴 Nexa is currently in SLEEP / IDLE mode (Camera is OFF).")
    print("🎤 Say 'Wake up Nexa' to start the camera and activate Nexa!")
    print("🚪 Say 'Close Nexa' or 'Sleep' to turn off the camera & return to sleep.")
    print("🛑 Press 'q' in the camera window or Ctrl+C in terminal to exit.")
    print("-"*55 + "\n")

    cv2_window_open = False

    try:
        while True:
            if router.is_nexa_active and gesture_manager.is_active:
                frame_to_show = None
                with last_frame_lock:
                    if last_frame_info["frame"] is not None:
                        frame_to_show = last_frame_info["frame"]
                        gesture_data = last_frame_info["gesture_data"]
                        landmarks = last_frame_info["landmarks"]

                if frame_to_show is not None:
                    # Draw HUD
                    if landmarks and gesture_manager.detector:
                        frame_to_show = gesture_manager.detector.draw_landmarks(frame_to_show, landmarks)

                    color = (0, 255, 0)
                    cv2.rectangle(frame_to_show, (0, 0), (640, 90), (0, 0, 0), -1)
                    cv2.putText(frame_to_show, "Nexa: ACTIVE | Camera: ON", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
                    cv2.putText(frame_to_show, f"Gesture: {gesture_data['gesture']}", (15, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

                    if gesture_data["gesture"] in ("Index", "Pinch"):
                        h, w, _ = frame_to_show.shape
                        cx = int(gesture_data["cursor_x"] * w)
                        cy = int(gesture_data["cursor_y"] * h)
                        dot_color = (0, 255, 255) if gesture_data["gesture"] == "Pinch" else (255, 100, 0)
                        cv2.circle(frame_to_show, (cx, cy), 10, dot_color, -1)
                        cv2.circle(frame_to_show, (cx, cy), 14, (255, 255, 255), 2)

                    cv2.imshow("Nexa Gesture Camera", frame_to_show)
                    cv2_window_open = True
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    time.sleep(0.02)
            else:
                # In Sleep mode: close camera window if it was open
                if cv2_window_open:
                    cv2.destroyAllWindows()
                    cv2_window_open = False
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        voice_listener.stop()
        gesture_manager.stop(speak_feedback=False)
        cv2.destroyAllWindows()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
