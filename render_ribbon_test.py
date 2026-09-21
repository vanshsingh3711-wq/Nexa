import sys, math
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QImage, QLinearGradient

app = QApplication(sys.argv)
width = 600
height = 100
img = QImage(width, height, QImage.Format_ARGB32)
img.fill(QColor(0, 0, 0, 0)) # Fully transparent background

painter = QPainter(img)
painter.setRenderHint(QPainter.Antialiasing)

mid_y = height / 2
wave_phase = 1.0

# 4 flowing overlapping ribbons
num_ribbons = 4

# Base colors for Blue (active state)
colors = [
    QColor(0, 90, 200, 180),   # Deep Blue
    QColor(0, 150, 255, 140),  # Bright Blue
    QColor(0, 200, 255, 110),  # Cyan
    QColor(50, 100, 255, 160)  # Indigo
]

for i in range(num_ribbons):
    path = QPainterPath()
    
    freq = 0.005 + (i * 0.0015)
    phase = i * 2.1 + wave_phase
    
    # Let amplitude scale with height, ribbons go slightly off-center
    amp = (height / 2.5) + (i * 2.0)
    
    # Top edge of ribbon
    start_y = mid_y + math.sin(phase) * amp
    path.moveTo(0, start_y)
    
    points_top = []
    for x in range(0, width + 10, 10):
        # We use a combined sine wave for organic non-repeating flow
        wave_val = math.sin(x * freq + phase) + 0.3 * math.sin(x * freq * 1.5 - phase * 0.8)
        y = mid_y + wave_val * amp
        points_top.append((x, y))
        path.lineTo(x, y)
        
    # Bottom edge of ribbon (slightly thicker in the middle)
    thickness = 15 + (i * 12)
    for x, y in reversed(points_top):
        # Dynamic thickness based on wave phase to give a 3D twist effect
        t = thickness * (0.6 + 0.4 * math.sin(x * 0.01 + phase * 1.5))
        path.lineTo(x, y + t)
        
    path.closeSubpath()
    
    # Create gradient fill
    gradient = QLinearGradient(0, 0, width, height)
    base_c = colors[i]
    c1 = QColor(base_c)
    c2 = QColor(base_c)
    c2.setAlpha(int(base_c.alpha() * 0.4)) # Fade out slightly
    
    gradient.setColorAt(0, c1)
    gradient.setColorAt(1, c2)
    
    painter.setPen(Qt.NoPen)
    painter.setBrush(gradient)
    painter.drawPath(path)

painter.end()
img.save("test_ribbons_2.png")
