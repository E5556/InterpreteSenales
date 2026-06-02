import os
import sys
import numpy as np
import cv2
import threading

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QApplication, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QImage, QPixmap, QIcon

C_BG     = "#0f0f1a"
C_ACCENT = "#7c3aed"
C_CARD   = "#1e1e2e"
C_SUCCESS= "#22c55e"
C_DANGER = "#ef4444"
C_TEXT   = "#f8fafc"
C_MUTED  = "#94a3b8"
C_BORDER = "#2d2d44"

GESTURE_COLORS = {
    "HOLA":    "#7c3aed",
    "ADIOS":   "#3b82f6",
    "ADULTO":  "#f59e0b",
    "ANCIANO": "#22c55e",
    "GATO":    "#ef4444",
}


def _lbl(text, size=13, bold=False, color=C_TEXT, align=Qt.AlignLeft):
    l = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet(f"color:{color}; background:transparent;")
    l.setAlignment(align)
    l.setWordWrap(True)
    return l


# Funciones de keypoints (igual que en evaluation_mode_window)
def _interp_subspace(frames_array, target_length):
    n = len(frames_array)
    if n == target_length:
        return frames_array
    indices = np.linspace(0, n - 1, target_length)
    result = []
    for i in indices:
        lo, hi = int(np.floor(i)), int(np.ceil(i))
        w = i - lo
        result.append(frames_array[lo] if lo == hi else (1 - w) * frames_array[lo] + w * frames_array[hi])
    return result


