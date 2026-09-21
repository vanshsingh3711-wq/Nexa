import sys, math
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QPen, QImage

app = QApplication(sys.argv)
width = 600
height = 120
img = QImage(width, height, QImage.Format_ARGB32)
img.fill(QColor(25, 25, 25, 255))

painter = QPainter(img)
painter.setRenderHint(QPainter.Antialiasing)
painter.setRenderHint(QPainter.HighQualityAntialiasing)

mid_y = height / 2
c1, c2 = QColor(255, 69, 0), QColor(255, 20, 147) # Hot pink/orange for testing
amplitude_mult = 1.5
wave_phase = 1.0

num_lines = 5
for i in range(num_lines):
    wave_path = QPainterPath()
    
    # 5 distinct lines, some fast, some slow, some tall, some short
    # i=0 is the main center wave
    K = 4.0 if i % 2 == 0 else -4.0  # spatial frequency
    speed = 0.2 + (i * 0.1)
    phase_offset = wave_phase * speed
    
    # attenuation
    attenuation = 1.0 - (i * 0.15)
    max_amp = (height / 2 - 10) * amplitude_mult * attenuation
    
    # Ensure it doesn't exceed height/2
    max_amp = min(max_amp, height / 2 - 5)
    
    wave_path.moveTo(0, mid_y)
    
    for x in range(0, width + 2, 2):
        # map x to [-2.5, 2.5]
        x_norm = ((x / width) * 2.0 - 1.0) * 2.5
        
        # Gaussian envelope
        envelope = math.exp(-(x_norm ** 2))
        
        # Sine wave
        wave_val = math.sin(K * x_norm + phase_offset)
        
        y = mid_y + (max_amp * envelope * wave_val)
        
        wave_path.lineTo(x, y)
        
    pen = QPen()
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    
    # Thicker for the main wave
    pen.setWidthF(2.0 if i == 0 else 1.2)
    
    ratio = i / max(1, num_lines - 1)
    r = int(c1.red() * (1 - ratio) + c2.red() * ratio)
    g = int(c1.green() * (1 - ratio) + c2.green() * ratio)
    b = int(c1.blue() * (1 - ratio) + c2.blue() * ratio)
    a = 255 if i == 0 else 180
    
    pen.setColor(QColor(r, g, b, a))
    painter.setPen(pen)
    painter.drawPath(wave_path)

painter.end()
img.save("test_waves_3.png")
