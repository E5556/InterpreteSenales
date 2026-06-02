import sys
import os
import cv2
import numpy as np
import time
import threading

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

def _interp_subspace(frames_array, target_length):
    """Interpola un subespacio (pose/cara/mano) por separado preservando su geometría."""
    n = len(frames_array)
    if n == target_length:
        return frames_array
    indices = np.linspace(0, n - 1, target_length)
    result = []
    for i in indices:
        lo = int(np.floor(i))
        hi = int(np.ceil(i))
        w = i - lo
        if lo == hi:
            result.append(frames_array[lo])
        else:
            result.append((1 - w) * frames_array[lo] + w * frames_array[hi])
    return result

def normalize_keypoints(keypoints, target_length=15):
    """
    Normaliza la secuencia a target_length frames usando interpolación por subespacio.
    Interpola pose (132), cara (1404), mano izq (63) y mano der (63) por separado
    para preservar la geometría de cada subespacio antes de concatenar.
    """
    arr = [np.array(kp) for kp in keypoints]
    # Separar subespacios
    pose   = [kp[:132]       for kp in arr]
    face   = [kp[132:1536]   for kp in arr]
    lh     = [kp[1536:1599]  for kp in arr]
    rh     = [kp[1599:]      for kp in arr]

    pose_i = _interp_subspace(pose, target_length)
    face_i = _interp_subspace(face, target_length)
    lh_i   = _interp_subspace(lh,   target_length)
    rh_i   = _interp_subspace(rh,   target_length)

    return [np.concatenate([pose_i[i], face_i[i], lh_i[i], rh_i[i]])
            for i in range(target_length)]

