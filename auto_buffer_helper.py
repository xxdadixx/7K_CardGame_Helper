import sys
import os
import traceback
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

        print("--- 0. Filtering Game UI Text Overlays ---")
        clean_frames = []
        global_bright_scores = []

        # Analyze the center of the screen where giant text usually appears
        for f in frames:
            h, w = f.shape[:2]
            center_roi = f[int(h * 0.3) : int(h * 0.7), int(w * 0.2) : int(w * 0.8)]
            gray = cv2.cvtColor(center_roi, cv2.COLOR_BGRA2GRAY)

            # Count intensely bright pixels (Yellow/White text)
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            global_bright_scores.append(cv2.countNonZero(binary))

        # Find the baseline brightness and filter out massive spikes
        median_bright = np.median(global_bright_scores)
        spike_threshold = max(median_bright * 2.5, 2000)

        for f, score in zip(frames, global_bright_scores):
            # Keep only frames without the massive bright text overlay
            if score < spike_threshold:
                clean_frames.append(f)

        if len(clean_frames) >= 5:
            print(
                f"Removed {len(frames) - len(clean_frames)} polluted frames. Proceeding with {len(clean_frames)} clean frames."
            )
            frames = clean_frames
        else:
            print(
                "Warning: Filter was too aggressive. Using the last 40% of frames as fallback."
            )
            keep = max(5, int(len(frames) * 0.4))
            frames = frames[-keep:]

        success = False
        best_frame = None if not frames else frames[len(frames) // 2].copy()
        best_boxes = []
        final_24_boxes = []

        print("--- 1. Mathematical Grid Reconstruction (Accumulated Strategy) ---")

        box_clusters = []  # Store unique locations and their detection counts

        # Step 1.1: Collect all possible card boxes across ALL frames
        for i, frame in enumerate(frames):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 30, 150)

            # Morphological Closing to fix broken lines from game effects
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            edges = cv2.dilate(edges, kernel, iterations=1)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                aspect_ratio = w / float(h) if h != 0 else 0

                # --- MODIFIED: Extreme relaxed constraints for ultra-squished windows ---
                # Aspect Ratio broadened to 0.15 - 1.20 (Supports extreme pillar-like thin cards)
                # Minimum size lowered to 15x30 to support the smallest window modes
                if 0.15 <= aspect_ratio <= 1.20 and 15 < w < 600 and 30 < h < 1000:
                    is_overlap = False

                    # Group boxes that appear in the same physical screen location
                    for cluster in box_clusters:
                        x2, y2, w2, h2 = cluster["box"]

                        # Use dynamic tolerance (40% of box size) instead of fixed px to handle jitters
                        if abs((x + w / 2) - (x2 + w2 / 2)) < (w * 0.4) and abs(
                            (y + h / 2) - (y2 + h2 / 2)
                        ) < (h * 0.4):
                            # Update moving average for robust coordinate stability
                            n = cluster["count"]
                            new_x = int((x + x2 * n) / (n + 1))
                            new_y = int((y + y2 * n) / (n + 1))
                            new_w = int((w + w2 * n) / (n + 1))
                            new_h = int((h + h2 * n) / (n + 1))

                            cluster["box"] = (new_x, new_y, new_w, new_h)
                            cluster["count"] += 1
                            is_overlap = True
                            break

                    if not is_overlap:
                        box_clusters.append({"box": (x, y, w, h), "count": 1})

        # Step 1.2: Filter out transient boxes (noise that appeared in less than 3 frames)
        filtered_boxes = [c["box"] for c in box_clusters if c["count"] >= 3]
        best_boxes = list(filtered_boxes)

        # Step 1.3: Generate Master Grid if enough valid anchors are found across the timeline
        if len(filtered_boxes) >= 6:
            print(
                f"Accumulated grid positions found: {len(filtered_boxes)} unique slots over time."
            )

            widths = [b[2] for b in filtered_boxes]
            heights = [b[3] for b in filtered_boxes]
            median_w = int(np.median(widths))
            median_h = int(np.median(heights))

            cx_list = [b[0] + b[2] // 2 for b in filtered_boxes]
            cy_list = [b[1] + b[3] // 2 for b in filtered_boxes]

            # Helper Function: Hit-Based Voting & Pairwise Gap Analysis
            def cluster_and_fit_grid(centers, target_count, card_size, frame_dim):
                if not centers:
                    return []

                # 1. Group extremely close centers to remove micro-jitters
                centers = sorted(centers)
                clusters = []
                current_cluster = [centers[0]]

                for c in centers[1:]:
                    if c - current_cluster[-1] <= card_size * 0.3:
                        current_cluster.append(c)
                    else:
                        clusters.append(int(np.mean(current_cluster)))
                        current_cluster = [c]
                clusters.append(int(np.mean(current_cluster)))

                # 🌟 2. THE ULTIMATE GAP FINDER (Pairwise Distance Analysis) 🌟
                # Measure distance between EVERY pair of clusters, not just adjacent ones.
                # This bypasses noise completely (e.g. noise inserted between Row 1 and Row 2).
                all_gaps = []
                for i in range(len(clusters)):
                    for j in range(i + 1, len(clusters)):
                        dist = clusters[j] - clusters[i]
                        all_gaps.append(dist)

                # A valid 1x gap is roughly between 0.8x and 1.8x the card size.
                single_gaps = [
                    g for g in all_gaps if card_size * 0.8 <= g <= card_size * 1.8
                ]

                if single_gaps:
                    median_gap = int(np.median(single_gaps))
                else:
                    median_gap = int(card_size * 1.15)  # Safe fallback

                # 3. Slide the template grid to find the Max Hits
                best_base_offset = clusters[0]
                max_hits = -1
                min_error = float("inf")
                best_center_dist = float("inf")

                for c in clusters:
                    for offset_idx in range(target_count):
                        test_base = c - (offset_idx * median_gap)

                        hits = 0
                        error = 0
                        for expected_idx in range(target_count):
                            expected_pos = test_base + (expected_idx * median_gap)
                            dists = [abs(expected_pos - cl) for cl in clusters]
                            min_dist = min(dists) if dists else float("inf")

                            # If a detected card aligns with a grid line, it's a hit!
                            if min_dist < card_size * 0.3:
                                hits += 1
                            error += min_dist

                        # Calculate distance to screen center to break ties
                        grid_center = test_base + (target_count - 1) * median_gap / 2.0
                        center_dist = abs(grid_center - (frame_dim / 2.0))

                        # Rules: 1. Maximize Hits  2. Minimize Error  3. Tie-breaker: Closest to Screen Center
                        if hits > max_hits:
                            max_hits = hits
                            min_error = error
                            best_center_dist = center_dist
                            best_base_offset = test_base
                        elif hits == max_hits:
                            if error < min_error - 10:
                                min_error = error
                                best_center_dist = center_dist
                                best_base_offset = test_base
                            elif abs(error - min_error) <= 10:
                                if center_dist < best_center_dist:
                                    min_error = error
                                    best_center_dist = center_dist
                                    best_base_offset = test_base

                return [
                    int(best_base_offset + i * median_gap) for i in range(target_count)
                ]

            # --- 🌟 โค้ดที่ต้องนำมาเติม (RESTORE MISSING CODE) 🌟 ---
            h_frame, w_frame = frames[0].shape[:2]

            cols = cluster_and_fit_grid(cx_list, 8, median_w, w_frame)
            rows = cluster_and_fit_grid(cy_list, 3, median_h, h_frame)

            for cy in rows:
                for cx in cols:
                    x = int(cx - median_w / 2)
                    y = int(cy - median_h / 2)
                    x = max(-500, x)
                    y = max(-500, y)
                    final_24_boxes.append((x, y, median_w, median_h))

            print(
                "Mathematical Grid perfectly reconstructed via Hit-Based Voting & Pairwise Gap Analysis."
            )
            # --------------------------------------------------------

        else:
            # --- NEW: Detailed Error Diagnostics ---
            print("\n--- ERROR DIAGNOSTICS ---")
            print(
                f"Total unique objects detected across all frames: {len(box_clusters)}"
            )
            print(
                f"Objects that survived the stability filter (count >= 3): {len(filtered_boxes)}"
            )

            if not box_clusters:
                print(
                    "Cause: No objects matching the card aspect ratio (0.50 - 0.85) were found."
                )
                print(
                    "Suggestion: The game screen might be too dark, or the cards are heavily obscured."
                )
            else:
                print(
                    "Top 5 most stable objects found (which were ignored or insufficient):"
                )
                sorted_clusters = sorted(
                    box_clusters, key=lambda k: k["count"], reverse=True
                )[:5]
                for idx, c in enumerate(sorted_clusters):
                    x, y, w, h = c["box"]
                    aspect = w / float(h) if h != 0 else 0
                    print(
                        f" {idx+1}. Size: {w}x{h} (Aspect: {aspect:.2f}), Position: ({x},{y}), Seen in {c['count']} frames"
                    )
                print(
                    "Cause: Found potential cards, but not enough remained stable across 3+ frames, or their aspect ratio/size fell outside limits."
                )

            print(
                f"\nError: Failed to find enough anchors. Only found {len(filtered_boxes)} stable slots."
            )

        # --- PREPARE MACHINE LEARNING ENVIRONMENT ---
        try:
            from sklearn.ensemble import RandomForestClassifier
        except ImportError:
            print("\n[CRITICAL ERROR] Machine Learning library not found!")
            print("Please open terminal and run: pip install scikit-learn\n")
            self.reset_status()
            return

        if len(final_24_boxes) == 24:
            print("--- 2. Machine Learning: Supervised Extraction ---")

            good_dir = os.path.join("card_library", "good_cards")
            bad_dir = os.path.join("card_library", "bad_cards")
            os.makedirs(good_dir, exist_ok=True)
            os.makedirs(bad_dir, exist_ok=True)

            # Feature Extractor for the ML Model
            def extract_ml_features(img):
                h_i, w_i = img.shape[:2]
                # Deep crop to focus on core features
                cy, cx = int(h_i * 0.20), int(w_i * 0.20)
                c_img = img[cy : h_i - cy, cx : w_i - cx] if cy > 0 and cx > 0 else img
                bgr = (
                    cv2.cvtColor(c_img, cv2.COLOR_BGRA2BGR)
                    if c_img.shape[2] == 4
                    else c_img
                )

                # 1. Color Profile (HSV Histogram)
                hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
                cv2.normalize(hist, hist)

                # 2. Structural Profile (Downscaled Grayscale)
                gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                small_gray = cv2.resize(gray, (16, 16)).flatten() / 255.0

                return np.concatenate((hist.flatten(), small_gray))

            # --- ML PHASE 1: Train the AI on the fly ---
            X_train, y_train = [], []
            for folder, label in [(good_dir, 1), (bad_dir, 0)]:
                for filename in os.listdir(folder):
                    if filename.endswith((".jpg", ".png")):
                        filepath = os.path.join(folder, filename)
                        img = cv2.imread(filepath)
                        if img is not None:
                            X_train.append(extract_ml_features(img))
                            y_train.append(label)

            ai_model = None
            if (
                len(set(y_train)) == 2
            ):  # Ensure we have both Good (1) and Bad (0) examples
                print(f"Training AI Model with {len(X_train)} saved examples...")
                ai_model = RandomForestClassifier(n_estimators=100, random_state=42)
                ai_model.fit(X_train, y_train)
            else:
                print(
                    "⚠️ AI Needs Training Data! Please sort some correct/wrong cards into the 'card_library' folders."
                )
                print("Using basic fallback logic for this run...")

            # --- ML PHASE 2: Predict and Extract Best Frames ---
            best_card_images = []
            slot_features = []

            for idx, (x, y, w, h) in enumerate(final_24_boxes):
                best_prob = -1
                best_roi = None
                best_feat = None

                for frame in frames:
                    if (
                        y < 0
                        or x < 0
                        or y + h > frame.shape[0]
                        or x + w > frame.shape[1]
                    ):
                        continue
                    roi = frame[y : y + h, x : x + w]
                    if roi.size == 0:
                        continue

                    feat = extract_ml_features(roi)

                    if ai_model:
                        # ML Prediction (0.0 to 1.0)
                        prob_good = ai_model.predict_proba([feat])[0][1]
                        score = prob_good
                    else:
                        # Fallback just to gather initial data
                        bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)
                        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                        score = cv2.Laplacian(gray, cv2.CV_64F).var()

                    if score > best_prob:
                        best_prob = score
                        best_roi = roi.copy()
                        best_feat = feat

                # Acceptance Gate
                threshold = 0.60 if ai_model else 50
                if best_roi is None or best_prob < threshold:
                    best_roi = np.zeros((h, w, 4), dtype=np.uint8)
                    slot_features.append(None)
                    print(
                        f"[Slot {idx+1:02d}] ❌ AI REJECTED (Confidence: {best_prob*100:.1f}%)"
                    )
                else:
                    slot_features.append(best_feat)
                    if ai_model:
                        print(
                            f"[Slot {idx+1:02d}] ✅ AI ACCEPTED (Confidence: {best_prob*100:.1f}%)"
                        )

                best_card_images.append(best_roi)

            # --- ML PHASE 3: Strict Pairing & Auto-Sorting ---
            print("\n--- 3. Strict Match & Auto-Sorting ---")
            distances = []
            for i in range(24):
                if slot_features[i] is None:
                    continue
                for j in range(i + 1, 24):
                    if slot_features[j] is None:
                        continue

                    hist_i, gray_i = slot_features[i][:256], slot_features[i][256:]
                    hist_j, gray_j = slot_features[j][:256], slot_features[j][256:]

                    hist_corr = cv2.compareHist(
                        hist_i.astype(np.float32),
                        hist_j.astype(np.float32),
                        cv2.HISTCMP_CORREL,
                    )
                    hist_dist = 1.0 - max(0, hist_corr)
                    mse = np.mean((gray_i - gray_j) ** 2)

                    total_dist = (hist_dist * 0.7) + (mse * 0.3)
                    distances.append((total_dist, i, j))

            distances.sort(key=lambda x: x[0])

            pair_ids = ["FAIL"] * 24
            current_pid = 1
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            for dist, i, j in distances:
                if pair_ids[i] == "FAIL" and pair_ids[j] == "FAIL":
                    # If similarity distance is low enough, consider it a solid pair
                    if dist < 0.4:
                        pid_str = f"P{current_pid}"
                        pair_ids[i] = pid_str
                        pair_ids[j] = pid_str
                        current_pid += 1

                        # Save to Good Library
                        cv2.imwrite(
                            os.path.join(good_dir, f"good_{ts}_{i}.jpg"),
                            best_card_images[i],
                        )
                        cv2.imwrite(
                            os.path.join(good_dir, f"good_{ts}_{j}.jpg"),
                            best_card_images[j],
                        )
                    if current_pid > 12:
                        break

            # Save unmatched/failed cards to Bad Library
            failed_count = 0
            for i in range(24):
                if pair_ids[i] == "FAIL" and np.sum(best_card_images[i]) > 0:
                    cv2.imwrite(
                        os.path.join(bad_dir, f"bad_{ts}_{i}.jpg"), best_card_images[i]
                    )
                    failed_count += 1

            print(
                f"Matched {current_pid - 1} pairs successfully. Sent {failed_count} unmatched cards to 'bad_cards'."
            )

            # --- 4. Rendering Solution Visuals ---
            print("--- 4. Rendering Solution Visuals ---")
            final_display_images = []

            def get_color(pid_str):
                if pid_str == "FAIL":
                    return (0, 0, 255)  # Red for fail
                colors = [
                    (0, 255, 0),
                    (255, 0, 0),
                    (0, 255, 255),
                    (255, 0, 255),
                    (255, 255, 0),
                    (0, 165, 255),
                    (130, 0, 250),
                    (0, 128, 0),
                    (255, 191, 0),
                    (147, 20, 255),
                    (255, 255, 255),
                    (200, 200, 200),
                ]
                idx = (
                    int(pid_str.replace("P", "")) % len(colors) if "P" in pid_str else 0
                )
                return colors[idx]

            for i, img in enumerate(best_card_images):
                display_img = img.copy()
                pid = pair_ids[i]
                color = get_color(pid)

                cv2.rectangle(
                    display_img,
                    (0, 0),
                    (display_img.shape[1], display_img.shape[0]),
                    color,
                    8,
                )

                if pid != "FAIL":
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    (tw, th), _ = cv2.getTextSize(pid, font, 1.0, 2)
                    tx = (display_img.shape[1] - tw) // 2
                    ty = (display_img.shape[0] + th) // 2

                    cv2.rectangle(
                        display_img,
                        (tx - 5, ty - th - 5),
                        (tx + tw + 5, ty + 5),
                        (0, 0, 0),
                        -1,
                    )
                    cv2.putText(display_img, pid, (tx, ty), font, 1.0, color, 2)

                final_display_images.append(display_img)

            # Stitch and Save Full Solution Image
            if best_frame is not None:
                solution_full_img = best_frame.copy()
                solution_full_img = cv2.addWeighted(
                    solution_full_img, 0.4, np.zeros_like(solution_full_img), 0.6, 0
                )

                for idx, (x, y, w, h) in enumerate(final_24_boxes):
                    if (
                        y < 0
                        or x < 0
                        or y + h > solution_full_img.shape[0]
                        or x + w > solution_full_img.shape[1]
                    ):
                        continue

                    sol_card = final_display_images[idx]
                    if sol_card.shape[:2] != (h, w):
                        sol_card = cv2.resize(sol_card, (w, h))

                    solution_full_img[y : y + h, x : x + w] = sol_card

                sol_dir = "solution_logs"
                os.makedirs(sol_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                sol_filepath = os.path.join(sol_dir, f"solution_vision_{timestamp}.jpg")
                cv2.imwrite(sol_filepath, solution_full_img)
                print(f"Solution image exported to: {os.path.abspath(sol_filepath)}")

            self.verification_window.display_cards(final_display_images)
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
        log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "crash_log.txt"
        )
        with open(log_path, "a") as f:
            f.write(
                f"--- INIT CRASH LOG: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n"
            )
            traceback.print_exc(file=f)
            f.write("\n" + "=" * 50 + "\n\n")
        raise
