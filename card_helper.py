import sys
import cv2
import numpy as np
import mss
import keyboard
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGridLayout,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont

# ---------------------------------------------------------
# APPLE QSS STYLING (Dark Mode Glassmorphism)
# ---------------------------------------------------------
APPLE_STYLE = """
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #FFFFFF;
}
QPushButton {
    background-color: #0A84FF; /* Apple Blue */
    color: white;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: bold;
    border: none;
}
QPushButton:hover {
    background-color: #007AFF;
}
QPushButton:pressed {
    background-color: #0056B3;
}
QLabel#TitleText {
    font-size: 18px;
    font-weight: 600;
}
QLabel#SubText {
    font-size: 12px;
    color: #EBEBF5; /* iOS Secondary Text */
}
"""


# ---------------------------------------------------------
# GLOBAL HOTKEY THREAD (Prevents UI Freezing)
# ---------------------------------------------------------
class HotkeyThread(QThread):
    capture_signal = pyqtSignal()

    def run(self):
        # Trigger the capture signal when F2 is pressed
        keyboard.add_hotkey("f2", lambda: self.capture_signal.emit())
        keyboard.wait()


# ---------------------------------------------------------
# GRID OVERLAY (To select the game region)
# ---------------------------------------------------------
class GridOverlay(QWidget):
    def __init__(self):
        super().__init__()
        # Frameless and translucent for the overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 800, 300)  # Default starting size
        self.is_active = False

    def paintEvent(self, event):
        if not self.is_active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark background for the overlay area
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # Apple-blue glowing grid lines
        pen = QPen(QColor(10, 132, 255, 200))
        pen.setWidth(2)
        painter.setPen(pen)

        w = self.width()
        h = self.height()

        # Draw 3x8 Grid
        for row in range(1, 3):
            y = int(h * (row / 3))
            painter.drawLine(0, y, w, y)
        for col in range(1, 8):
            x = int(w * (col / 8))
            painter.drawLine(x, 0, x, h)

        # Draw Border
        pen.setWidth(4)
        painter.setPen(pen)
        painter.drawRect(0, 0, w, h)

    # Allow dragging the overlay to position it over the game
    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition().toPoint() - self.old_pos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPosition().toPoint()


# ---------------------------------------------------------
# SOLUTION SCREEN (Glassmorphic Result Window)
# ---------------------------------------------------------
class SolutionScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.layout = QGridLayout(self)
        self.layout.setSpacing(8)  # Space between cards
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.image_labels = []

        for i in range(24):
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "background-color: rgba(255,255,255,0.1); border-radius: 8px;"
            )
            self.image_labels.append(lbl)
            row, col = divmod(i, 8)
            self.layout.addWidget(lbl, row, col)

    def paintEvent(self, event):
        # iOS-style Glassmorphism background (Dark Blur Simulation)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(28, 28, 30, 230))  # Translucent dark gray
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)  # 20px rounded corners

    def display_cards(self, cards):
        for i, card_img in enumerate(cards):
            # Convert OpenCV BGRA to RGB, then to QPixmap
            rgb_img = cv2.cvtColor(card_img, cv2.COLOR_BGRA2RGB)
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            q_img = QImage(
                rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
            )
            pixmap = QPixmap.fromImage(q_img)

            # Scale slightly for nice UI presentation
            scaled_pixmap = pixmap.scaled(
                80,
                80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_labels[i].setPixmap(scaled_pixmap)

        self.show()


# ---------------------------------------------------------
# MAIN CONTROL WINDOW
# ---------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(APPLE_STYLE)

        self.overlay = GridOverlay()
        self.solution_screen = SolutionScreen()
        self.sct = mss.mss()

        self.init_ui()
        self.init_hotkeys()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("7K Rebirth Helper")
        title.setObjectName("TitleText")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Press F2 to Capture Cards")
        subtitle.setObjectName("SubText")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_toggle_grid = QPushButton("Show Grid Overlay")
        self.btn_toggle_grid.clicked.connect(self.toggle_grid)

        self.btn_close = QPushButton("Exit")
        self.btn_close.setStyleSheet("background-color: #FF3B30;")  # Apple Red
        self.btn_close.clicked.connect(self.close_app)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.btn_toggle_grid)
        layout.addWidget(self.btn_close)

    def paintEvent(self, event):
        # Apple Control Panel Background
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

    def toggle_grid(self):
        if self.overlay.is_active:
            self.overlay.is_active = False
            self.overlay.hide()
            self.btn_toggle_grid.setText("Show Grid Overlay")
        else:
            self.overlay.is_active = True
            self.overlay.show()
            self.btn_toggle_grid.setText("Hide Grid Overlay")

    def init_hotkeys(self):
        self.hotkey_thread = HotkeyThread()
        self.hotkey_thread.capture_signal.connect(self.trigger_capture)
        self.hotkey_thread.start()

    def trigger_capture(self):
        # Hide overlay temporarily if it's visible so it doesn't get captured
        grid_was_active = self.overlay.is_active
        if grid_was_active:
            self.overlay.hide()

        # Get coordinates of the overlay box
        rect = self.overlay.geometry()
        monitor = {
            "top": rect.y(),
            "left": rect.x(),
            "width": rect.width(),
            "height": rect.height(),
        }

        # Capture the defined screen region
        img = np.array(self.sct.grab(monitor))

        if grid_was_active:
            self.overlay.show()

        # Slice image into 3x8 grid
        self.cards = []
        h, w = img.shape[:2]
        cell_h, cell_w = h // 3, w // 8

        for r in range(3):
            for c in range(8):
                card = img[r * cell_h : (r + 1) * cell_h, c * cell_w : (c + 1) * cell_w]
                self.cards.append(card)

        # Simulate the wait for the last card to flip down (e.g., 3000ms = 3 seconds)
        # You can adjust this timer to perfectly match the game's animation speed
        QTimer.singleShot(3000, self.show_solution)

    def show_solution(self):
        # Position the solution screen slightly below the capture area
        rect = self.overlay.geometry()
        self.solution_screen.setGeometry(
            rect.x(), rect.y() + rect.height() + 20, rect.width(), rect.height()
        )
        self.solution_screen.display_cards(self.cards)

    def close_app(self):
        self.sct.close()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