# Importar la función correcta para obtener gestos
from training_utils import get_gestures_with_valid_keypoints
from prediction_filter import PredictionFilter
from conversation_manager import ConversationManager

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
        self.learning_mode_window = None
        self.gamification_window = None

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

    def show_learning_mode(self):
        from learning_mode_window import LearningModeWindow
        self.learning_mode_window = LearningModeWindow()
        self.learning_mode_window.show()

    def show_gamification(self, user_id):
        from gamification_window import GamificationWindow
        self.gamification_window = GamificationWindow(user_id, self)
        self.gamification_window.show()
    
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
        if self.main_window:
            self.main_window.close()
        if self.history_window:
            self.history_window.close()
        if self.sessions_window:
            self.sessions_window.close()
            self.sessions_window = None
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
        title_label = QLabel("<h2>Interpretación en Tiempo Real</h2>", self)
        title_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(title_label)

        # Indicador de estado de detección
        self.status_label = QLabel("Estado: Esperando manos...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "QLabel { background-color: #444; color: #aaa; padding: 4px; border-radius: 4px; font-size: 12px; }"
        )
        right_layout.addWidget(self.status_label)

        # Frase en construcción (gesto actual acumulado)
        self.phrase_label = QLabel("Frase actual: —", self)
        self.phrase_label.setAlignment(Qt.AlignCenter)
        self.phrase_label.setStyleSheet(
            "QLabel { background-color: #1a3a5c; color: #7ec8e3; padding: 6px; "
            "border-radius: 4px; font-size: 13px; font-weight: bold; }"
        )
        right_layout.addWidget(self.phrase_label)

        # Historial de interpretación
        self.interpretation_text = QTextEdit(self)
        self.interpretation_text.setReadOnly(True)
        self.interpretation_text.setFontPointSize(14)
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
        self.sensitivity_slider.setValue(65)    # 0.65 umbral inicial
        self.sensitivity_slider.valueChanged.connect(self.adjust_sensitivity)
        controls_layout.addWidget(self.sensitivity_slider)
        
        # Botón para hablar la frase acumulada manualmente
        self.speak_button = QPushButton("🔊 Hablar Frase", self)
        self.speak_button.clicked.connect(self.speak_current_phrase)
        controls_layout.addWidget(self.speak_button)

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
            self.delay_frames = 2
            self.confidence_threshold = 0.65

            self.prediction_filter = PredictionFilter(window_size=3, confidence_threshold=self.confidence_threshold)
            self.conversation_manager = ConversationManager(
                max_phrase_length=10,
                gesture_timeout=3.0,
                confidence_threshold=self.confidence_threshold
            )

            # Cooldown: evita registrar el mismo gesto dos veces seguidas rápido
            self.last_gesture_name = None
            self.last_gesture_time = 0.0
            self.gesture_cooldown = 1.5   # segundos mínimos entre el mismo gesto
            self.any_gesture_cooldown = 0.4  # segundos mínimos entre cualquier gesto

            print(f"Cargando modelo desde: {MODEL_PATH}")
            self.model = load_model(MODEL_PATH)
            self.recording = False

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
            hand_present = there_hand(results)

            # Actualizar ConversationManager con estado de manos
            self.conversation_manager.update_hands_detection(hand_present)

            if hand_present or self.recording:
                self.recording = False
                self.count_frame += 1
                if self.count_frame > self.margin_frame:
                    self.kp_seq.append(extract_keypoints(results))

                # Feedback: mano detectada acumulando frames
                frames_acum = len(self.kp_seq)
                self.status_label.setText(f"Grabando gesto... ({frames_acum} frames)")
                self.status_label.setStyleSheet(
                    "QLabel { background-color: #1a5c1a; color: #7ecc7e; padding: 4px; border-radius: 4px; font-size: 12px; }"
                )
            else:
                if self.count_frame >= MIN_LENGTH_FRAMES + self.margin_frame:
                    self.fix_frames += 1
                    if self.fix_frames < self.delay_frames:
                        self.recording = True
                        # Feedback: esperando confirmación de fin de gesto
                        self.status_label.setText(f"Confirmando fin de gesto... ({self.fix_frames}/{self.delay_frames})")
                        self.status_label.setStyleSheet(
                            "QLabel { background-color: #5c4a1a; color: #ccb87e; padding: 4px; border-radius: 4px; font-size: 12px; }"
                        )
                        return

                    # --- Procesar secuencia ---
                    trim = self.margin_frame + self.delay_frames
                    if len(self.kp_seq) > trim:
                        self.kp_seq = self.kp_seq[:-trim]

                    if len(self.kp_seq) >= MIN_LENGTH_FRAMES:
                        kp_normalized = normalize_keypoints(self.kp_seq, int(MODEL_FRAMES))
                        res = self.model.predict(np.expand_dims(kp_normalized, axis=0), verbose=0)[0]

                        gesture_name, confidence = self.prediction_filter.add_prediction(res, self.word_ids)

                        # Feedback de confianza en status
                        pct = int(confidence * 100)
                        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
                        self.status_label.setText(f"Confianza: {bar} {pct}%  |  {gesture_name}")
                        self.status_label.setStyleSheet(
                            "QLabel { background-color: #1a3a5c; color: #7ec8e3; padding: 4px; border-radius: 4px; font-size: 12px; }"
                        )

                        if confidence >= self.confidence_threshold:
                            word_id = gesture_name.split('-')[0]
                            sent = get_display_text(word_id)
                            if sent:
                                now = time.time()
                                # Cooldown: mismo gesto no se repite antes de gesture_cooldown
                                same_gesture_ok = (
                                    gesture_name != self.last_gesture_name or
                                    (now - self.last_gesture_time) >= self.gesture_cooldown
                                )
                                any_gesture_ok = (now - self.last_gesture_time) >= self.any_gesture_cooldown

                                if same_gesture_ok and any_gesture_ok:
                                    # Agregar al ConversationManager
                                    self.conversation_manager.add_gesture(sent, confidence, now)
                                    self.last_gesture_name = gesture_name
                                    self.last_gesture_time = now
                                    print(f"GESTO RECONOCIDO: {sent} ({pct}%)")
                                    # Guardar en BD — solo gestos individuales del modelo actual
                                    try:
                                        from database import add_interpretation
                                        if gesture_name in self.word_ids:
                                            add_interpretation(self.session_id, gesture_name.upper(), confidence)
                                    except Exception as _e:
                                        print(f"[BD] Error guardando interpretación: {_e}")
                                    # Acumular confidence para gamificación
                                    self._conf_sum = getattr(self, '_conf_sum', 0.0) + confidence
                                    self._conf_count = getattr(self, '_conf_count', 0) + 1
                                    self._session_avg_confidence = self._conf_sum / self._conf_count

                    self.prediction_filter.reset()

                else:
                    # Secuencia demasiado corta — ignorar silenciosamente
                    pass

                # Reset estado de captura
                self.recording = False
                self.fix_frames = 0
                self.count_frame = 0
                self.kp_seq = []

                # Feedback idle
                if not hand_present:
                    self.status_label.setText("Esperando manos...")
                    self.status_label.setStyleSheet(
                        "QLabel { background-color: #444; color: #aaa; padding: 4px; border-radius: 4px; font-size: 12px; }"
                    )

            # Actualizar frase en construcción desde ConversationManager
            current_phrase = self.conversation_manager.get_current_phrase()
            if current_phrase:
                self.phrase_label.setText(f"Frase actual: {current_phrase}")
            else:
                self.phrase_label.setText("Frase actual: —")

            # Verificar si ConversationManager completó una frase por timeout
            completed = self.conversation_manager.check_timeout()
            if completed:
                print(f"FRASE COMPLETADA: {completed}")
                self.interpretation_text.append(f">> {completed}")
                self.phrase_label.setText("Frase actual: —")
                threading.Thread(target=text_to_speech, args=(completed,), daemon=True).start()

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
        """Ajustar el umbral de confianza en PredictionFilter y ConversationManager."""
        threshold = value / 100.0
        self.confidence_threshold = threshold
        if hasattr(self, 'prediction_filter'):
            self.prediction_filter.confidence_threshold = threshold
        if hasattr(self, 'conversation_manager'):
            self.conversation_manager.set_confidence_threshold(threshold)
        print(f"Umbral de confianza: {threshold:.2f}")
        
    def speak_current_phrase(self):
        """Habla la frase acumulada manualmente y la registra."""
        phrase = self.conversation_manager.force_complete_phrase()
        if phrase:
            self.interpretation_text.append(f">> {phrase}")
            self.phrase_label.setText("Frase actual: —")
            threading.Thread(target=text_to_speech, args=(phrase,), daemon=True).start()
            print(f"FRASE MANUAL: {phrase}")

    def clear_conversation(self):
        """Limpiar la conversación actual"""
        self.sentence = []
        self.interpretation_text.clear()
        self.phrase_label.setText("Frase actual: —")
        if hasattr(self, 'conversation_manager'):
            self.conversation_manager.reset()
        if hasattr(self, 'prediction_filter'):
            self.prediction_filter.reset()
        self.last_gesture_name = None
        self.last_gesture_time = 0.0
        print("Conversación limpiada")

    def closeEvent(self, event):
        try:
            if hasattr(self, 'timer'):
                self.timer.stop()
            if hasattr(self, 'capture') and self.capture is not None:
                self.capture.release()
            if hasattr(self, 'holistic_model'):
                self.holistic_model.close()
        except Exception as e:
            print(f"Error al cerrar recursos: {e}")

        # Registrar puntos de la sesión y mostrar logros nuevos
        try:
            gestures = len(self.sentence) if hasattr(self, 'sentence') else 0
            acc = getattr(self, '_session_avg_confidence', 0.0)
            if gestures > 0:
                from gamification_db import award_session_points
                try:
                    new_ach = award_session_points(self.user_id, self.session_id, gestures, acc)
                    if new_ach:
                        from PyQt5.QtWidgets import QMessageBox
                        msg = QMessageBox(self)
                        msg.setWindowTitle("🏆 ¡Logros desbloqueados!")
                        msg.setText(
                            "<b>¡Felicitaciones!</b><br><br>"
                            + "".join(f"🏅 {a}<br>" for a in new_ach)
                            + "<br>Estos logros ya aparecen en <b>Mis Logros</b>."
                        )
                        msg.setIcon(QMessageBox.NoIcon)
                        msg.setStandardButtons(QMessageBox.Ok)
                        msg.setStyleSheet("QLabel{min-width:320px;font-size:14px;}")
                        msg.exec_()
                except Exception as ex:
                    print(f"[Gamificación] Error al guardar puntos: {ex}")
        except Exception as e:
            print(f"[Gamificación] Error preparando puntos: {e}")

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