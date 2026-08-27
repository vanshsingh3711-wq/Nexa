import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os

class HandLandmarkDetector:
    def __init__(self, model_asset_path='input/gesture/hand_landmarker.task', num_hands=2):
        """Initialize the MediaPipe Hand Landmarker Task."""
        if not os.path.exists(model_asset_path):
            raise FileNotFoundError(f"Model file not found at {model_asset_path}. Please download it.")
            
        base_options = python.BaseOptions(model_asset_path=model_asset_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=num_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def process_frame(self, frame):
        """
        Processes an OpenCV BGR frame and returns the detected hand landmarks.
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        # Perform the hand landmark detection
        detection_result = self.detector.detect(mp_image)
        
        # Return the list of hand landmarks
        return detection_result.hand_landmarks

    def draw_landmarks(self, frame, landmarks):
        """
        Draw landmarks directly onto the frame.
        """
        if not landmarks:
            return frame
            
        for hand_landmarks in landmarks:
            for mark in hand_landmarks:
                x = int(mark.x * frame.shape[1])
                y = int(mark.y * frame.shape[0])
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
                
        return frame

    def release(self):
        """Clean up resources."""
        if hasattr(self, 'detector') and self.detector is not None:
            self.detector.close()

    def __del__(self):
        self.release()
