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

/* Dynamic Record Button States */
QPushButton#RecordBtnReady { background-color: #0A84FF; }
QPushButton#RecordBtnReady:hover { background-color: #007AFF; }
QPushButton#RecordBtnRecording { background-color: #FF9F0A; } /* Apple Orange */
QPushButton#RecordBtnRecording:hover { background-color: #FFB340; }
QPushButton:disabled { background-color: #555555; color: #AAAAAA; }

QPushButton#DangerBtn { background-color: #FF3B30; }
QPushButton#DangerBtn:hover { background-color: #FF453A; }

QLabel#TitleText { font-size: 18px; font-weight: 600; }
QLabel#SubText { font-size: 12px; color: #EBEBF5; }
QLabel#StatusReady { font-size: 14px; color: #32D74B; font-weight: bold; }
QLabel#StatusRecording { font-size: 14px; color: #FF9F0A; font-weight: bold; }
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

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("StatusReady")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Primary Action Button (Fallback for F2 Hotkey)
        self.btn_toggle = QPushButton("Start Recording (F2)")
        self.btn_toggle.setObjectName("RecordBtnReady")
        self.btn_toggle.clicked.connect(self.toggle_recording)

        btn_exit = QPushButton("Exit App")
        btn_exit.setObjectName("DangerBtn")
        btn_exit.clicked.connect(self.close_app)

        layout.addWidget(title)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.btn_toggle)
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

            # Update Label
            self.lbl_status.setText("Recording...")
            self.lbl_status.setObjectName("StatusRecording")
            self.style().unpolish(self.lbl_status)
            self.style().polish(self.lbl_status)

            # Update Button dynamically to Orange "Stop"
            self.btn_toggle.setText("Stop & Process (F2)")
            self.btn_toggle.setObjectName("RecordBtnRecording")
            self.style().unpolish(self.btn_toggle)
            self.style().polish(self.btn_toggle)

            self.record_thread.is_recording = True
            self.record_thread.start()
        else:
            self.is_recording = False

            # Update Label
            self.lbl_status.setText("Processing Buffer...")
            self.lbl_status.setObjectName("StatusRecording")
            self.style().unpolish(self.lbl_status)
            self.style().polish(self.lbl_status)

            # Update Button to Processing State and lock it
            self.btn_toggle.setText("Calculating Grid...")
            self.btn_toggle.setEnabled(False)

            self.record_thread.is_recording = False
            # Thread will naturally finish and emit the buffer to `process_buffer`

    def process_buffer(self, frames):
        if not frames:
            self.reset_status()
            return

        success = False
        best_frame = None
        best_boxes = []
        final_24_boxes = []

        print("--- 1. Mathematical Grid Reconstruction ---")
        for i, frame in enumerate(frames):
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

                if 0.60 <= aspect_ratio <= 0.75 and 150 < w < 400 and 200 < h < 550:
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

            if len(filtered_boxes) > len(best_boxes):
                best_frame = frame.copy()
                best_boxes = list(filtered_boxes)

            if len(filtered_boxes) >= 14:
                print(
                    f"Anchor frame found at index {i} with {len(filtered_boxes)} raw boxes."
                )
                widths = [b[2] for b in filtered_boxes]
                heights = [b[3] for b in filtered_boxes]
                median_w = int(np.median(widths))
                median_h = int(np.median(heights))

                cx_list = [b[0] + b[2] // 2 for b in filtered_boxes]
                cy_list = [b[1] + b[3] // 2 for b in filtered_boxes]

                def cluster_and_extrapolate(centers, target_count, max_bound):
                    centers = sorted(centers)
                    clusters = []
                    current_cluster = [centers[0]]

                    for c in centers[1:]:
                        if c - current_cluster[-1] <= 40:
                            current_cluster.append(c)
                        else:
                            clusters.append(int(np.mean(current_cluster)))
                            current_cluster = [c]
                    clusters.append(int(np.mean(current_cluster)))

                    if len(clusters) > 1:
                        gaps = [
                            clusters[idx + 1] - clusters[idx]
                            for idx in range(len(clusters) - 1)
                        ]
                        median_gap = int(np.median(gaps))
                    else:
                        median_gap = 200

                    while len(clusters) < target_count:
                        inserted = False
                        for idx in range(len(clusters) - 1):
                            if clusters[idx + 1] - clusters[idx] > 1.5 * median_gap:
                                clusters.insert(
                                    idx + 1, int(clusters[idx] + median_gap)
                                )
                                inserted = True
                                break
                        if not inserted:
                            break

                    while len(clusters) < target_count:
                        space_left = clusters[0]
                        space_right = max_bound - clusters[-1]
                        if space_left > space_right:
                            clusters.insert(0, int(clusters[0] - median_gap))
                        else:
                            clusters.append(int(clusters[-1] + median_gap))

                    return sorted(clusters)[:target_count]

                h_frame, w_frame = frame.shape[:2]
                cols = cluster_and_extrapolate(cx_list, 8, w_frame)
                rows = cluster_and_extrapolate(cy_list, 3, h_frame)

                for cy in rows:
                    for cx in cols:
                        x = int(cx - median_w / 2)
                        y = int(cy - median_h / 2)
                        x = max(0, x)
                        y = max(0, y)
                        final_24_boxes.append((x, y, median_w, median_h))

                print("Mathematical Grid perfectly reconstructed from Anchor Frame.")
                break

        # 6. Smart Face-Up Extraction (Mean Brightness)
        if final_24_boxes:
            print("--- 2. Smart Face-Up Extraction (HSV Brightness) ---")
            best_card_images = []

            for idx, (x, y, w, h) in enumerate(final_24_boxes):
                highest_brightness = -1
                best_roi = None

                for frame in frames:
                    roi = frame[y : y + h, x : x + w]

                    if roi.size == 0:
                        continue

                    bgr_roi = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)
                    hsv_roi = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2HSV)
                    brightness = hsv_roi[:, :, 2].mean()

                    if brightness > highest_brightness:
                        highest_brightness = brightness
                        best_roi = roi.copy()

                if best_roi is None:
                    best_roi = np.zeros((h, w, 4), dtype=np.uint8)

                best_card_images.append(best_roi)
                print(
                    f"Card {idx+1:02d}/24 extracted with Max Brightness: {highest_brightness:.2f}"
                )

            self.verification_window.display_cards(best_card_images)
            success = True

        # --- FINAL STATUS & UI RESET ---
        if success:
            self.lbl_status.setText("Success: Extracted 24 Cards!")
            self.lbl_status.setObjectName("StatusReady")
        else:
            self.lbl_status.setText("Error: Could not find Anchor.")
            self.lbl_status.setObjectName("StatusWarning")

        if best_frame is not None:
            debug_img = best_frame.copy()
            if success:
                for x, y, w, h in final_24_boxes:
                    cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(
                        debug_img,
                        f"Math {w}x{h}",
                        (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                    )
            else:
                for x, y, w, h in best_boxes:
                    cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(
                        debug_img,
                        f"Raw {w}x{h}",
                        (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),
                        1,
                    )

            import os

            cv2.imwrite("debug_vision.jpg", debug_img)
            print(f"Debug image exported to: {os.path.abspath('debug_vision.jpg')}")

        # Polish label styles
        self.style().unpolish(self.lbl_status)
        self.style().polish(self.lbl_status)

        # Completely unlock and reset the Main Action Button
        self.btn_toggle.setText("Start Recording (F2)")
        self.btn_toggle.setObjectName("RecordBtnReady")
        self.btn_toggle.setEnabled(True)
        self.style().unpolish(self.btn_toggle)
        self.style().polish(self.btn_toggle)

    def reset_status(self):
        self.lbl_status.setText("Ready")
        self.lbl_status.setObjectName("StatusReady")
        self.style().unpolish(self.lbl_status)
        self.style().polish(self.lbl_status)

        # Reset the Main Action Button
        self.btn_toggle.setText("Start Recording (F2)")
        self.btn_toggle.setObjectName("RecordBtnReady")
        self.btn_toggle.setEnabled(True)
        self.style().unpolish(self.btn_toggle)
        self.style().polish(self.btn_toggle)

    def close_app(self):
        self.record_thread.is_recording = False
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
