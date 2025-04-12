from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

class LoadingAnimation(QWidget):
    def __init__(self, parent=None, text="Loading..."):
        super().__init__(parent)
        self.text = text
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(50)  # Update every 50ms
        self.setVisible(False)
        
        # Set up layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setFixedWidth(200)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add text label
        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.text_label)
        
        self.setLayout(layout)
        
        # Set background color to make it stand out
        self.setStyleSheet("background-color: rgba(255, 255, 255, 200); border-radius: 10px;")
    
    def rotate(self):
        self.angle = (self.angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw spinning circle
        center = self.rect().center()
        radius = min(self.width(), self.height()) // 4
        
        # Draw outer circle
        painter.setPen(QPen(QColor(0, 120, 215), 3))  # Blue color, thicker line
        painter.drawEllipse(center.x() - radius, center.y() - radius, 
                        radius * 2, radius * 2)
        
        # Draw spinning arc
        painter.setPen(QPen(QColor(0, 120, 215), 5))  # Blue color, even thicker line
        painter.drawArc(center.x() - radius, center.y() - radius, 
                        radius * 2, radius * 2, 
                        self.angle * 16, 270 * 16)
        
        # Draw center dot
        painter.setBrush(QBrush(QColor(0, 120, 215)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, 5, 5)
    
    def setText(self, text):
        self.text = text
        self.text_label.setText(text)
    
    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)
    
    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event) 