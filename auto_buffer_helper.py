import sys
import cv2
import time
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
        # Removed mss initialization from the main thread context

    def run(self):
        self.frames = []

        # Initialize mss inside the worker thread context using a context manager
        with mss.mss() as sct:
            # Grab the primary monitor (index 1 is usually the primary display)
            monitor = sct.monitors[1]

            # Capture frames at ~10 FPS to save RAM while recording
            while self.is_recording:
                img_np = np.array(sct.grab(monitor))
                self.frames.append(img_np)
                time.sleep(0.1)

        # Emit the buffered frames once recording is stopped and mss cleans up
        self.finished_signal.emit(self.frames)


# ---------------------------------------------------------
# GLOBAL HOTKEY LISTENER THREAD
# ---------------------------------------------------------
class HotkeyThread(QThread):
    toggle_signal = pyqtSignal()

    def run(self):
        # We use a slight debounce to prevent double-firing
        while True:
            keyboard.wait("f2")
            self.toggle_signal.emit()
            time.sleep(0.3)


# ---------------------------------------------------------
# SEPARATE VERIFICATION WINDOW (Glassmorphism)
# ---------------------------------------------------------
class VerificationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
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
            lbl.setFixedSize(60, 85)  # Scaled down nicely for UI
            lbl.setStyleSheet(
                "background-color: rgba(255,255,255,0.05); border-radius: 6px;"
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_labels.append(lbl)
            row, col = divmod(i, 8)
            self.grid_layout.addWidget(lbl, row, col)

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.grid_widget)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(28, 28, 30, 240))  # Solid translucent dark background
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
            q_img = QImage(
                rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
            )
            pixmap = QPixmap.fromImage(q_img)
            scaled_pixmap = pixmap.scaled(
                60,
                85,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_labels[i].setPixmap(scaled_pixmap)
        self.show()


# ---------------------------------------------------------
# MAIN CONTROL PANEL
# ---------------------------------------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
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
        best_frame = None
        best_boxes = []
        best_diff = float("inf")  # Track how close we got to 24

        print("--- Starting Frame Analysis ---")
        for i, frame in enumerate(reversed(frames)):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 30, 150)

            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            valid_boxes = []
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                aspect_ratio = w / float(h)

                # Widened tolerances: Aspect ratio ~0.50 to 0.85
                if 0.50 <= aspect_ratio <= 0.85 and 40 < w < 400 and 60 < h < 600:
                    valid_boxes.append((x, y, w, h))

            # Non-Maximum Suppression (Filter overlaps)
            filtered_boxes = []
            for box in valid_boxes:
                x1, y1, w1, h1 = box
                is_overlap = False
                for f_box in filtered_boxes:
                    x2, y2, w2, h2 = f_box
                    if (
                        abs((x1 + w1 / 2) - (x2 + w2 / 2)) < 30
                        and abs((y1 + h1 / 2) - (y2 + h2 / 2)) < 30
                    ):
                        is_overlap = True
                        break
                if not is_overlap:
                    filtered_boxes.append(box)

            print(
                f"Frame {i}: Contours: {len(contours)} | Valid: {len(valid_boxes)} | NMS Filtered: {len(filtered_boxes)}"
            )

            # Keep track of the "best" frame for our debug image
            diff = abs(len(filtered_boxes) - 24)
            if diff < best_diff:
                best_diff = diff
                best_frame = frame.copy()
                best_boxes = list(filtered_boxes)

            # SMART GRID EXTRACTION HEURISTIC
            if len(filtered_boxes) >= 24:
                # 1. Sort all boxes top-to-bottom (by Y coordinate)
                sorted_by_y = sorted(filtered_boxes, key=lambda b: b[1])

                # 2. Group into rows. If Y difference is small (<50px), it's the same row.
                rows = []
                current_row = [sorted_by_y[0]]
                for box in sorted_by_y[1:]:
                    if abs(box[1] - current_row[-1][1]) < 50:
                        current_row.append(box)
                    else:
                        rows.append(current_row)
                        current_row = [box]
                rows.append(current_row)

                # 3. Filter out any rows that don't have at least 8 elements
                valid_rows = [r for r in rows if len(r) >= 8]

                # 4. Do we have at least 3 valid rows?
                if len(valid_rows) >= 3:
                    # Take exactly the first 3 rows (in case game UI triggered a 4th row at the bottom)
                    valid_rows = sorted(
                        valid_rows, key=lambda r: np.mean([b[1] for b in r])
                    )[:3]

                    final_24_boxes = []
                    for r in valid_rows:
                        # Sort the row left-to-right (by X coordinate)
                        sorted_x = sorted(r, key=lambda b: b[0])

                        # If the row has more than 8 boxes, drop the ones with anomalous widths
                        if len(sorted_x) > 8:
                            median_w = np.median([b[2] for b in sorted_x])
                            # Keep the 8 boxes closest to the median width
                            sorted_x = sorted(
                                sorted_x, key=lambda b: abs(b[2] - median_w)
                            )[:8]
                            # Re-sort left-to-right
                            sorted_x = sorted(sorted_x, key=lambda b: b[0])

                        final_24_boxes.extend(sorted_x)

                    if len(final_24_boxes) == 24:
                        cards = [
                            frame[y : y + h, x : x + w]
                            for (x, y, w, h) in final_24_boxes
                        ]
                        self.verification_window.display_cards(cards)
                        success = True
                        break  # We found our golden frame!

        # STATUS UPDATES & DEBUG EXPORT
        if success:
            self.lbl_status.setText("Success: Found 24 Cards!")
            self.lbl_status.setObjectName("StatusReady")
        else:
            self.lbl_status.setText("Warning: See debug_vision.jpg")
            self.lbl_status.setObjectName("StatusWarning")

            # Draw rectangles on the best frame and save it
            if best_frame is not None:
                debug_img = best_frame.copy()
                for x, y, w, h in best_boxes:
                    cv2.rectangle(
                        debug_img, (x, y), (x + w, y + h), (0, 0, 255), 2
                    )  # Red bounding box
                    # Write the dimensions above the box for easy tuning
                    cv2.putText(
                        debug_img,
                        f"{w}x{h}",
                        (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        1,
                    )

                import os

                cv2.imwrite("debug_vision.jpg", debug_img)
                print(f"Debug image exported to: {os.path.abspath('debug_vision.jpg')}")

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
