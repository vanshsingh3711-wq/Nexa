import cv2

class Camera:
    def __init__(self, camera_index=0):
        """Initialize the camera using OpenCV."""
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera with index {camera_index}")

    def get_frame(self):
        """Capture a frame from the camera."""
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to capture frame from camera")
        return frame

    def release(self):
        """Release the camera resource."""
        if self.cap.isOpened():
            self.cap.release()

    def __del__(self):
        """Ensure the camera is released when the object is destroyed."""
        self.release()
