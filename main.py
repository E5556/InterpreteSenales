import sys
import cv2
import numpy as np
from keras.models import load_model
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QTextEdit, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QMessageBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from mediapipe.python.solutions.holistic import Holistic
from helpers import *
from constants import *
from text_to_speech import text_to_speech
from login import LoginWindow
from sessions_window import SessionsWindow
from history_window import HistoryWindow
from change_password_window import ChangePasswordWindow
from admin_panel import AdminPanel
from gesture_manager_window import GestureManagerWindow
from capture_window import CaptureWindow
from training_dashboard_window import TrainingDashboardWindow
import os

# Función extract_keypoints movida aquí para evitar problemas de importación
def extract_keypoints(results):
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
    lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose, face, lh, rh])

# Función normalize_keypoints movida aquí
def normalize_keypoints(keypoints_sequence, max_frames):
    """
    Normaliza una secuencia de keypoints para que tenga exactamente max_frames frames.
    """
    if len(keypoints_sequence) == 0:
        return np.zeros((max_frames, LENGTH_KEYPOINTS))
    
    # Si la secuencia es más corta que max_frames, la rellenamos con el último frame
    if len(keypoints_sequence) < max_frames:
        last_frame = keypoints_sequence[-1]
        while len(keypoints_sequence) < max_frames:
            keypoints_sequence.append(last_frame)
    
    # Si la secuencia es más larga que max_frames, la truncamos
    if len(keypoints_sequence) > max_frames:
        keypoints_sequence = keypoints_sequence[:max_frames]
    
    return np.array(keypoints_sequence)

class AppController:
    def __init__(self):
        self.login_window = LoginWindow(self)
        self.sessions_window = None
        self.main_window = None
        self.history_window = None
        self.change_password_window = None
        self.admin_panel = None
        self.gesture_manager = None
        self.capture_window = None
        self.training_dashboard = None

    def start(self):
        self.login_window.show()

    def handle_successful_login(self, user_id, role, must_change_password):
        if must_change_password:
            self.show_change_password_window(user_id)
        elif role == 'admin':
            self.show_admin_panel()
        else: # rol es 'user'
            self.show_sessions_window(user_id)

    def show_admin_panel(self):
        self.admin_panel = AdminPanel(self)
        self.admin_panel.show()

    def show_gesture_manager(self):
        self.gesture_manager = GestureManagerWindow(self)
        self.gesture_manager.show()

    def show_capture_window(self, gesture_name):
        self.capture_window = CaptureWindow(gesture_name)
        self.capture_window.show()
        
    def show_training_dashboard(self):
        self.training_dashboard = TrainingDashboardWindow(self)
        self.training_dashboard.show()

    def show_change_password_window(self, user_id):
        self.change_password_window = ChangePasswordWindow(user_id, self)
        self.change_password_window.show()

    def show_sessions_window(self, user_id):
        self.sessions_window = SessionsWindow(user_id, self, is_admin_mode=False)
        self.sessions_window.show()

    def show_user_sessions_for_admin(self, user_id, username):
        self.sessions_window = SessionsWindow(user_id, self, is_admin_mode=True)
        self.sessions_window.setWindowTitle(f"Sesiones de {username}")
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
        if self.admin_panel:
            self.admin_panel.close()
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
        try:
            self.holistic_model = Holistic()
            self.kp_seq, self.sentence = [], []
            self.count_frame = 0
            self.fix_frames = 0
            self.margin_frame = 1
            self.delay_frames = 3
            
            # Cargar el modelo con manejo de errores
            if os.path.exists(MODEL_PATH):
                self.model = load_model(MODEL_PATH)
            else:
                QMessageBox.critical(self, "Error", f"No se encontró el modelo en: {MODEL_PATH}\nPor favor, entrena el modelo primero.")
                self.close()
                return
                
            self.recording = False
        except Exception as e:
            QMessageBox.critical(self, "Error de Inicialización", f"Error al inicializar el sistema: {str(e)}")
            self.close()

    def update_frame(self):
        try:
            # Usar detección automática desde training_utils
            from training_utils import get_gestures_with_samples
            word_ids = get_gestures_with_samples()
            ret, frame = self.capture.read()
            if not ret: 
                print("Error: No se puede leer frame de la cámara")
                return

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
                    
                    try:
                        res = self.model.predict(np.expand_dims(kp_normalized, axis=0), verbose=0)[0]

                        if res[np.argmax(res)] > 0.7:
                            word_id = word_ids[np.argmax(res)].split('-')[0]
                            from constants import get_display_text
                            sent = get_display_text(word_id)
                            if sent:
                                self.sentence.insert(0, sent)
                                self.interpretation_text.append(sent)
                                text_to_speech(sent)
                                # Guardar en la base de datos
                                from database import add_interpretation
                                add_interpretation(self.session_id, sent)
                    except Exception as e:
                        print(f"Error en predicción del modelo: {e}")

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
            
        except Exception as e:
            print(f"Error en update_frame: {e}")
            # Si hay un error crítico, detener el timer
            if hasattr(self, 'timer'):
                self.timer.stop()

    def go_back(self):
        self.controller.go_back_to_sessions(self.user_id)

    def closeEvent(self, event):
        try:
            # Detener el timer
            if hasattr(self, 'timer'):
                self.timer.stop()
            
            # Liberar la cámara
            if hasattr(self, 'capture'):
                self.capture.release()
            
            # Cerrar el modelo Holistic
            if hasattr(self, 'holistic_model'):
                self.holistic_model.close()
                
        except Exception as e:
            print(f"Error al cerrar recursos: {e}")
        
        # Al cerrar con la 'X', también volvemos al menú
        self.controller.go_back_to_sessions(self.user_id)
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Crear directorios necesarios si no existen
    from constants import FRAME_ACTIONS_PATH, KEYPOINTS_PATH
    import os
    os.makedirs(FRAME_ACTIONS_PATH, exist_ok=True)
    os.makedirs(KEYPOINTS_PATH, exist_ok=True)
    print("✅ Sistema iniciado - Detección automática de gestos activa")
    
    controller = AppController()
    controller.start()
    sys.exit(app.exec_())