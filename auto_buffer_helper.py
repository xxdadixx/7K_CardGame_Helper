import sys
import cv2
import time
import numpy as np
import mss
import keyboard
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGridLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor

# ---------------------------------------------------------
# APPLE QSS STYLING
# ---------------------------------------------------------
APPLE_STYLE = """
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #FFFFFF;
}
QPushButton {
    background-color: #0A84FF;
    color: white;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: bold;
    border: none;
}
QPushButton:hover { background-color: #007AFF; }
QPushButton:pressed { background-color: #0056B3; }
QPushButton#DangerBtn { background-color: #FF3B30; }
QPushButton#DangerBtn:hover { background-color: #FF453A; }
QLabel#TitleText { font-size: 18px; font-weight: 600; }
QLabel#SubText { font-size: 12px; color: #EBEBF5; }
QLabel#StatusReady { font-size: 14px; color: #32D74B; font-weight: bold; }
QLabel#StatusRecording { font-size: 14px; color: #FF9F0A; font-weight: bold; } /* Apple Orange */
QLabel#StatusWarning { font-size: 14px; color: #FF3B30; font-weight: bold; }
"""

# ---------------------------------------------------------
# FRAME BUFFER RECORDING THREAD
# ---------------------------------------------------------
class RecordThread(QThread):
    finished_signal = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.frames = []
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1] # Primary monitor

    def run(self):
        self.frames = []
        # Capture frames at ~10 FPS to save RAM while recording
        while self.is_recording:
            img_np = np.array(self.sct.grab(self.monitor))
            self.frames.append(img_np)
            time.sleep(0.1) 
            
        self.finished_signal.emit(self.frames)

# ---------------------------------------------------------
# GLOBAL HOTKEY LISTENER THREAD
# ---------------------------------------------------------
class HotkeyThread(QThread):
    toggle_signal = pyqtSignal()
    
    def run(self):
        # We use a slight debounce to prevent double-firing
        while True:
            keyboard.wait('f2')
            self.toggle_signal.emit()
            time.sleep(0.3) 

# ---------------------------------------------------------
# SEPARATE VERIFICATION WINDOW (Glassmorphism)
# ---------------------------------------------------------
class VerificationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(APPLE_STYLE)
        
        # Base Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # Header (Title + Close Button)
        header_layout = QHBoxLayout()
        title = QLabel("Solution Verification")
        title.setObjectName("TitleText")
        
        btn_close = QPushButton("Clear & Close")
        btn_close.setObjectName("DangerBtn")
        btn_close.clicked.connect(self.hide)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)
        
        # 3x8 Grid Layout for Cards
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_labels = []
        for i in range(24):
            lbl = QLabel()
            lbl.setFixedSize(60, 85) # Scaled down nicely for UI
            lbl.setStyleSheet("background-color: rgba(255,255,255,0.05); border-radius: 6px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_labels.append(lbl)
            row, col = divmod(i, 8)
            self.grid_layout.addWidget(lbl, row, col)
            
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.grid_widget)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(28, 28, 30, 240)) # Solid translucent dark background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition().toPoint() - self.old_pos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPosition().toPoint()

    def display_cards(self, cards):
        for i, card_img in enumerate(cards):
            rgb_img = cv2.cvtColor(card_img, cv2.COLOR_BGRA2RGB)
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            scaled_pixmap = pixmap.scaled(60, 85, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_labels[i].setPixmap(scaled_pixmap)
        self.show()

# ---------------------------------------------------------
# MAIN CONTROL PANEL
# ---------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(APPLE_STYLE)
        
        self.is_recording = False
        self.verification_window = VerificationWindow()
        
        self.init_ui()
        self.init_threads()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        title = QLabel("7K AI Tracker")
        title.setObjectName("TitleText")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Press F2 to Start/Stop Buffer")
        subtitle.setObjectName("SubText")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("StatusReady")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_exit = QPushButton("Exit App")
        btn_exit.setObjectName("DangerBtn")
        btn_exit.clicked.connect(self.close_app)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.lbl_status)
        layout.addWidget(btn_exit)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(44, 44, 46, 240))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition().toPoint() - self.old_pos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPosition().toPoint()

    def init_threads(self):
        self.record_thread = RecordThread()
        self.record_thread.finished_signal.connect(self.process_buffer)
        
        self.hotkey_thread = HotkeyThread()
        self.hotkey_thread.toggle_signal.connect(self.toggle_recording)
        self.hotkey_thread.start()

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.lbl_status.setText("Recording... (Press F2 to Stop)")
            self.lbl_status.setObjectName("StatusRecording")
            self.style().unpolish(self.lbl_status)
            self.style().polish(self.lbl_status)
            
            self.record_thread.is_recording = True
            self.record_thread.start()
        else:
            self.is_recording = False
            self.lbl_status.setText("Processing Buffer...")
            self.lbl_status.setObjectName("StatusRecording")
            
            self.record_thread.is_recording = False
            # Thread will naturally finish and emit the buffer to `process_buffer`

    def process_buffer(self, frames):
        if not frames:
            self.reset_status()
            return

        success = False
        # Scan frames BACKWARDS. The clearest frame with all 24 cards 
        # is usually right before you hit stop.
        for frame in reversed(frames):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 30, 150)
            
            kernel = np.ones((3,3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            valid_boxes = []
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                aspect_ratio = w / float(h)
                
                # Aspect ratio ~0.685 (174/254)
                if 0.58 <= aspect_ratio <= 0.78 and 60 < w < 300 and 90 < h < 450:
                    valid_boxes.append((x, y, w, h))
            
            # Non-Maximum Suppression (Remove overlaps)
            filtered_boxes = []
            for box in valid_boxes:
                x1, y1, w1, h1 = box
                is_overlap = False
                for f_box in filtered_boxes:
                    x2, y2, w2, h2 = f_box
                    if abs((x1 + w1/2) - (x2 + w2/2)) < 30 and abs((y1 + h1/2) - (y2 + h2/2)) < 30:
                        is_overlap = True
                        break
                if not is_overlap:
                    filtered_boxes.append(box)

            # Did we find exactly 24 cards in this frame?
            if len(filtered_boxes) == 24:
                # Sort rows and columns
                filtered_boxes.sort(key=lambda b: b[1])
                row1 = sorted(filtered_boxes[0:8], key=lambda b: b[0])
                row2 = sorted(filtered_boxes[8:16], key=lambda b: b[0])
                row3 = sorted(filtered_boxes[16:24], key=lambda b: b[0])
                sorted_boxes = row1 + row2 + row3

                # Extract the 24 images
                cards = [frame[y:y+h, x:x+w] for (x, y, w, h) in sorted_boxes]
                
                # Display in the separate Verification Window
                self.verification_window.display_cards(cards)
                success = True
                break # We found our golden frame, stop processing

        if success:
            self.lbl_status.setText("Success: Found 24 Cards!")
            self.lbl_status.setObjectName("StatusReady")
        else:
            self.lbl_status.setText("Warning: Frame not found. Try again.")
            self.lbl_status.setObjectName("StatusWarning")
            
        self.style().unpolish(self.lbl_status)
        self.style().polish(self.lbl_status)

    def reset_status(self):
        self.lbl_status.setText("Ready")
        self.lbl_status.setObjectName("StatusReady")
        self.style().unpolish(self.lbl_status)
        self.style().polish(self.lbl_status)

    def close_app(self):
        self.record_thread.is_recording = False
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())