import sys
import os
import traceback
from datetime import datetime

# ==============================================================================
# GLOBAL CRASH LOGGER (Must be at the very top to catch early import errors)
# ==============================================================================
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Catches all unhandled exceptions and writes them to crash_log.txt"""
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
    with open(log_path, "a") as f:
        f.write(f"--- CRASH LOG: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        f.write("\n" + "=" * 50 + "\n\n")
    # Still print to console if one is open
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = global_exception_handler

import cv2
import time
import numpy as np
import mss
import keyboard
import ctypes
from datetime import datetime
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
        self.animation_delay = 1.8

    def run(self):
        self.frames = []
        elapsed = 0.0
        while elapsed < self.animation_delay and self.is_recording:
            time.sleep(0.1)
            elapsed += 0.1

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            while self.is_recording:
                img_np = np.array(sct.grab(monitor))
                self.frames.append(img_np)
                time.sleep(0.1)

        self.finished_signal.emit(self.frames)


# ---------------------------------------------------------
# GLOBAL HOTKEY LISTENER THREAD
# ---------------------------------------------------------
class HotkeyThread(QThread):
    toggle_signal = pyqtSignal()

    def run(self):
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

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        title = QLabel("Solution Verification")
        title.setObjectName("TitleText")

        btn_close = QPushButton("Clear & Close")
        btn_close.setObjectName("DangerBtn")
        btn_close.clicked.connect(self.hide)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.image_labels = []
        for i in range(24):
            lbl = QLabel()
            lbl.setFixedSize(60, 85)
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
        painter.setBrush(QColor(28, 28, 30, 240))
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

            self.lbl_status.setText("Recording...")
            self.lbl_status.setObjectName("StatusRecording")
            self.style().unpolish(self.lbl_status)
            self.style().polish(self.lbl_status)

            self.btn_toggle.setText("Stop & Process (F2)")
            self.btn_toggle.setObjectName("RecordBtnRecording")
            self.style().unpolish(self.btn_toggle)
            self.style().polish(self.btn_toggle)

            self.record_thread.is_recording = True
            self.record_thread.start()
        else:
            self.is_recording = False

            self.lbl_status.setText("Processing Buffer...")
            self.lbl_status.setObjectName("StatusRecording")
            self.style().unpolish(self.lbl_status)
            self.style().polish(self.lbl_status)

            self.btn_toggle.setText("Calculating Grid...")
            self.btn_toggle.setEnabled(False)

            self.record_thread.is_recording = False

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

            # Keep track of the frame with the most boxes for our debug image
            if len(filtered_boxes) > len(best_boxes):
                best_frame = frame.copy()
                best_boxes = list(filtered_boxes)

            # 1. ANCHOR FRAME FOUND
            if len(filtered_boxes) >= 14:
                print(
                    f"Anchor frame found at index {i} with {len(filtered_boxes)} raw boxes."
                )

                # 2. Calculate Medians & Centers
                widths = [b[2] for b in filtered_boxes]
                heights = [b[3] for b in filtered_boxes]
                median_w = int(np.median(widths))
                median_h = int(np.median(heights))

                cx_list = [b[0] + b[2] // 2 for b in filtered_boxes]
                cy_list = [b[1] + b[3] // 2 for b in filtered_boxes]

                # Helper Function: Cluster and Extrapolate
                def cluster_and_extrapolate(centers, target_count, max_bound):
                    centers = sorted(centers)
                    clusters = []
                    current_cluster = [centers[0]]

                    # Cluster centers within a 40px tolerance
                    for c in centers[1:]:
                        if c - current_cluster[-1] <= 40:
                            current_cluster.append(c)
                        else:
                            clusters.append(int(np.mean(current_cluster)))
                            current_cluster = [c]
                    clusters.append(int(np.mean(current_cluster)))

                    # Calculate median gap between valid adjacent clusters
                    if len(clusters) > 1:
                        gaps = [
                            clusters[idx + 1] - clusters[idx]
                            for idx in range(len(clusters) - 1)
                        ]
                        median_gap = int(np.median(gaps))
                    else:
                        median_gap = 200  # Safe fallback

                    # Fill missing INTERNAL gaps (e.g. if column 3 was completely missed)
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

                    # Fill missing EXTERNAL gaps (Leftmost or Rightmost columns)
                    while len(clusters) < target_count:
                        space_left = clusters[0]
                        space_right = max_bound - clusters[-1]

                        # Add to whichever side has more physical screen space
                        if space_left > space_right:
                            clusters.insert(0, int(clusters[0] - median_gap))
                        else:
                            clusters.append(int(clusters[-1] + median_gap))

                    return sorted(clusters)[:target_count]

                # 3 & 4. Extrapolate Columns (X) and Rows (Y)
                h_frame, w_frame = frame.shape[:2]
                cols = cluster_and_extrapolate(cx_list, 8, w_frame)
                rows = cluster_and_extrapolate(cy_list, 3, h_frame)

                # 5. Generate Master Grid
                for cy in rows:
                    for cx in cols:
                        x = int(cx - median_w / 2)
                        y = int(cy - median_h / 2)
                        # Ensure coordinates don't technically go off-screen
                        x = max(0, x)
                        y = max(0, y)
                        final_24_boxes.append((x, y, median_w, median_h))

                print("Mathematical Grid perfectly reconstructed from Anchor Frame.")
                break  # We generated the 24 mathematical boxes, stop searching!

        # 🌟 NEW: 1.5 MACRO / GLOBAL FRAME FILTERING 🌟
        clean_frames = []
        if frames:
            print("--- 1.5 Global Frame Filtering (Removing Text Animations) ---")
            h_full, w_full = frames[0].shape[:2]
            
            # Define a massive center region (middle 50% of the screen)
            cx1, cx2 = int(w_full * 0.25), int(w_full * 0.75)
            cy1, cy2 = int(h_full * 0.25), int(h_full * 0.75)
            center_area = (cx2 - cx1) * (cy2 - cy1)
            
            # HSV bounds for the golden/yellow "Ready" and "START" texts
            lower_yellow = np.array([10, 100, 120])
            upper_yellow = np.array([40, 255, 255])
            
            for f_idx, frame in enumerate(frames):
                center_roi = frame[cy1:cy2, cx1:cx2]
                
                # Convert to HSV
                bgr_roi = cv2.cvtColor(center_roi, cv2.COLOR_BGRA2BGR)
                hsv_roi = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2HSV)
                
                # Mask and count yellow pixels in the center of the screen
                yellow_mask = cv2.inRange(hsv_roi, lower_yellow, upper_yellow)
                yellow_ratio = cv2.countNonZero(yellow_mask) / center_area
                
                # If the center of the screen has a heavy concentration of yellow (>3%), 
                # it's the giant text animation. Discard the WHOLE frame.
                if yellow_ratio < 0.03:
                    clean_frames.append(frame)
                else:
                    print(f"Discarding Frame {f_idx}: Yellow Ratio in center is {yellow_ratio:.2%}")
            
            print(f"Filtered out {len(frames) - len(clean_frames)} corrupted frames. {len(clean_frames)} clean frames remaining.")
            
            # Fallback: Just in case a super short recording filters everything
            if not clean_frames:
                print("Warning: All frames were filtered. Reverting to the last recorded frame.")
                clean_frames = [frames[-1]]

        # 6. Smart Face-Up Extraction (Edge Complexity on CLEAN FRAMES)
        if final_24_boxes and clean_frames:
            print("--- 2. Smart Face-Up Extraction (Clean Edge Complexity) ---")
            best_card_images = []

            for idx, (x, y, w, h) in enumerate(final_24_boxes):
                highest_complexity = -1
                best_roi = None

                # 🌟 IMPORTANT: We now ONLY iterate through clean_frames!
                for frame in clean_frames:
                    roi = frame[y : y + h, x : x + w]

                    # Safety check in case a box was generated slightly out of bounds
                    if roi.size == 0:
                        continue

                    # Calculate total edge complexity using Canny
                    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGRA2GRAY)
                    blur_roi = cv2.GaussianBlur(gray_roi, (5, 5), 0)
                    canny_roi = cv2.Canny(blur_roi, 30, 150)

                    complexity = canny_roi.sum()

                    if complexity > highest_complexity:
                        highest_complexity = complexity
                        best_roi = roi.copy()

                if best_roi is None:
                    best_roi = (
                        clean_frames[-1][y : y + h, x : x + w].copy()
                        if clean_frames
                        else np.zeros((h, w, 4), dtype=np.uint8)
                    )

                best_card_images.append(best_roi)
                print(
                    f"Card {idx+1:02d}/24 extracted with Max Complexity: {highest_complexity:.2f}"
                )

            self.verification_window.display_cards(best_card_images)
            success = True

        # Status Update & Debug Export
        if success:
            self.lbl_status.setText("Success: Extracted 24 Cards!")
            self.lbl_status.setObjectName("StatusReady")
        else:
            self.lbl_status.setText("Error: Could not find Anchor Frame.")
            self.lbl_status.setObjectName("StatusWarning")

        # Draw the visual proof
        if best_frame is not None:
            debug_img = best_frame.copy()

            if success:
                # If we succeeded, draw the MATHEMATICALLY generated grid in NEON GREEN
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
                # If it utterly failed, draw the RAW detected boxes in RED so you can tune the sizes
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
            from datetime import datetime

            debug_dir = "debug_logs"
            os.makedirs(debug_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(debug_dir, f"debug_vision_{timestamp}.jpg")

            cv2.imwrite(filepath, debug_img)
            print(f"Debug image exported to: {os.path.abspath(filepath)}")

        self.style().unpolish(self.lbl_status)
        self.style().polish(self.lbl_status)

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

        self.btn_toggle.setText("Start Recording (F2)")
        self.btn_toggle.setObjectName("RecordBtnReady")
        self.btn_toggle.setEnabled(True)
        self.style().unpolish(self.btn_toggle)
        self.style().polish(self.btn_toggle)

    def close_app(self):
        self.record_thread.is_recording = False
        QApplication.quit()

# ---------------------------------------------------------
# UAC ELEVATION & MAIN EXECUTION
# ---------------------------------------------------------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    try:
        # 1. Auto-Request Administrator Privileges
        if not is_admin():
            print("Requesting Administrator privileges...")
            # Handles both running as a pure python script and as a compiled PyInstaller .exe
            if getattr(sys, "frozen", False):
                # Running as compiled executable
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1
                )
            else:
                # Running as a python script
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1
                )
            sys.exit()

        # 2. Start Application
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
        
    except Exception as e:
        # Failsafe logging just in case UI fails to initialize
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
        with open(log_path, "a") as f:
            f.write(f"--- INIT CRASH LOG: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            traceback.print_exc(file=f)
            f.write("\n" + "="*50 + "\n\n")
        raise