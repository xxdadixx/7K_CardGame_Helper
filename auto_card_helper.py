import sys
import cv2
import numpy as np
import mss
import keyboard
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QGridLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor

# ---------------------------------------------------------
# APPLE QSS STYLING (Dark Mode Glassmorphism)
# ---------------------------------------------------------
APPLE_STYLE = """
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
QPushButton#ExitBtn { background-color: #FF3B30; }
QPushButton#ExitBtn:hover { background-color: #FF453A; }
QLabel#TitleText { font-size: 18px; font-weight: 600; }
QLabel#SubText { font-size: 12px; color: #EBEBF5; }
QLabel#StatusReady { font-size: 13px; color: #32D74B; font-weight: bold; } /* Apple Green */
QLabel#StatusWarning { font-size: 13px; color: #FF453A; font-weight: bold; } /* Apple Red */
"""

class HotkeyThread(QThread):
    capture_signal = pyqtSignal()
    
    def run(self):
        keyboard.add_hotkey('f2', lambda: self.capture_signal.emit())
        keyboard.wait()

class SolutionScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QGridLayout(self)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.image_labels = []
        
        for i in range(24):
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("background-color: rgba(255,255,255,0.05); border-radius: 8px;")
            self.image_labels.append(lbl)
            row, col = divmod(i, 8)
            self.layout.addWidget(lbl, row, col)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(28, 28, 30, 220)) # Translucent dark gray
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def display_solution(self, cards, geometry):
        self.setGeometry(geometry[0], geometry[1], geometry[2], geometry[3])
        
        for i, card_img in enumerate(cards):
            rgb_img = cv2.cvtColor(card_img, cv2.COLOR_BGRA2RGB)
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            
            # Scale dynamically based on the label size
            lbl_size = self.image_labels[i].size()
            scaled_pixmap = pixmap.scaled(lbl_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_labels[i].setPixmap(scaled_pixmap)
        
        self.show()

    def mousePressEvent(self, event):
        # Click anywhere on the solution screen to hide it
        self.hide()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(APPLE_STYLE)
        
        self.solution_screen = SolutionScreen()
        self.sct = mss.mss()
        
        self.init_ui()
        self.init_hotkeys()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        title = QLabel("7K Rebirth Helper")
        title.setObjectName("TitleText")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Press F2 to Auto-Scan Cards")
        subtitle.setObjectName("SubText")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("StatusReady")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_close = QPushButton("Exit")
        btn_close.setObjectName("ExitBtn")
        btn_close.clicked.connect(self.close_app)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.lbl_status)
        layout.addWidget(btn_close)
        
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

    def init_hotkeys(self):
        self.hotkey_thread = HotkeyThread()
        self.hotkey_thread.capture_signal.connect(self.trigger_capture)
        self.hotkey_thread.start()

    def trigger_capture(self):
        self.lbl_status.setText("Scanning...")
        self.lbl_status.setObjectName("StatusReady")
        self.style().unpolish(self.lbl_status)
        self.style().polish(self.lbl_status)
        
        # Capture primary monitor
        monitor = self.sct.monitors[1]
        img_np = np.array(self.sct.grab(monitor))
        
        success, msg, cards, geometry = self.extract_cards(img_np)
        
        if not success:
            self.lbl_status.setText(msg)
            self.lbl_status.setObjectName("StatusWarning")
            self.style().unpolish(self.lbl_status)
            self.style().polish(self.lbl_status)
            return
            
        self.lbl_status.setText(msg)
        self.lbl_status.setObjectName("StatusReady")
        self.style().unpolish(self.lbl_status)
        self.style().polish(self.lbl_status)
        
        self.cards = cards
        self.solution_geom = geometry
        
        # 3-second delay to match the game's flip-down animation
        QTimer.singleShot(3000, self.show_solution)

    def extract_cards(self, img_np):
        gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 30, 150)
        
        # Dilate slightly to connect broken lines around card edges
        kernel = np.ones((3,3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_boxes = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            aspect_ratio = w / float(h)
            
            # Target aspect ratio is 174/254 (~0.685). We allow a safe range.
            if 0.58 <= aspect_ratio <= 0.78 and 60 < w < 300 and 90 < h < 450:
                valid_boxes.append((x, y, w, h))
                
        # Non-Maximum Suppression (Filter overlapping/duplicate boxes)
        filtered_boxes = []
        for box in valid_boxes:
            x1, y1, w1, h1 = box
            is_overlap = False
            for f_box in filtered_boxes:
                x2, y2, w2, h2 = f_box
                # Check center proximity
                if abs((x1 + w1/2) - (x2 + w2/2)) < 30 and abs((y1 + h1/2) - (y2 + h2/2)) < 30:
                    is_overlap = True
                    break
            if not is_overlap:
                filtered_boxes.append(box)

        # Validation: Did we find exactly 24 cards?
        if len(filtered_boxes) != 24:
            return False, f"Warning: Found {len(filtered_boxes)} cards, expected 24. Try again.", [], None

        # Sort the 24 cards perfectly (Top to Bottom, Left to Right)
        filtered_boxes.sort(key=lambda b: b[1]) # Sort globally by Y (Rows)
        row1 = sorted(filtered_boxes[0:8], key=lambda b: b[0]) # Sort Row 1 by X
        row2 = sorted(filtered_boxes[8:16], key=lambda b: b[0]) # Sort Row 2 by X
        row3 = sorted(filtered_boxes[16:24], key=lambda b: b[0]) # Sort Row 3 by X
        sorted_boxes = row1 + row2 + row3

        # Extract images
        cards = [img_np[y:y+h, x:x+w] for (x, y, w, h) in sorted_boxes]
        
        # Calculate full UI geometry to overlay perfectly on top of the game client
        min_x = min([b[0] for b in sorted_boxes]) - 10
        min_y = min([b[1] for b in sorted_boxes]) - 10
        max_x = max([b[0]+b[2] for b in sorted_boxes]) + 10
        max_y = max([b[1]+b[3] for b in sorted_boxes]) + 10
        geometry = (min_x, min_y, max_x - min_x, max_y - min_y)

        return True, "Success! Intercepted 24 cards.", cards, geometry

    def show_solution(self):
        self.solution_screen.display_solution(self.cards, self.solution_geom)

    def close_app(self):
        self.sct.close()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())