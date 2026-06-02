import os
import sys
import random
import threading
import numpy as np
import cv2

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QApplication, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QImage, QPixmap, QIcon

C_BG       = "#0f0f1a"
C_ACCENT   = "#7c3aed"
C_SUCCESS  = "#22c55e"
C_DANGER   = "#ef4444"
C_CARD     = "#1e1e2e"
C_TEXT     = "#f8fafc"
C_MUTED    = "#94a3b8"

SECONDS_PER_WORD = 5   # tiempo para hacer cada seña
WORDS_PER_EXAM   = 5   # cantidad de señas por evaluación


def _lbl(text, size=13, bold=False, color=C_TEXT, align=Qt.AlignLeft):
    l = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet(f"color:{color}; background:transparent;")
    l.setAlignment(align)
    l.setWordWrap(True)
    return l


class EvaluationModeWindow(QWidget):
    """
    Modo evaluación: muestra una palabra de LSP, el usuario hace la seña,
    el modelo verifica si es correcta. Al final muestra el puntaje.
    """

    def __init__(self, user_id, controller=None):
        super().__init__()
        self.user_id = user_id
        self.controller = controller

        self.setWindowTitle("Modo Evaluación — Intérprete LSP")
        self.setGeometry(150, 80, 960, 620)
        self.setMinimumSize(800, 500)
        self.setStyleSheet(f"background:{C_BG};")

        # Estado interno
        self._words = []
        self._current_idx = 0
        self._results = []          # (word, predicted, correct, confidence)
        self._countdown = SECONDS_PER_WORD
        self._last_prediction = None
        self._last_confidence = 0.0
        self._capture = None
        self._holistic = None
        self._model = None
        self._word_ids = []
        self._running = False

        self._build_ui()
        self._load_model_async()

    # ── UI ──────────────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Panel izquierdo: video
        left = QVBoxLayout()
        left.setContentsMargins(20, 20, 10, 20)
        left.setSpacing(12)

        self.video_label = QLabel()
        self.video_label.setFixedSize(480, 360)
        self.video_label.setStyleSheet(f"background:#000; border-radius:12px;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("Cargando cámara...")
        self.video_label.setFont(QFont("Segoe UI", 13))
        self.video_label.setStyleSheet(f"background:#000; color:{C_MUTED}; border-radius:12px;")
        left.addWidget(self.video_label)

        # Estado de detección
        self.detection_label = _lbl("Esperando detección...", 13, color=C_MUTED, align=Qt.AlignCenter)
        left.addWidget(self.detection_label)

        root.addLayout(left)

        # Panel derecho: instrucciones + resultado
        right = QVBoxLayout()
        right.setContentsMargins(10, 30, 30, 20)
        right.setSpacing(18)

        right.addWidget(_lbl("Modo Evaluación", 22, bold=True, align=Qt.AlignCenter))
        right.addWidget(_lbl(f"Haz {WORDS_PER_EXAM} señas en {SECONDS_PER_WORD}s cada una", 12,
                             color=C_MUTED, align=Qt.AlignCenter))
        right.addSpacing(10)

        # Palabra a mostrar
        self.word_card = QFrame()
        self.word_card.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:16px;}}")
        wl = QVBoxLayout(self.word_card)
        wl.setContentsMargins(24, 24, 24, 24)
        self.word_display = _lbl("Cargando...", 42, bold=True, color=C_ACCENT, align=Qt.AlignCenter)
        self.word_display.setAlignment(Qt.AlignCenter)
        wl.addWidget(self.word_display)
        self.word_sub = _lbl("", 13, color=C_MUTED, align=Qt.AlignCenter)
        wl.addWidget(self.word_sub)
        right.addWidget(self.word_card)

        # Countdown bar
        self.countdown_bar = QProgressBar()
        self.countdown_bar.setMaximum(SECONDS_PER_WORD * 10)
        self.countdown_bar.setValue(SECONDS_PER_WORD * 10)
        self.countdown_bar.setFixedHeight(12)
        self.countdown_bar.setTextVisible(False)
        self.countdown_bar.setStyleSheet(
            f"QProgressBar{{background:#2d2d44;border-radius:6px;}}"
            f"QProgressBar::chunk{{background:{C_ACCENT};border-radius:6px;}}"
        )
        right.addWidget(self.countdown_bar)
        self.countdown_lbl = _lbl(f"{SECONDS_PER_WORD}s", 13, color=C_MUTED, align=Qt.AlignCenter)
        right.addWidget(self.countdown_lbl)

        # Progreso general
        self.progress_lbl = _lbl("", 12, color=C_MUTED, align=Qt.AlignCenter)
        right.addWidget(self.progress_lbl)

        # Resultado instantáneo de cada seña
        self.result_lbl = _lbl("", 16, bold=True, align=Qt.AlignCenter)
        right.addWidget(self.result_lbl)

        right.addStretch()

        # Botones
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶  Iniciar Evaluación")
        self.btn_start.setFixedHeight(44)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.btn_start.setStyleSheet(f"""
            QPushButton{{background:{C_ACCENT};color:white;border-radius:10px;border:none;}}
            QPushButton:hover{{background:#6d28d9;}}
            QPushButton:disabled{{background:#2d2d44;color:{C_MUTED};}}
        """)
        self.btn_start.clicked.connect(self._start_evaluation)
        btn_row.addWidget(self.btn_start)

        self.btn_back = QPushButton("← Volver")
        self.btn_back.setFixedHeight(44)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setFont(QFont("Segoe UI", 12))
        self.btn_back.setStyleSheet(f"""
            QPushButton{{background:transparent;color:{C_MUTED};border:1px solid #2d2d44;border-radius:10px;}}
            QPushButton:hover{{color:{C_TEXT};border-color:{C_MUTED};}}
        """)
        self.btn_back.clicked.connect(self.close)
        btn_row.addWidget(self.btn_back)
        right.addLayout(btn_row)

        root.addLayout(right)

        # Timers
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._update_frame)
        self.frame_timer.setInterval(33)  # ~30 fps

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._tick_countdown)
        self.countdown_timer.setInterval(100)  # 100ms ticks

    # ── CARGA DEL MODELO ────────────────────────────────────────
    def _load_model_async(self):
        self.btn_start.setEnabled(False)
        self.word_display.setText("Cargando modelo...")
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self):
        try:
            from keras.models import load_model as keras_load
            from mediapipe.python.solutions.holistic import Holistic
            from training_utils import get_gestures_with_valid_keypoints
            from constants import MODEL_PATH

            self._holistic = Holistic()
            self._model = keras_load(MODEL_PATH)
            self._word_ids = get_gestures_with_valid_keypoints()
            self._capture = cv2.VideoCapture(0)

            # Señalizar éxito en el hilo principal via timer de un disparo
            QTimer.singleShot(0, self._on_model_loaded)
        except Exception as e:
            QTimer.singleShot(0, lambda: self._on_model_error(str(e)))

    def _on_model_loaded(self):
        self.btn_start.setEnabled(True)
        self.word_display.setText("¡Listo!")
        self.word_sub.setText(f"Gestos disponibles: {', '.join(g.upper() for g in self._word_ids)}")
        self.frame_timer.start()

    def _on_model_error(self, msg):
        self.word_display.setText("Error al cargar")
        self.word_sub.setText(msg)
        self.detection_label.setText(f"Error: {msg}")

    # ── VIDEO ────────────────────────────────────────────────────
    def _update_frame(self):
        if self._capture is None or not self._capture.isOpened():
            return
        ret, frame = self._capture.read()
        if not ret:
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self._running and self._holistic and self._model:
            try:
                from helpers import mediapipe_detection, there_hand, get_keypoints, normalize_keypoints
                from prediction_filter import PredictionFilter
                results = mediapipe_detection(frame, self._holistic)
                if there_hand(results):
                    if not hasattr(self, '_kp_seq'):
                        self._kp_seq = []
                        self._pred_filter = PredictionFilter(window_size=3, confidence_threshold=0.60)
                    kp = get_keypoints(results)
                    self._kp_seq.append(kp)
                    if len(self._kp_seq) > 15:
                        self._kp_seq = self._kp_seq[-15:]
                    if len(self._kp_seq) == 15:
                        from constants import MAX_LENGTH_FRAMES
                        padded = self._kp_seq[:]
                        while len(padded) < MAX_LENGTH_FRAMES:
                            padded.insert(0, np.zeros_like(padded[0]))
                        kp_arr = np.array(padded[-MAX_LENGTH_FRAMES:])
                        kp_norm = normalize_keypoints(kp_arr)
                        res = self._model.predict(np.expand_dims(kp_norm, axis=0), verbose=0)[0]
                        name, conf = self._pred_filter.add_prediction(res, self._word_ids)
                        if name:
                            self._last_prediction = name
                            self._last_confidence = conf
                            pct = int(conf * 100)
                            self.detection_label.setText(f"Detectando: {name.upper()} ({pct}%)")
            except Exception:
                pass

        h, w, ch = frame_rgb.shape
        qi = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qi).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    # ── EVALUACIÓN ───────────────────────────────────────────────
    def _start_evaluation(self):
        if not self._word_ids:
            return
        words_pool = [w.upper() for w in self._word_ids]
        self._words = random.sample(words_pool * max(1, WORDS_PER_EXAM // len(words_pool) + 1),
                                    WORDS_PER_EXAM)
        self._current_idx = 0
        self._results = []
        self.btn_start.setEnabled(False)
        self._show_word()

    def _show_word(self):
        if self._current_idx >= len(self._words):
            self._finish_evaluation()
            return

        word = self._words[self._current_idx]
        self.word_display.setText(word)
        self.word_sub.setText(f"Haz la seña en {SECONDS_PER_WORD} segundos")
        self.progress_lbl.setText(f"Seña {self._current_idx + 1} de {len(self._words)}")
        self.result_lbl.setText("")
        self.countdown_bar.setValue(SECONDS_PER_WORD * 10)
        self.countdown_lbl.setText(f"{SECONDS_PER_WORD}s")
        self.countdown_bar.setStyleSheet(
            f"QProgressBar{{background:#2d2d44;border-radius:6px;}}"
            f"QProgressBar::chunk{{background:{C_ACCENT};border-radius:6px;}}"
        )

        self._last_prediction = None
        self._last_confidence = 0.0
        if hasattr(self, '_kp_seq'):
            self._kp_seq = []
        if hasattr(self, '_pred_filter'):
            del self._pred_filter

        self._countdown = SECONDS_PER_WORD * 10  # ticks de 100ms
        self._running = True
        self.countdown_timer.start()

    def _tick_countdown(self):
        self._countdown -= 1
        self.countdown_bar.setValue(self._countdown)
        secs_left = self._countdown / 10
        self.countdown_lbl.setText(f"{secs_left:.1f}s")

        # Color del bar según tiempo restante
        if secs_left <= 1.5:
            chunk_color = C_DANGER
        elif secs_left <= 2.5:
            chunk_color = "#f59e0b"
        else:
            chunk_color = C_ACCENT
        self.countdown_bar.setStyleSheet(
            f"QProgressBar{{background:#2d2d44;border-radius:6px;}}"
            f"QProgressBar::chunk{{background:{chunk_color};border-radius:6px;}}"
        )

        if self._countdown <= 0:
            self.countdown_timer.stop()
            self._running = False
            self._evaluate_word()

    def _evaluate_word(self):
        word = self._words[self._current_idx]
        predicted = (self._last_prediction or "").upper()
        correct = (predicted == word)
        conf = self._last_confidence

        self._results.append((word, predicted, correct, conf))

        if correct:
            self.result_lbl.setText(f"✅ ¡Correcto! ({int(conf*100)}%)")
            self.result_lbl.setStyleSheet(f"color:{C_SUCCESS}; background:transparent; font-size:16px; font-weight:bold;")
        else:
            shown = predicted if predicted else "No detectado"
            self.result_lbl.setText(f"❌ Incorrecto — detecté: {shown}")
            self.result_lbl.setStyleSheet(f"color:{C_DANGER}; background:transparent; font-size:16px; font-weight:bold;")

        self._current_idx += 1
        # Pausa de 1.5s para que el usuario vea el resultado antes de la siguiente
        QTimer.singleShot(1500, self._show_word)

    def _finish_evaluation(self):
        self._running = False
        self.countdown_timer.stop()

        correct_count = sum(1 for _, _, ok, _ in self._results if ok)
        total = len(self._results)
        score_pct = int(correct_count / total * 100) if total > 0 else 0

        # Pantalla de resultado final
        self.word_display.setText(f"{correct_count}/{total}")
        self.word_display.setStyleSheet(
            f"color:{C_SUCCESS if score_pct >= 60 else C_DANGER}; background:transparent; "
            f"font-size:42px; font-weight:bold;"
        )
        self.word_sub.setText(f"Puntuación: {score_pct}%  —  {'¡Excelente!' if score_pct>=80 else 'Sigue practicando'}")
        self.progress_lbl.setText("")
        self.result_lbl.setText("")
        self.countdown_lbl.setText("")
        self.countdown_bar.setValue(0)

        # Detalle por seña
        detail = "\n".join(
            f"{'✅' if ok else '❌'}  {w}  →  {pred or 'No detectado'}  ({int(c*100)}%)"
            for w, pred, ok, c in self._results
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("Resultado de la Evaluación")
        msg.setText(
            f"<b>{correct_count} de {total} correctas — {score_pct}%</b><br><br>"
            + detail.replace("\n", "<br>")
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("QLabel{min-width:360px; font-size:13px;}")
        msg.exec_()

        self.btn_start.setEnabled(True)
        self.word_display.setText("¿Repetir?")
        self.word_sub.setText("Pulsa 'Iniciar' para una nueva evaluación")

    # ── CIERRE ───────────────────────────────────────────────────
    def closeEvent(self, event):
        self._running = False
        self.frame_timer.stop()
        self.countdown_timer.stop()
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
    w = EvaluationModeWindow(user_id=2)
    w.show()
    sys.exit(app.exec_())
