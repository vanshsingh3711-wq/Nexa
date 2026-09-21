import sys
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
import threading
import requests
import time
import math
from PyQt5.QtWidgets import QApplication, QWidget, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QCursor, QPainterPath, QPen

API_URL = "http://127.0.0.1:8000"

class NexaOrb(QWidget):
    def __init__(self):
        super().__init__()
        
        # UI State
        self.nexa_active = False
        self.gestures_active = False
        self.voice_active = False
        self.server_online = False
        
        self.last_action_timestamp = 0.0
        self.is_animating_action = False
        self.animation_step = 0
        self.local_mouse_pos = None
        self.is_user_speaking = False
        
        self.current_amplitude_mult = 0.3
        self.current_colors = [
            QColor(120, 120, 120, 120),
            QColor(150, 150, 150, 100),
            QColor(180, 180, 180, 80),
            QColor(100, 100, 100, 100)
        ]
        
        # Setup Window Properties
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Size of the widget (Wide rectangle for waves)
        self.resize(600, 100)
        self.setMouseTracking(True)
        
        # Window Dragging State
        self.old_pos = self.pos()
        
        # Setup Polling Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_backend)
        self.timer.start(300)  # 300ms interval for more responsive feedback
        
        # Continuous Animation Timer for Waves
        self.wave_phase = 0.0
        self.wave_timer = QTimer(self)
        self.wave_timer.timeout.connect(self.animate_waves)
        self.wave_timer.start(30)
        
        # Initial Poll
        self.poll_backend()

    def poll_backend(self):
        def _fetch():
            try:
                response = requests.get(f"{API_URL}/", timeout=1)
                if response.status_code == 200:
                    data = response.json()
                    self.server_online = True
                    self.nexa_active = data.get("nexa_active", False)
                    self.gestures_active = data.get("gestures_active", False)
                    self.voice_active = data.get("voice_active", False)
                    self.is_user_speaking = data.get("is_user_speaking", False)
                    
                    new_ts = data.get("last_action_timestamp", 0.0)
                    if new_ts > self.last_action_timestamp:
                        if self.last_action_timestamp != 0.0:
                            # Avoid animating on startup
                            self.trigger_action_animation()
                        self.last_action_timestamp = new_ts
                else:
                    self.server_online = False
            except Exception:
                self.server_online = False
            
            # The UI is updated 30 times a second by animate_waves, so we don't need self.update() here.
            # Calling self.update() from a background thread can cause a core dump.

        # Run fetch in a thread so it doesn't freeze the GUI
        threading.Thread(target=_fetch, daemon=True).start()

    def trigger_action_animation(self):
        self.is_animating_action = True
        self.animation_step = 0

    def animate_waves(self):
        speed_mult = 1.0
        if getattr(self, 'is_animating_action', False):
            speed_mult = 1.5
            self.animation_step += 1
            if self.animation_step > 30: # Slower, smoother fade out
                self.is_animating_action = False
                self.animation_step = 0
        elif getattr(self, 'is_user_speaking', False) and self.nexa_active:
            speed_mult = 1.0 # Speed up noticeably when speaking
        elif not self.server_online:
            speed_mult = 0.3
        elif self.gestures_active:
            speed_mult = 1.0
        elif not self.nexa_active:
            speed_mult = 0.1
            
        self.wave_phase += 0.05 * speed_mult  # Reduced base speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        mid_y = height / 2

        # Determine color based on state
        amplitude_mult = 1.0
        is_speaking_now = getattr(self, 'is_user_speaking', False) and self.nexa_active
        
        # Determine Target Amplitude
        if self.is_animating_action:
            # Smooth spike amplitude during action
            target_amplitude_mult = 1.0 + (15 - abs(15 - self.animation_step)) / 10.0 
        elif is_speaking_now:
            target_amplitude_mult = 1.5
        elif not self.server_online:
            target_amplitude_mult = 0.2
        elif self.gestures_active:
            target_amplitude_mult = 1.0
        elif self.nexa_active:
            target_amplitude_mult = 0.8
        else:
            target_amplitude_mult = 0.3

        # Determine Target Colors
        num_ribbons = 4
        if getattr(self, 'is_user_speaking', False) and self.nexa_active:
            target_colors = [
                QColor(255, 60, 0, 160),    # Vibrant Orange
                QColor(255, 20, 100, 140),  # Hot Pink
                QColor(255, 100, 0, 120),   # Light Orange
                QColor(255, 0, 150, 100)    # Deep Magenta
            ]
        elif self.nexa_active:
            target_colors = [
                QColor(0, 90, 200, 160),    # Deep Blue
                QColor(0, 150, 255, 140),   # Bright Blue
                QColor(0, 200, 255, 120),   # Cyan
                QColor(50, 100, 255, 100)   # Indigo
            ]
        else:
            target_colors = [
                QColor(120, 120, 120, 120),
                QColor(150, 150, 150, 100),
                QColor(180, 180, 180, 80),
                QColor(100, 100, 100, 100)
            ]

        # Interpolate Amplitude (Smooth transition)
        self.current_amplitude_mult += (target_amplitude_mult - self.current_amplitude_mult) * 0.15

        # Interpolate Colors (Smooth transition)
        for i in range(num_ribbons):
            cc = self.current_colors[i]
            tc = target_colors[i]
            r = cc.red() + (tc.red() - cc.red()) * 0.1
            g = cc.green() + (tc.green() - cc.green()) * 0.1
            b = cc.blue() + (tc.blue() - cc.blue()) * 0.1
            a = cc.alpha() + (tc.alpha() - cc.alpha()) * 0.1
            self.current_colors[i] = QColor(int(r), int(g), int(b), int(a))

        for i in range(num_ribbons):
            path = QPainterPath()
            
            freq = 0.005 + (i * 0.0015)
            phase = i * 2.1 + self.wave_phase
            
            # Amplitude scales with height
            amp = (height / 2.5) * self.current_amplitude_mult + (i * 2.0)
            
            # Top edge of ribbon
            start_y = mid_y + math.sin(phase) * amp
            
            # Apply mouse pull to start_y if applicable
            if getattr(self, 'local_mouse_pos', None) is not None:
                mx = self.local_mouse_pos.x()
                my = self.local_mouse_pos.y()
                if mx < 150:
                    influence = math.cos((mx / 150) * (math.pi / 2)) ** 2
                    start_y += (my - start_y) * 0.6 * influence

            path.moveTo(0, start_y)
            
            points_top = []
            for x in range(0, width + 10, 10):
                wave_val = math.sin(x * freq + phase) + 0.3 * math.sin(x * freq * 1.5 - phase * 0.8)
                y = mid_y + wave_val * amp
                
                # Mouse Interaction: Attract waves to the cursor
                if getattr(self, 'local_mouse_pos', None) is not None:
                    mx = self.local_mouse_pos.x()
                    my = self.local_mouse_pos.y()
                    dist_x = abs(x - mx)
                    if dist_x < 150:
                        influence = math.cos((dist_x / 150) * (math.pi / 2)) ** 2
                        y += (my - y) * 0.6 * influence
                        
                points_top.append((x, y))
                path.lineTo(x, y)
                
            # Bottom edge of ribbon
            thickness = 15 + (i * 12)
            for x, y in reversed(points_top):
                # Dynamic thickness for a 3D twist effect
                t = thickness * (0.6 + 0.4 * math.sin(x * 0.01 + phase * 1.5))
                path.lineTo(x, y + t)
                
            path.closeSubpath()
            
            # Gradient fill
            gradient = QLinearGradient(0, 0, width, height)
            base_c = self.current_colors[i]
            c1 = QColor(base_c)
            c2 = QColor(base_c)
            c2.setAlpha(int(base_c.alpha() * 0.4))
            
            gradient.setColorAt(0, c1)
            gradient.setColorAt(1, c2)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawPath(path)

    # --- Window Dragging & Mouse Interaction ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        self.local_mouse_pos = event.pos()
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()
        self.update()

    def leaveEvent(self, event):
        self.local_mouse_pos = None
        self.update()

    # --- Context Menu ---
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        
        # Styling the menu
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 5px;
            }
            QMenu::item {
                padding: 5px 20px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #313244;
            }
        """)

        # Add Actions
        toggle_nexa_action = QAction("Sleep Nexa" if self.nexa_active else "Wake Nexa", self)
        toggle_nexa_action.triggered.connect(self.toggle_nexa)
        context_menu.addAction(toggle_nexa_action)

        toggle_gestures_action = QAction("Disable Gestures" if self.gestures_active else "Enable Gestures", self)
        toggle_gestures_action.triggered.connect(self.toggle_gestures)
        context_menu.addAction(toggle_gestures_action)

        context_menu.addSeparator()

        shutdown_nexa_action = QAction("Shutdown Backend & Quit", self)
        shutdown_nexa_action.triggered.connect(self.shutdown_backend)
        context_menu.addAction(shutdown_nexa_action)

        quit_ui_action = QAction("Hide UI Orb Only", self)
        quit_ui_action.triggered.connect(self.close)
        context_menu.addAction(quit_ui_action)

        context_menu.exec_(QCursor.pos())

    # --- API Action Handlers ---
    def toggle_nexa(self):
        endpoint = "/nexa/close" if self.nexa_active else "/nexa/wake"
        threading.Thread(target=lambda: requests.post(f"{API_URL}{endpoint}")).start()
        self.poll_backend()

    def toggle_gestures(self):
        endpoint = "/gesture/stop" if self.gestures_active else "/gesture/start"
        threading.Thread(target=lambda: requests.post(f"{API_URL}{endpoint}")).start()
        self.poll_backend()

    def shutdown_backend(self):
        try:
            requests.post(f"{API_URL}/nexa/close", timeout=2)
        except Exception:
            pass
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Hide from taskbar
    app.setQuitOnLastWindowClosed(True)
    
    orb = NexaOrb()
    orb.show()
    
    # Position in bottom-center initially
    screen_geometry = QApplication.primaryScreen().availableGeometry()
    width = 600
    height = 100
    x = (screen_geometry.width() - width) // 2
    y = screen_geometry.height() - height - 40  # 40px padding from bottom
    orb.move(x, y)
    
    sys.exit(app.exec_())
