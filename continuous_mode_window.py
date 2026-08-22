import os
import sys
import time
import threading
import numpy as np
import cv2

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QApplication, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QImage, QPixmap, QIcon

C_BG     = "#0f0f1a"
C_ACCENT = "#7c3aed"
C_CARD   = "#1e1e2e"
C_CARD2  = "#16213e"
C_SUCCESS= "#22c55e"
C_DANGER = "#ef4444"
C_WARN   = "#f59e0b"
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


class ContinuousModeWindow(QWidget):
    """
    Modo continuo para usuarios avanzados: reconoce señas de forma fluida
    sin necesidad de bajar la mano entre gestos. Usa rolling buffer de 15 frames.
    """

    def __init__(self, user_id, controller=None):
        super().__init__()
        self.user_id    = user_id
        self.controller = controller

        self.setWindowTitle("Modo Continuo — Intérprete LSC")
        self.setGeometry(120, 60, 1100, 650)
        self.setMinimumSize(900, 550)
        self.setStyleSheet(f"background:{C_BG};")

        # Cámara y modelo
        self._capture  = None
        self._holistic = None
        self._model    = None
        self._word_ids = []
        self._timer    = None

        # Rolling buffer
        self._rolling_buf       = []
        self._rolling_size      = 15
        self._rolling_skip      = 5
        self._rolling_since_pred = 0

        # Cooldowns
        self._last_gesture_name = None
        self._last_gesture_time = 0.0
        self._cooldown_same     = 1.2
        self._cooldown_any      = 0.3

        # Frase acumulada
        self._phrase = []

        # Stats de sesión
        self._total_gestos = 0
        self._conf_sum     = 0.0
        self._gesture_counts = {}  # {word: int}

        # Gestos registrados (para BD al cerrar)
        self._session_log = []  # [(word, confidence)]

        self._model_ready = False  # flag seteado por hilo background
        self._load_error  = None

        self._build_ui()
        threading.Thread(target=self._load_model, daemon=True).start()

        # Timer de polling en hilo principal: espera hasta que modelo esté listo
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._check_model_ready)
        self._poll_timer.start(200)

    # ── UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addLayout(self._build_left_panel())
        root.addLayout(self._build_right_panel(), stretch=1)

    def _build_left_panel(self):
        lay = QVBoxLayout()
        lay.setContentsMargins(20, 24, 12, 20)
        lay.setSpacing(14)

        # Título
        lay.addWidget(_lbl("Modo Continuo", 18, bold=True, color=C_ACCENT))
        lay.addWidget(_lbl("Señas fluidas sin bajar la mano", 10, color=C_MUTED))

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background:{C_BORDER};")
        lay.addWidget(sep)

        # Stats de sesión
        stats_card = QFrame()
        stats_card.setStyleSheet(f"background:{C_CARD};border-radius:10px;")
        sc = QVBoxLayout(stats_card)
        sc.setContentsMargins(14, 12, 14, 12)
        sc.setSpacing(8)
        sc.addWidget(_lbl("ESTADÍSTICAS", 9, bold=True, color=C_MUTED))

        self.lbl_total = _lbl("0 gestos reconocidos", 12, color=C_TEXT)
        self.lbl_prec  = _lbl("— precisión promedio", 12, color=C_MUTED)
        sc.addWidget(self.lbl_total)
        sc.addWidget(self.lbl_prec)
        lay.addWidget(stats_card)

        # Contadores por gesto
        lay.addWidget(_lbl("GESTOS DETECTADOS", 9, bold=True, color=C_MUTED))
        self._count_labels = {}
        for word in ["HOLA", "ADIOS", "ADULTO", "ANCIANO", "GATO"]:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setFont(QFont("Segoe UI", 11))
            color = GESTURE_COLORS.get(word, C_ACCENT)
            dot.setStyleSheet(f"color:{color}; background:transparent;")
            dot.setFixedWidth(18)
            lbl_w = _lbl(word, 12, color=C_TEXT)
            lbl_w.setFixedWidth(80)
            cnt = _lbl("0", 12, bold=True, color=color, align=Qt.AlignRight)
            self._count_labels[word] = cnt
            row.addWidget(dot)
            row.addWidget(lbl_w)
            row.addStretch()
            row.addWidget(cnt)
            lay.addLayout(row)

        lay.addStretch()

        # Botón volver
        btn_back = QPushButton("← Volver al menú")
        btn_back.setFixedHeight(40)
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setFont(QFont("Segoe UI", 11))
        btn_back.setStyleSheet(
            f"QPushButton{{background:transparent;color:{C_MUTED};border:1px solid {C_BORDER};border-radius:8px;}}"
            f"QPushButton:hover{{color:{C_TEXT};border-color:{C_MUTED};}}"
        )
        btn_back.clicked.connect(self.close)
        lay.addWidget(btn_back)

        container = QWidget()
        container.setFixedWidth(240)
        container.setStyleSheet(f"background:{C_BG};")
        container.setLayout(lay)
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)
        return outer

    def _build_right_panel(self):
        lay = QVBoxLayout()
        lay.setContentsMargins(12, 20, 24, 20)
        lay.setSpacing(12)

        # Video
        self.video_label = QLabel()
        self.video_label.setMinimumSize(560, 380)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background:#000; color:#94a3b8; border-radius:12px;")
        self.video_label.setText("Cargando modelo y cámara...")
        self.video_label.setFont(QFont("Segoe UI", 13))
        lay.addWidget(self.video_label, stretch=1)

        # Gesto detectado + barra confianza
        detect_row = QHBoxLayout()
        detect_row.setSpacing(12)

        self.lbl_gesto = _lbl("—", 22, bold=True, color=C_ACCENT, align=Qt.AlignLeft)
        self.lbl_gesto.setFixedWidth(200)
        detect_row.addWidget(self.lbl_gesto)

        conf_col = QVBoxLayout()
        conf_col.setSpacing(4)
        conf_row = QHBoxLayout()
        conf_row.addWidget(_lbl("Confianza:", 10, color=C_MUTED))
        self.lbl_conf_pct = _lbl("0%", 10, bold=True, color=C_MUTED)
        conf_row.addWidget(self.lbl_conf_pct)
        conf_row.addStretch()
        conf_col.addLayout(conf_row)

        self.conf_bar = QProgressBar()
        self.conf_bar.setMaximum(100)
        self.conf_bar.setValue(0)
        self.conf_bar.setFixedHeight(10)
        self.conf_bar.setTextVisible(False)
        self.conf_bar.setStyleSheet(
            "QProgressBar{background:#2d2d44;border-radius:5px;}"
            "QProgressBar::chunk{background:#ef4444;border-radius:5px;}"
        )
        conf_col.addWidget(self.conf_bar)
        detect_row.addLayout(conf_col)
        detect_row.addStretch()

        # Status mano
        self.lbl_status = _lbl("Iniciando...", 11, color=C_MUTED, align=Qt.AlignRight)
        detect_row.addWidget(self.lbl_status)

        lay.addLayout(detect_row)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background:{C_BORDER};")
        lay.addWidget(sep)

        # Frase acumulada
        lay.addWidget(_lbl("FRASE ACUMULADA", 9, bold=True, color=C_MUTED))

        self.lbl_frase = QLabel("—")
        self.lbl_frase.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.lbl_frase.setStyleSheet(
            f"color:{C_TEXT}; background:{C_CARD}; border-radius:10px; padding:12px 16px;"
        )
        self.lbl_frase.setWordWrap(True)
        self.lbl_frase.setMinimumHeight(60)
        lay.addWidget(self.lbl_frase)

        # Botones frase
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_clear = QPushButton("🗑️  Limpiar frase")
        self.btn_clear.setFixedHeight(38)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setFont(QFont("Segoe UI", 11))
        self.btn_clear.setStyleSheet(
            f"QPushButton{{background:{C_CARD};color:{C_DANGER};border:1px solid {C_DANGER};border-radius:8px;padding:0 14px;}}"
            f"QPushButton:hover{{background:rgba(239,68,68,0.12);}}"
        )
        self.btn_clear.clicked.connect(self._clear_phrase)
        btn_row.addWidget(self.btn_clear)

        self.btn_speak = QPushButton("🔊  Pronunciar frase")
        self.btn_speak.setFixedHeight(38)
        self.btn_speak.setCursor(Qt.PointingHandCursor)
        self.btn_speak.setFont(QFont("Segoe UI", 11))
        self.btn_speak.setStyleSheet(
            f"QPushButton{{background:{C_ACCENT};color:white;border:none;border-radius:8px;padding:0 14px;}}"
            f"QPushButton:hover{{background:#6d28d9;}}"
        )
        self.btn_speak.clicked.connect(self._speak_phrase)
        btn_row.addWidget(self.btn_speak)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        return lay

    # ── CARGA DE MODELO ───────────────────────────────────────────

    def _load_model(self):
        error_msg = None
        try:
            import mediapipe as mp
            import tensorflow as tf
            from constants import MODEL_PATH, MODEL_FRAMES
            from training_utils import get_gestures_with_valid_keypoints
            from prediction_filter import PredictionFilter

            self._holistic = mp.solutions.holistic.Holistic(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self._model    = tf.keras.models.load_model(MODEL_PATH)
            self._word_ids = get_gestures_with_valid_keypoints()
            self._rolling_size = MODEL_FRAMES
            self._pred_filter = PredictionFilter(window_size=3, confidence_threshold=0.70)

            self._capture = cv2.VideoCapture(0)
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            self._model_ready = True
        except Exception as e:
            error_msg = str(e)
            print(f"[ContinuousMode] Error al cargar: {error_msg}")

        # Actualizar UI solo desde el hilo principal via _check_model_ready
        if error_msg:
            self._load_error = error_msg

    def _check_model_ready(self):
        if getattr(self, '_load_error', None):
            self._poll_timer.stop()
            self.video_label.setText(f"Error al cargar:\n{self._load_error}")
        elif self._model_ready:
            self._poll_timer.stop()
            self._start_timer()

    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        self._timer.start(33)
        self.video_label.setText("")

    # ── LOOP DE CAPTURA ───────────────────────────────────────────

    def _update_frame(self):
        if not self._capture or not self._capture.isOpened():
            return

        ret, frame = self._capture.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self._holistic.process(image)
        image.flags.writeable = True

        # Detectar si hay mano
        hand_present = (results.left_hand_landmarks is not None or
                        results.right_hand_landmarks is not None)

        if hand_present:
            self.lbl_status.setText("✋ Mano detectada")
            self.lbl_status.setStyleSheet("color:#22c55e; background:transparent;")

            kp = _extract_keypoints(results)
            self._rolling_buf.append(kp)
            if len(self._rolling_buf) > self._rolling_size:
                self._rolling_buf.pop(0)
            self._rolling_since_pred += 1

            if (len(self._rolling_buf) == self._rolling_size and
                    self._rolling_since_pred >= self._rolling_skip):
                self._rolling_since_pred = 0
                self._run_prediction(results)
        else:
            self.lbl_status.setText("👁️  Esperando mano...")
            self.lbl_status.setStyleSheet(f"color:{C_MUTED}; background:transparent;")
            self._rolling_buf.clear()
            self._rolling_since_pred = 0

        # Dibujar keypoints
        self._draw_keypoints(image, results)
        self._show_frame(image)

    def _run_prediction(self, results):
        try:
            kp_norm = _normalize_keypoints(self._rolling_buf, self._rolling_size)
            pred    = self._model.predict(np.expand_dims(kp_norm, axis=0), verbose=0)[0]
            gesture_name, confidence = self._pred_filter.add_prediction(pred, self._word_ids)
            confidence = float(confidence) if confidence is not None else 0.0
            pct = int(confidence * 100)

            # Actualizar barra de confianza siempre
            self.conf_bar.setValue(pct)
            bar_color = C_SUCCESS if pct >= 80 else (C_WARN if pct >= 60 else C_DANGER)
            self.conf_bar.setStyleSheet(
                f"QProgressBar{{background:#2d2d44;border-radius:5px;}}"
                f"QProgressBar::chunk{{background:{bar_color};border-radius:5px;}}"
            )
            self.lbl_conf_pct.setText(f"{pct}%")
            self.lbl_conf_pct.setStyleSheet(f"color:{bar_color}; background:transparent; font-weight:bold;")

            if gesture_name and confidence >= 0.70:
                now = time.time()
                same_ok = (gesture_name != self._last_gesture_name or
                           (now - self._last_gesture_time) >= self._cooldown_same)
                any_ok  = (now - self._last_gesture_time) >= self._cooldown_any

                if same_ok and any_ok:
                    self._on_gesture(gesture_name, confidence)
                    self._last_gesture_name = gesture_name
                    self._last_gesture_time = now

            # Mostrar mejor candidato aunque no pase cooldown
            if gesture_name:
                color = GESTURE_COLORS.get(gesture_name.upper(), C_ACCENT)
                self.lbl_gesto.setText(gesture_name.upper())
                self.lbl_gesto.setStyleSheet(f"color:{color}; background:transparent; font-weight:bold;")
            else:
                self.lbl_gesto.setText("—")
                self.lbl_gesto.setStyleSheet(f"color:{C_MUTED}; background:transparent;")

        except Exception:
            pass

    def _on_gesture(self, word, confidence):
        word_upper = word.upper()

        # Acumular en frase
        self._phrase.append(word_upper)
        frase_texto = "  ".join(self._phrase)
        self.lbl_frase.setText(frase_texto)

        # Stats
        self._total_gestos += 1
        self._conf_sum += confidence
        self._gesture_counts[word_upper] = self._gesture_counts.get(word_upper, 0) + 1
        self._session_log.append((word_upper, float(confidence)))

        avg_pct = int(self._conf_sum / self._total_gestos * 100)
        self.lbl_total.setText(f"{self._total_gestos} gesto{'s' if self._total_gestos != 1 else ''} reconocido{'s' if self._total_gestos != 1 else ''}")
        self.lbl_prec.setText(f"{avg_pct}% precisión promedio")

        # Actualizar contador del gesto
        if word_upper in self._count_labels:
            self._count_labels[word_upper].setText(str(self._gesture_counts[word_upper]))

    def _clear_phrase(self):
        self._phrase.clear()
        self.lbl_frase.setText("—")

    def _speak_phrase(self):
        if not self._phrase:
            return
        frase = " ".join(self._phrase).lower()
        try:
            from text_to_speech import text_to_speech
            threading.Thread(target=text_to_speech, args=(frase,), daemon=True).start()
        except Exception:
            pass

    # ── VIDEO ─────────────────────────────────────────────────────

    def _draw_keypoints(self, image, results):
        try:
            import mediapipe as mp
            mp_draw = mp.solutions.drawing_utils
            mp_styles = mp.solutions.drawing_styles
            if results.pose_landmarks:
                mp_draw.draw_landmarks(image, results.pose_landmarks,
                                       mp.solutions.holistic.POSE_CONNECTIONS)
            if results.left_hand_landmarks:
                mp_draw.draw_landmarks(image, results.left_hand_landmarks,
                                       mp.solutions.holistic.HAND_CONNECTIONS,
                                       mp_styles.get_default_hand_landmarks_style(),
                                       mp_styles.get_default_hand_connections_style())
            if results.right_hand_landmarks:
                mp_draw.draw_landmarks(image, results.right_hand_landmarks,
                                       mp.solutions.holistic.HAND_CONNECTIONS,
                                       mp_styles.get_default_hand_landmarks_style(),
                                       mp_styles.get_default_hand_connections_style())
        except Exception:
            pass

    def _show_frame(self, image):
        h, w, ch = image.shape
        qimg = QImage(image.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(
            qimg.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        ))

    # ── CIERRE ────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self._timer:
            self._timer.stop()
        if self._capture:
            self._capture.release()
        if self._holistic:
            self._holistic.close()

        # Guardar interpretaciones en BD si hay gestos registrados
        if self._session_log:
            try:
                from database import add_interpretation, create_session
                from constants import get_database_name
                session_id = create_session(self.user_id)
                for word, conf in self._session_log:
                    add_interpretation(session_id, word, float(conf))
            except Exception:
                pass

        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    class MockController:
        def logout(self): print("Logout")

    w = ContinuousModeWindow(user_id=1, controller=MockController())
    w.show()
    sys.exit(app.exec_())
