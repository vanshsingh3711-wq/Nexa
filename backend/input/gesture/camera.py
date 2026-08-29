import sys
import time
import threading
import cv2

class Camera:
    def __init__(self, camera_index=0, width=640, height=480):
        """
        Initialize the camera using OpenCV with a dedicated background capture thread.

        The capture thread continuously reads frames and keeps only the most recent
        frame available to the processing pipeline, reducing stale-frame and blocking
        camera I/O latency.
        """
        self.camera_index = camera_index
        self.cap = None
        
        # 1. Select backend (DirectShow on Windows avoids MSMF issues and buffer lag)
        if sys.platform.startswith("win"):
            self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        
        # Fallback to default backend if not opened
        if self.cap is None or not self.cap.isOpened():
            if self.cap is not None:
                self.cap.release()
            self.cap = cv2.VideoCapture(camera_index)
            
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera with index {camera_index}")

        # 2. Hardware properties optimization
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if width:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        # 3. Threaded reader state
        self._lock = threading.Lock()
        self._frame = None
        self._has_frame = threading.Event()
        self._is_running = True
        
        # Start continuous reader thread
        self._thread = threading.Thread(target=self._capture_loop, name="Nexa-Camera-Thread", daemon=True)
        self._thread.start()

        # Wait for the first frame to arrive (up to 2.5 seconds)
        if not self._has_frame.wait(timeout=2.5):
            self.release()
            raise RuntimeError(f"Camera index {camera_index} initialized but failed to stream frames.")

    def _capture_loop(self):
        """Background thread continuously grabbing the most recent frame."""
        while self._is_running:
            if self.cap is None or not self.cap.isOpened():
                break
                
            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self._lock:
                    self._frame = frame
                self._has_frame.set()
            else:
                # Small yield to prevent CPU pegging if camera stream hiccups
                time.sleep(0.005)

    def get_frame(self, copy: bool = False):
        """
        Returns the latest captured frame instantly without blocking on camera I/O.
        
        Zero-Copy by default (copy=False): In Python, `cap.read()` allocates a new
        NumPy ndarray for each read frame. Returning the reference avoids copying
        ~0.9MB per frame (~27MB/s at 30 FPS), reducing memory bandwidth and GC pressure.
        """
        with self._lock:
            if self._frame is None:
                raise RuntimeError("No frame available from camera")
            return self._frame.copy() if copy else self._frame


    def release(self):
        """Release the camera and stop the background capture thread."""
        self._is_running = False
        if hasattr(self, '_thread') and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=1.0)
            
        with self._lock:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
                self.cap = None

    def __del__(self):
        """Ensure resources are released on garbage collection."""
        self.release()


