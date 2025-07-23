import sys
import cv2
import numpy as np
from keras.models import load_model
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QTextEdit, QHBoxLayout, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from mediapipe.python.solutions.holistic import Holistic
from evaluate_model import normalize_keypoints
from helpers import *
from constants import *
from text_to_speech import text_to_speech
from login import LoginWindow
from sessions_window import SessionsWindow
from history_window import HistoryWindow

class AppController:
    def __init__(self):
        self.login_window = LoginWindow(self)
        self.sessions_window = None
        self.main_window = None
        self.history_window = None

    def start(self):
        self.login_window.show()

    def show_sessions_window(self, user_id):
        self.sessions_window = SessionsWindow(user_id, self)
        self.sessions_window.show()

    def start_new_interpreter_session(self, user_id):
        # Aquí iniciaremos la ventana principal pasándole el session_id
        from database import create_session
        session_id = create_session(user_id)
        self.main_window = VideoRecorder(session_id, user_id, self)
        self.main_window.show()

    def show_history_window(self, session_id):
        self.history_window = HistoryWindow(session_id, self)
        self.history_window.show()

    def go_back_to_sessions(self, user_id):
        # Cierra ventanas abiertas y muestra la de sesiones
        if self.main_window:
            self.main_window.close()
        if self.history_window:
            self.history_window.close()
        self.show_sessions_window(user_id)
    
    def logout(self):
        # Cierra todo y vuelve al login
        if self.main_window:
            self.main_window.close()
        if self.history_window:
            self.history_window.close()
        if self.sessions_window:
            self.sessions_window.close()
        self.login_window.show()


class VideoRecorder(QMainWindow):
    def __init__(self, session_id, user_id, controller):
        super().__init__()
        self.session_id = session_id
        self.user_id = user_id
        self.controller = controller
        self.setWindowTitle("Intérprete de Lengua de Señas")
        self.setGeometry(100, 100, 1280, 720)

        # Layout principal
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        # Cambiamos a QVBoxLayout para añadir botones debajo
        main_layout = QVBoxLayout(central_widget)

        # Layout para video y texto (el que ya teníamos)
        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        # Lado izquierdo: Video
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self.video_label, 1)

        # Lado derecho: Texto de interpretación
        right_layout = QVBoxLayout()
        title_label = QLabel("<h2>Interpretación</h2>", self)
        title_label.setAlignment(Qt.AlignCenter)
        self.interpretation_text = QTextEdit(self)
        self.interpretation_text.setReadOnly(True)
        self.interpretation_text.setFontPointSize(14)
        
        right_layout.addWidget(title_label)
        right_layout.addWidget(self.interpretation_text)
        
        top_layout.addLayout(right_layout, 1)
        
        # Botón para volver
        self.back_button = QPushButton("Volver al Menú de Sesiones", self)
        main_layout.addWidget(self.back_button)
        self.back_button.clicked.connect(self.go_back)

        # Configuración de la captura de video
        self.capture = cv2.VideoCapture(0)
        self.init_lsp(session_id)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def init_lsp(self, session_id):
        self.holistic_model = Holistic()
        self.kp_seq, self.sentence = [], []
        self.count_frame = 0
        self.fix_frames = 0
        self.margin_frame = 1
        self.delay_frames = 3
        self.model = load_model(MODEL_PATH)
        self.recording = False

    def update_frame(self):
        word_ids = get_word_ids(WORDS_JSON_PATH)
        ret, frame = self.capture.read()
        if not ret: return

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = mediapipe_detection(frame, self.holistic_model)

        if there_hand(results) or self.recording:
            self.recording = False
            self.count_frame += 1
            if self.count_frame > self.margin_frame:
                self.kp_seq.append(extract_keypoints(results))
        else:
            if self.count_frame >= MIN_LENGTH_FRAMES + self.margin_frame:
                self.fix_frames += 1
                if self.fix_frames < self.delay_frames:
                    self.recording = True
                    return

                self.kp_seq = self.kp_seq[: - (self.margin_frame + self.delay_frames)]
                kp_normalized = normalize_keypoints(self.kp_seq, int(MODEL_FRAMES))
                res = self.model.predict(np.expand_dims(kp_normalized, axis=0))[0]

                if res[np.argmax(res)] > 0.7:
                    word_id = word_ids[np.argmax(res)].split('-')[0]
                    sent = words_text.get(word_id)
                    self.sentence.insert(0, sent)
                    self.interpretation_text.append(sent)
                    text_to_speech(sent)
                    # Guardar en la base de datos
                    from database import add_interpretation
                    add_interpretation(self.session_id, sent)

            self.recording = False
            self.fix_frames = 0
            self.count_frame = 0
            self.kp_seq = []

        draw_keypoints(image, results)

        height, width, channel = image.shape
        step = channel * width
        qImg = QImage(image.data, width, height, step, QImage.Format_RGB888)
        
        # Escalar imagen manteniendo la proporción
        scaled_qImg = qImg.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(QPixmap.fromImage(scaled_qImg))

    def go_back(self):
        self.controller.go_back_to_sessions(self.user_id)

    def closeEvent(self, event):
        self.capture.release()
        # Al cerrar con la 'X', también volvemos al menú
        self.controller.go_back_to_sessions(self.user_id)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AppController()
    controller.start()
    sys.exit(app.exec_())