def _extract_keypoints(results):
    pose = np.array([[r.x, r.y, r.z, r.visibility] for r in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    face = np.array([[r.x, r.y, r.z] for r in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
    lh   = np.array([[r.x, r.y, r.z] for r in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    rh   = np.array([[r.x, r.y, r.z] for r in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose, face, lh, rh])


def _normalize_keypoints(keypoints, target_length=15):
    arr  = [np.array(kp) for kp in keypoints]
    pose = _interp_subspace([kp[:132]      for kp in arr], target_length)
    face = _interp_subspace([kp[132:1536]  for kp in arr], target_length)
    lh   = _interp_subspace([kp[1536:1599] for kp in arr], target_length)
    rh   = _interp_subspace([kp[1599:]     for kp in arr], target_length)
    return [np.concatenate([pose[i], face[i], lh[i], rh[i]]) for i in range(target_length)]


class PracticeModeWindow(QWidget):
    """Modo práctica libre: el usuario elige un gesto y practica sin límite de tiempo."""

    def __init__(self, user_id, target_gesture=None, controller=None):
        super().__init__()
        self.user_id = user_id
        self.controller = controller
        self.target_gesture = target_gesture  # gesto a practicar (o None = todos)

        self.setWindowTitle("Modo Práctica — Intérprete LSP")
        self.setGeometry(150, 80, 960, 600)
        self.setMinimumSize(800, 500)
        self.setStyleSheet(f"background:{C_BG};")

        # Estado detector
        self._capture    = None
        self._holistic   = None
        self._model      = None
        self._word_ids   = []
        self._pred_filter = None
        self._kp_seq     = []
        self._count_frame = 0
        self._fix_frames  = 0
        self._recording   = False
        self._margin_frame = 1
        self._delay_frames = 2
        self._min_length   = 5
        self._model_frames = 15

        # Estadísticas por gesto
        self._stats = {}  # {word: {"intentos": 0, "correctos": 0, "conf_sum": 0}}

        self._build_ui()
        threading.Thread(target=self._load_model, daemon=True).start()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Panel izquierdo: video ────────────────────────────────
        left = QVBoxLayout()
        left.setContentsMargins(20, 20, 10, 20)
        left.setSpacing(10)

        self.video_label = QLabel()
        self.video_label.setFixedSize(460, 345)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background:#000; color:#94a3b8; border-radius:12px;")
        self.video_label.setText("Cargando cámara...")
        self.video_label.setFont(QFont("Segoe UI", 13))
        left.addWidget(self.video_label)

        self.detection_lbl = _lbl("Esperando seña...", 12, color=C_MUTED, align=Qt.AlignCenter)
        left.addWidget(self.detection_lbl)

        # Confianza en vivo
        conf_row = QHBoxLayout()
        conf_row.addWidget(_lbl("Confianza:", 11, color=C_MUTED))
        self.conf_bar = QProgressBar()
        self.conf_bar.setMaximum(100)
        self.conf_bar.setValue(0)
        self.conf_bar.setFixedHeight(12)
        self.conf_bar.setTextVisible(False)
        self.conf_bar.setStyleSheet(
            "QProgressBar{background:#2d2d44;border-radius:6px;}"
            "QProgressBar::chunk{background:#ef4444;border-radius:6px;}"
        )
        self.conf_pct = _lbl("0%", 11, bold=True, color=C_MUTED)
        conf_row.addWidget(self.conf_bar)
        conf_row.addWidget(self.conf_pct)
        left.addLayout(conf_row)
        left.addStretch()

        # Botón volver
        btn_back = QPushButton("← Volver")
        btn_back.setFixedHeight(38)
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setFont(QFont("Segoe UI", 11))
        btn_back.setStyleSheet(
            f"QPushButton{{background:transparent;color:{C_MUTED};border:1px solid {C_BORDER};border-radius:8px;}}"
            f"QPushButton:hover{{color:{C_TEXT};border-color:{C_MUTED};}}"
        )
        btn_back.clicked.connect(self.close)
        left.addWidget(btn_back)

        root.addLayout(left)

        # ── Panel derecho: selección de gesto + estadísticas ─────
        right = QVBoxLayout()
        right.setContentsMargins(10, 20, 24, 20)
        right.setSpacing(14)

        right.addWidget(_lbl("Modo Práctica", 20, bold=True))
        right.addWidget(_lbl("Haz el gesto que quieras practicar frente a la cámara", 11, color=C_MUTED))

        # Selector de gesto objetivo
        right.addWidget(_lbl("Practicar:", 12, color=C_MUTED))
        self._gesture_btns = {}
        btn_grid = QGridLayout()
        btn_grid.setSpacing(8)
        all_gestures = ["TODOS"] + list(GESTURE_COLORS.keys())
        for i, g in enumerate(all_gestures):
            btn = QPushButton(g)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
            is_sel = (g == (self.target_gesture or "TODOS"))
            color = GESTURE_COLORS.get(g, C_ACCENT)
            btn.setStyleSheet(
                f"QPushButton{{background:{color if is_sel else C_CARD};"
                f"color:{'white' if is_sel else C_MUTED};"
                f"border:1px solid {color};border-radius:8px;}}"
                f"QPushButton:hover{{background:{color};color:white;}}"
            )
            btn.clicked.connect(lambda _, gg=g: self._set_target(gg))
            self._gesture_btns[g] = btn
            btn_grid.addWidget(btn, i // 3, i % 3)
        right.addLayout(btn_grid)

        # Gesto detectado (grande)
        self.detected_card = QFrame()
        self.detected_card.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:14px;}}")
        dc = QVBoxLayout(self.detected_card)
        dc.setContentsMargins(20, 14, 20, 14)
        self.detected_word = _lbl("—", 38, bold=True, color=C_ACCENT, align=Qt.AlignCenter)
        self.detected_word.setAlignment(Qt.AlignCenter)
        self.detected_result = _lbl("", 14, align=Qt.AlignCenter)
        self.detected_result.setAlignment(Qt.AlignCenter)
        dc.addWidget(self.detected_word)
        dc.addWidget(self.detected_result)
        right.addWidget(self.detected_card)

        # Estadísticas por gesto
        right.addWidget(_lbl("Estadísticas de esta sesión:", 12, bold=True))
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(6)
        self._stats_labels = {}
        for i, g in enumerate(GESTURE_COLORS.keys()):
            self._stats[g] = {"intentos": 0, "correctos": 0, "conf_sum": 0.0}
            chip = QLabel(f"{g}: 0 intentos")
            chip.setFont(QFont("Segoe UI", 10))
            chip.setStyleSheet(f"background:{C_CARD};color:{C_MUTED};border-radius:6px;padding:4px 8px;")
            self.stats_grid.addWidget(chip, i // 2, i % 2)
            self._stats_labels[g] = chip
        right.addLayout(self.stats_grid)
        right.addStretch()

        root.addLayout(right)

        # Timers
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._update_frame)
        self.frame_timer.setInterval(33)

    def _set_target(self, gesture):
        self.target_gesture = None if gesture == "TODOS" else gesture
        for g, btn in self._gesture_btns.items():
            is_sel = (g == gesture)
            color = GESTURE_COLORS.get(g, C_ACCENT)
            btn.setStyleSheet(
                f"QPushButton{{background:{color if is_sel else C_CARD};"
                f"color:{'white' if is_sel else C_MUTED};"
                f"border:1px solid {color};border-radius:8px;}}"
                f"QPushButton:hover{{background:{color};color:white;}}"
            )

    def _load_model(self):
        try:
            from keras.models import load_model as keras_load
            from mediapipe.python.solutions.holistic import Holistic
            from training_utils import get_gestures_with_valid_keypoints
            from constants import MODEL_PATH
            from prediction_filter import PredictionFilter

            self._holistic    = Holistic()
            self._model       = keras_load(MODEL_PATH)
            self._word_ids    = get_gestures_with_valid_keypoints()
            self._pred_filter = PredictionFilter(window_size=3, confidence_threshold=0.55)
            self._capture     = cv2.VideoCapture(0)
            QTimer.singleShot(0, self.frame_timer.start)
        except Exception as e:
            QTimer.singleShot(0, lambda: self.detection_lbl.setText(f"Error: {e}"))

    def _update_frame(self):
        if not self._capture or not self._capture.isOpened():
            return
        ret, frame = self._capture.read()
        if not ret:
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self._holistic and self._model and self._pred_filter:
            try:
                from helpers import mediapipe_detection, there_hand
                results = mediapipe_detection(frame, self._holistic)
                hand_present = there_hand(results)

                if hand_present or self._recording:
                    self._recording = False
                    self._count_frame += 1
                    if self._count_frame > self._margin_frame:
                        self._kp_seq.append(_extract_keypoints(results))
                    self.detection_lbl.setText(f"Grabando... ({len(self._kp_seq)} frames)")
                else:
                    if self._count_frame >= self._min_length + self._margin_frame:
                        self._fix_frames += 1
                        if self._fix_frames < self._delay_frames:
                            self._recording = True
                        else:
                            trim = self._margin_frame + self._delay_frames
                            if len(self._kp_seq) > trim:
                                self._kp_seq = self._kp_seq[:-trim]
                            if len(self._kp_seq) >= self._min_length:
                                kp_norm = _normalize_keypoints(self._kp_seq, self._model_frames)
                                res = self._model.predict(np.expand_dims(kp_norm, axis=0), verbose=0)[0]
                                name, conf = self._pred_filter.add_prediction(res, self._word_ids)
                                if name:
                                    self._on_gesture_detected(name.upper(), conf)

                    if not self._recording:
                        self._count_frame = 0
                        self._fix_frames  = 0
                        self._kp_seq      = []
                        if not hand_present:
                            self.detection_lbl.setText("Esperando seña...")
            except Exception:
                pass

        h, w, ch = frame_rgb.shape
        qi = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qi).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    def _on_gesture_detected(self, word, conf):
        pct = int(conf * 100)
        color_word = GESTURE_COLORS.get(word, C_ACCENT)

        # Actualizar barra de confianza
        self.conf_bar.setValue(pct)
        bar_color = "#22c55e" if pct >= 80 else ("#f59e0b" if pct >= 60 else "#ef4444")
        self.conf_bar.setStyleSheet(
            f"QProgressBar{{background:#2d2d44;border-radius:6px;}}"
            f"QProgressBar::chunk{{background:{bar_color};border-radius:6px;}}"
        )
        self.conf_pct.setText(f"{pct}%")
        self.conf_pct.setStyleSheet(f"color:{bar_color};background:transparent;font-weight:bold;font-size:11px;")

        # Mostrar gesto detectado
        self.detected_word.setText(word)
        self.detected_word.setStyleSheet(f"color:{color_word};background:transparent;font-size:38px;font-weight:bold;")

        # Evaluar si es correcto según el objetivo
        if self.target_gesture and self.target_gesture != "TODOS":
            is_correct = (word == self.target_gesture)
            result_text = "✅ ¡Correcto!" if is_correct else f"❌ Era: {self.target_gesture}"
            result_color = C_SUCCESS if is_correct else C_DANGER
            self.detected_result.setText(result_text)
            self.detected_result.setStyleSheet(f"color:{result_color};background:transparent;font-size:14px;font-weight:bold;")
        else:
            self.detected_result.setText(f"Confianza: {pct}%")
            self.detected_result.setStyleSheet(f"color:{C_MUTED};background:transparent;font-size:14px;")

        # Actualizar estadísticas
        if word in self._stats:
            self._stats[word]["intentos"] += 1
            self._stats[word]["conf_sum"] += conf
            target_ok = (not self.target_gesture or self.target_gesture == "TODOS" or word == self.target_gesture)
            if target_ok and pct >= 70:
                self._stats[word]["correctos"] += 1
            st = self._stats[word]
            avg = int(st["conf_sum"] / st["intentos"] * 100) if st["intentos"] > 0 else 0
            color = GESTURE_COLORS.get(word, C_ACCENT)
            self._stats_labels[word].setText(f"{word}: {st['intentos']} intentos  •  {avg}% prom")
            self._stats_labels[word].setStyleSheet(
                f"background:{C_CARD};color:{color};border-radius:6px;padding:4px 8px;font-weight:bold;"
            )
        self.detection_lbl.setText(f"Detectado: {word} ({pct}%)")

    def closeEvent(self, event):
        self.frame_timer.stop()
        try:
            if self._capture:
                self._capture.release()
            if self._holistic:
                self._holistic.close()
        except Exception:
            pass
        event.accept()

    def _blank_icon(self):
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        return QIcon(px)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = PracticeModeWindow(user_id=2, target_gesture="HOLA")
    w.show()
    sys.exit(app.exec_())
