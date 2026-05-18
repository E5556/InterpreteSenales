import sys
import os
import cv2
import numpy as np
import time

# Configurar variables de entorno para suprimir advertencias de CUDA
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suprimir advertencias de TensorFlow
os.environ['CUDA_VISIBLE_DEVICES'] = ''   # Forzar uso de CPU

from keras.models import load_model
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QTextEdit, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QMessageBox, QCheckBox, QSlider
from PyQt5.QtGui import QImage, QPixmap, QIcon
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
# Importaciones simplificadas - solo las necesarias
import os

# Función extract_keypoints movida aquí para evitar problemas de importación
def extract_keypoints(results):
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
    lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose, face, lh, rh])

# Función normalize_keypoints basada en el código funcional
def normalize_keypoints(keypoints, target_length=15):
    """
    Normaliza keypoints usando interpolación como en el código funcional
    """
    current_length = len(keypoints)
    if current_length == target_length:
        return keypoints
    
    # Interpolación lineal como en evaluate_model.py
    indices = np.linspace(0, current_length - 1, target_length)
    interpolated_keypoints = []
    for i in indices:
        lower_idx = int(np.floor(i))
        upper_idx = int(np.ceil(i))
        weight = i - lower_idx
        if lower_idx == upper_idx:
            interpolated_keypoints.append(keypoints[lower_idx])
        else:
            interpolated_point = (1 - weight) * np.array(keypoints[lower_idx]) + weight * np.array(keypoints[upper_idx])
            interpolated_keypoints.append(interpolated_point.tolist())
    
    return interpolated_keypoints

# Importar la función correcta para obtener gestos
from training_utils import get_gestures_with_valid_keypoints
from prediction_filter import PredictionFilter

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
    
    def show_statistics(self, user_id=None, user_role='user'):
        """Muestra las estadísticas del usuario o del sistema"""
        try:
            stats = EstadisticasIntegrado()
            if user_role == 'admin':
                stats.mostrar_estadisticas_consola()  # Estadísticas del sistema
            else:
                stats.mostrar_estadisticas_consola(user_id)  # Estadísticas del usuario
        except Exception as e:
            print(f"❌ Error mostrando estadísticas: {e}")

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
        self.setWindowTitle("🎥 Intérprete LSC - Traducción en Tiempo Real")
        self.setGeometry(100, 100, 1280, 720)
        
        # Configurar icono de la ventana
        self.setWindowIcon(self.create_interpreter_icon())

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
        title_label = QLabel("<h2>📝 Interpretación en Tiempo Real</h2>", self)
        title_label.setAlignment(Qt.AlignCenter)
        self.interpretation_text = QTextEdit(self)
        self.interpretation_text.setReadOnly(True)
        self.interpretation_text.setFontPointSize(14)
        
        right_layout.addWidget(title_label)
        right_layout.addWidget(self.interpretation_text)
        
        top_layout.addLayout(right_layout, 1)
        
        # Controles de conversación
        controls_layout = QHBoxLayout()
        
        # Checkbox para modo conversación
        self.conversation_checkbox = QCheckBox("💬 Modo Conversación Continua", self)
        self.conversation_checkbox.setChecked(True)
        self.conversation_checkbox.stateChanged.connect(self.toggle_conversation_mode)
        controls_layout.addWidget(self.conversation_checkbox)
        
        # Slider para ajustar sensibilidad
        sensitivity_label = QLabel("Sensibilidad:", self)
        controls_layout.addWidget(sensitivity_label)
        
        self.sensitivity_slider = QSlider(Qt.Horizontal, self)
        self.sensitivity_slider.setMinimum(50)  # 0.5 (menos sensible)
        self.sensitivity_slider.setMaximum(95)  # 0.95 (muy sensible)
        self.sensitivity_slider.setValue(60)    # 0.6 (valor inicial más permisivo)
        self.sensitivity_slider.valueChanged.connect(self.adjust_sensitivity)
        controls_layout.addWidget(self.sensitivity_slider)
        
        # Botón para limpiar conversación
        self.clear_button = QPushButton("🗑️ Limpiar Conversación", self)
        self.clear_button.clicked.connect(self.clear_conversation)
        controls_layout.addWidget(self.clear_button)
        
        # Botón para volver
        self.back_button = QPushButton("🔙 Volver al Menú de Sesiones", self)
        controls_layout.addWidget(self.back_button)
        self.back_button.clicked.connect(self.go_back)
        
        main_layout.addLayout(controls_layout)

        # Configuración de la captura de video con manejo de errores mejorado
        self.capture = None
        self.init_camera()
        self.init_lsp(session_id)
        
        # Variables simples como en el código funcional
        self.conversation_mode = True
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def init_camera(self):
        """Inicializa la cámara con manejo robusto de errores"""
        print("📹 Inicializando cámara...")
        
        # Intentar diferentes índices de cámara si el configurado falla
        camera_indices = [CAMERA_INDEX, 0, 1, 2, 3]
        
        for camera_index in camera_indices:
            try:
                print(f"   Probando cámara {camera_index}...")
                self.capture = cv2.VideoCapture(camera_index)
                
                if not self.capture.isOpened():
                    print(f"   ❌ Cámara {camera_index} no se puede abrir")
                    continue
                
                # Configurar propiedades de la cámara
                self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.capture.set(cv2.CAP_PROP_FPS, 30)
                
                # Probar lectura de frame
                ret, frame = self.capture.read()
                if ret and frame is not None:
                    print(f"   OK: Camara {camera_index} inicializada correctamente")
                    return True
                else:
                    print(f"   ⚠️ Cámara {camera_index} no puede leer frames")
                    self.capture.release()
                    continue
                    
            except Exception as e:
                print(f"   ❌ Error con cámara {camera_index}: {e}")
                if self.capture:
                    self.capture.release()
                continue
        
        # Si llegamos aquí, ninguna cámara funcionó
        print("❌ No se pudo inicializar ninguna cámara")
        QMessageBox.critical(
            self, 
            "Error de Cámara", 
            "No se pudo acceder a ninguna cámara.\n\n"
            "Posibles soluciones:\n"
            "• Cerrar otras aplicaciones que usen la cámara\n"
            "• Verificar que la cámara esté conectada\n"
            "• Reiniciar la aplicación\n"
            "• Ejecutar como administrador"
        )
        self.capture = None
        return False

    def reintentar_camara(self):
        """Reintenta inicializar la cámara si falla"""
        print("🔄 Reintentando inicializar cámara...")
        
        # Liberar cámara actual si existe
        if self.capture:
            self.capture.release()
            self.capture = None
        
        # Esperar un momento antes de reintentar
        import time
        time.sleep(1)
        
        # Intentar inicializar nuevamente
        if self.init_camera():
            print("OK: Camara reinicializada exitosamente")
        else:
            print("❌ No se pudo reinicializar la cámara")

    def init_lsp(self, session_id):
        try:
            print("Inicializando sistema LSP...")
            self.holistic_model = Holistic()
            self.kp_seq, self.sentence = [], []
            self.count_frame = 0
            self.fix_frames = 0
            self.margin_frame = 1
            self.delay_frames = 5  # Igual que en capture_window para consistencia con entrenamiento
            self.prediction_filter = PredictionFilter(window_size=3, confidence_threshold=0.7)
            
            # Cargar modelo como en el código funcional
            print(f"Cargando modelo desde: {MODEL_PATH}")
            self.model = load_model(MODEL_PATH)
            self.recording = False
            
            # Obtener word_ids una sola vez al inicializar
            self.word_ids = get_gestures_with_valid_keypoints()
            print(f"Modelo verificado: {self.model.input_shape} -> {self.model.output_shape}")
            
            print("Sistema LSP inicializado correctamente")
            
        except Exception as e:
            print(f"Error en inicialización: {e}")
            QMessageBox.critical(
                self, 
                "Error de Inicialización", 
                f"Error al inicializar el sistema:\n{str(e)}\n\n"
                f"Por favor, verifique la configuración y reinicie la aplicación."
            )
            self.close()

    def update_frame(self):
        try:
            # Verificar que la cámara esté disponible
            if self.capture is None:
                return
            
            ret, frame = self.capture.read()
            if not ret: 
                print("Error: No se puede leer frame de la cámara")
                return

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = mediapipe_detection(frame, self.holistic_model)

            # Lógica simplificada basada en el código funcional
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

                    trim = self.margin_frame + self.delay_frames
                    if len(self.kp_seq) > trim:
                        self.kp_seq = self.kp_seq[:-trim]
                    if len(self.kp_seq) < MIN_LENGTH_FRAMES:
                        pass  # Secuencia demasiado corta, ignorar
                    else:
                        kp_normalized = normalize_keypoints(self.kp_seq, int(MODEL_FRAMES))
                        res = self.model.predict(np.expand_dims(kp_normalized, axis=0))[0]

                        # Suavizar predicción con PredictionFilter (votación por ventana)
                        gesture_name, confidence = self.prediction_filter.add_prediction(res, self.word_ids)
                        if confidence > 0.7:
                            word_id = gesture_name.split('-')[0]
                            sent = get_display_text(word_id)
                            if sent:
                                self.sentence.insert(0, sent)
                                self.interpretation_text.append(f"• {sent}")
                                text_to_speech(sent)
                                print(f"GESTO RECONOCIDO: {sent} (confianza: {confidence:.2f})")
                        self.prediction_filter.reset()

                self.recording = False
                self.fix_frames = 0
                self.count_frame = 0
                self.kp_seq = []

            # Actualizar display de frase como en el código funcional
            self.interpretation_text.setText(" - ".join(self.sentence))
            draw_keypoints(image, results)

            height, width, channel = image.shape
            step = channel * width
            qImg = QImage(image.data, width, height, step, QImage.Format_RGB888)
            scaled_qImg = qImg.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.video_label.setPixmap(QPixmap.fromImage(scaled_qImg))
            
        except Exception as e:
            print(f"Error en update_frame: {e}")

    def go_back(self):
        self.controller.go_back_to_sessions(self.user_id)

    def create_interpreter_icon(self):
        """Crear icono para la ventana de interpretación"""
        # Crear un icono simple usando texto/emoji
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)
    
    def toggle_conversation_mode(self, state):
        """Alternar entre modo conversación y modo tradicional"""
        self.conversation_mode = state == Qt.Checked
        if self.conversation_mode:
            print("Modo conversación continua activado")
        else:
            print("Modo tradicional activado")
            
    def adjust_sensitivity(self, value):
        """Ajustar la sensibilidad del detector"""
        threshold = value / 100.0
        print(f"Sensibilidad ajustada a: {threshold:.2f}")
        
    def clear_conversation(self):
        """Limpiar la conversación actual"""
        self.sentence = []
        self.interpretation_text.clear()
        print("Conversación limpiada")

    def closeEvent(self, event):
        try:
            # Detener el timer
            if hasattr(self, 'timer'):
                self.timer.stop()
            
            # Liberar la cámara correctamente
            if hasattr(self, 'capture') and self.capture is not None:
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
    print("OK: Sistema iniciado - Deteccion automatica de gestos activa")
    
    controller = AppController()
    controller.start()
    sys.exit(app.exec_())