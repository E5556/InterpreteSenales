import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QMessageBox, QPushButton, QCheckBox)
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from mediapipe.python.solutions.holistic import Holistic
from datetime import datetime
from helpers import create_folder, draw_keypoints, mediapipe_detection, save_frames, there_hand
from constants import FRAME_ACTIONS_PATH, MIN_LENGTH_FRAMES, CAMERA_INDEX

class ProcessingThread(QThread):
    progress_updated = pyqtSignal(float, str)
    finished_successfully = pyqtSignal(bool)
    
    def __init__(self, gesture_name):
        super().__init__()
        self.gesture_name = gesture_name
    
    def run(self):
        try:
            from training_utils import normalize_and_create_keypoints_single_gesture
            
            def progress_callback(progress, message):
                self.progress_updated.emit(progress, message)
            
            result = normalize_and_create_keypoints_single_gesture(
                self.gesture_name, 
                progress_callback
            )
            self.finished_successfully.emit(result)
            
        except Exception as e:
            self.progress_updated.emit(0.0, f"Error: {str(e)}")
            self.finished_successfully.emit(False)

class CaptureWindow(QWidget):
    def __init__(self, gesture_name, parent=None):
        super().__init__(parent)
        self.gesture_name = gesture_name
        self.gesture_path = os.path.join(FRAME_ACTIONS_PATH, self.gesture_name)

        self.setWindowTitle(f"📹 Intérprete LSC - Captura de Muestras: '{self.gesture_name}'")
        self.setGeometry(100, 100, 950, 750)  # Ventana más grande para video completo
        
        # Configurar icono de la ventana
        self.setWindowIcon(self.create_capture_icon())
        
        # Asegurar que esta ventana no termine la aplicación al cerrarse
        self.setAttribute(Qt.WA_QuitOnClose, False)

        # --- Lógica de Captura Automática ---
        self.holistic_model = Holistic()
        self.frames_sequence = []
        self.count_frame = 0
        self.fix_frames = 0
        self.in_delay_period = False
        self.margin_frame = 1
        self.delay_frames = 5 # Un pequeño margen para evitar cortes accidentales
        
        # --- Interface Layout ---
        main_layout = QVBoxLayout(self)
        
        # Título de la ventana
        title_label = QLabel(f"<h2>📹 Captura de Muestras: '{self.gesture_name}'</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Video área (tamaño real de cámara)
        self.video_label = QLabel("📹 Iniciando cámara...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)  # Tamaño estándar de cámara
        self.video_label.setStyleSheet("border: 2px solid #4CAF50; background-color: black; border-radius: 5px;")
        
        # Frame counter y status en una línea horizontal
        info_layout = QHBoxLayout()
        
        self.frame_counter_label = QLabel("📊 Frames: 0")
        self.frame_counter_label.setStyleSheet("font-weight: bold; color: #333; font-size: 14px;")
        
        self.status_label = QLabel("🎯 Listo para capturar. Muestre una seña a la cámara.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #2E7D32;")
        
        # Contador de muestras capturadas
        self.samples_counter_label = QLabel("📁 Muestras: 0")
        self.samples_counter_label.setStyleSheet("font-weight: bold; color: #1976D2; font-size: 14px;")
        
        info_layout.addWidget(self.frame_counter_label)
        info_layout.addWidget(self.samples_counter_label)
        info_layout.addStretch()
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()
        
        # Agregar todo al layout principal
        main_layout.addWidget(self.video_label)
        main_layout.addLayout(info_layout)
        
        # Botones de navegación
        buttons_layout = QHBoxLayout()
        
        # Botón para finalizar captura y volver
        self.finish_button = QPushButton("✅ Finalizar Captura y Volver", self)
        self.finish_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        # Botón para cerrar sin guardar
        self.cancel_button = QPushButton("❌ Cancelar y Cerrar", self)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c1170b;
            }
        """)
        
        # Botón para procesar muestras capturadas
        self.process_button = QPushButton("⚙️ Procesar Muestras Capturadas", self)
        self.process_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        
        # Agregar botones al layout
        buttons_layout.addWidget(self.finish_button)
        buttons_layout.addWidget(self.process_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(buttons_layout)
        
        # Conectar señales de los botones
        self.finish_button.clicked.connect(self.finish_capture)
        self.cancel_button.clicked.connect(self.cancel_capture)
        self.process_button.clicked.connect(self.process_captured_samples)
        
        # Inicializar contador de muestras existentes
        initial_sample_count = self.count_captured_samples()
        self.samples_counter_label.setText(f"📁 Muestras: {initial_sample_count}")
        
        # Variables para procesamiento manual (si se necesita en el futuro)
        self.processing_thread = None

        # --- Cámara y Timer ---
        try:
            self.capture = cv2.VideoCapture(CAMERA_INDEX)
            if not self.capture.isOpened():
                QMessageBox.warning(self, "Error de Cámara", "No se puede acceder a la cámara.")
                self.capture = None
                return
            
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)
        except Exception as e:
            QMessageBox.critical(self, "Error de Inicialización", f"Error al inicializar la cámara: {str(e)}")
            self.capture = None

    def update_frame(self):
        if not self.capture or not self.capture.isOpened():
            self.status_label.setText("Error: Cámara no disponible.")
            return
            
        ret, frame = self.capture.read()
        if not ret:
            self.status_label.setText("Error: No se puede acceder a la cámara.")
            return

        # Crear copia para dibujar (mantener frame original para guardar)
        image_copy = frame.copy()
        results = mediapipe_detection(frame, self.holistic_model)
        
        # --- Lógica de Estado de Captura ---
        if there_hand(results) or self.in_delay_period:
            self.in_delay_period = False
            self.count_frame += 1
            if self.count_frame > self.margin_frame:
                # Dibujar texto "Capturando..." en el video (como original)
                cv2.putText(image_copy, 'Capturando...', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 50, 0), 2)
                self.frames_sequence.append(np.asarray(frame))
                # Actualizar contador y status
                self.frame_counter_label.setText(f"📊 Frames: {len(self.frames_sequence)}")
                self.status_label.setText(f"🔴 ¡GRABANDO! Frames capturados: {len(self.frames_sequence)}")
        else: # No se detecta mano
            if len(self.frames_sequence) >= MIN_LENGTH_FRAMES + self.margin_frame:
                self.fix_frames += 1
                if self.fix_frames < self.delay_frames:
                    self.in_delay_period = True # Inicia el periodo de espera por si la mano vuelve
                else:
                    self.save_captured_sequence()
                    self.reset_capture_state() # Reinicia para la siguiente captura
            else: # Si la secuencia era muy corta, simplemente reinicia
                self.reset_capture_state()
                # Dibujar texto "Listo para capturar..." en el video (como original)
                cv2.putText(image_copy, 'Listo para capturar...', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 220, 100), 2)
                self.status_label.setText("🎯 Listo para capturar. Muestre una seña a la cámara.")

        # Dibujar keypoints en la imagen (como original)
        draw_keypoints(image_copy, results)

        # Convertir a RGB para PyQt
        rgb_image = cv2.cvtColor(image_copy, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)
        
    def save_captured_sequence(self):
        frames_to_save = self.frames_sequence[: - (self.margin_frame + self.delay_frames)]
        if len(frames_to_save) >= MIN_LENGTH_FRAMES:
            today = datetime.now().strftime('%y%m%d%H%M%S%f')
            output_folder = os.path.join(self.gesture_path, f"sample_{today}")
            create_folder(output_folder)
            save_frames(frames_to_save, output_folder)
            
            # Actualizar contador de muestras
            sample_count = self.count_captured_samples()
            self.samples_counter_label.setText(f"📁 Muestras: {sample_count}")
            
            self.status_label.setText(f"✅ ¡Muestra guardada! ({len(frames_to_save)} frames). Total: {sample_count} muestras.")
        else:
            self.status_label.setText(f"⚠️ Captura muy corta, no guardada. Inténtelo de nuevo.")
    
    def process_gesture(self):
        """Iniciar el procesamiento del gesto en un hilo separado"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.status_label.setText("Ya hay un procesamiento en curso...")
            return
        
        self.status_label.setText(f"Procesando gesto '{self.gesture_name}'...")
        
        self.processing_thread = ProcessingThread(self.gesture_name)
        self.processing_thread.progress_updated.connect(self.on_processing_progress)
        self.processing_thread.finished_successfully.connect(self.on_processing_finished)
        self.processing_thread.start()
    
    def on_processing_progress(self, progress, message):
        """Actualizar el progreso del procesamiento"""
        progress_percent = int(progress * 100)
        self.status_label.setText(f"[{progress_percent}%] {message}")
    
    def on_processing_finished(self, success):
        """Procesamiento terminado"""
        if success:
            self.status_label.setText(f"✅ ¡Procesamiento completado! Muestras listas para entrenamiento.")
            QMessageBox.information(
                self, 
                "Procesamiento Completado", 
                f"✅ ¡Procesamiento exitoso!\n\n"
                f"🤲 Gesto: '{self.gesture_name}'\n"
                f"📊 Muestras procesadas y normalizadas a 20 frames\n"
                f"🔧 Keypoints generados\n\n"
                f"💡 El gesto está listo para entrenamiento."
            )
        else:
            self.status_label.setText("❌ Error en procesamiento. Verifique las muestras capturadas.")
            QMessageBox.warning(
                self, 
                "Error en Procesamiento", 
                "❌ Hubo un error procesando las muestras.\n\n"
                "Verifique que las muestras capturadas sean válidas."
            )

    def reset_capture_state(self):
        self.in_delay_period = False
        self.fix_frames = 0
        self.frames_sequence = []
        self.count_frame = 0
        # Reiniciar contador visual
        self.frame_counter_label.setText("📊 Frames: 0")

    def create_capture_icon(self):
        """Crear icono para la ventana de captura"""
        # Crear un icono simple usando texto/emoji
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

    def finish_capture(self):
        """Finalizar captura y volver al gestor de gestos"""
        # Contar muestras capturadas
        sample_count = self.count_captured_samples()
        
        if sample_count > 0:
            reply = QMessageBox.question(
                self, 
                "Finalizar Captura", 
                f"Has capturado {sample_count} muestras para '{self.gesture_name}'.\n\n"
                f"¿Deseas finalizar la captura y volver al gestor de gestos?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                QMessageBox.information(
                    self, 
                    "Captura Finalizada", 
                    f"✅ Captura completada exitosamente!\n\n"
                    f"📊 Muestras capturadas: {sample_count}\n"
                    f"🤲 Gesto: '{self.gesture_name}'\n\n"
                    f"💡 Puedes procesar estas muestras desde el gestor de gestos."
                )
                self.close()
        else:
            reply = QMessageBox.question(
                self, 
                "Sin Muestras Capturadas", 
                "No se han capturado muestras aún.\n\n¿Deseas cerrar la ventana de captura?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.close()

    def cancel_capture(self):
        """Cancelar captura y cerrar ventana"""
        sample_count = self.count_captured_samples()
        
        if sample_count > 0:
            reply = QMessageBox.question(
                self, 
                "Cancelar Captura", 
                f"Has capturado {sample_count} muestras.\n\n"
                f"¿Estás seguro de que deseas cancelar y cerrar?\n"
                f"Las muestras capturadas se mantendrán guardadas.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.close()
        else:
            self.close()

    def process_captured_samples(self):
        """Procesar las muestras capturadas"""
        sample_count = self.count_captured_samples()
        
        if sample_count == 0:
            QMessageBox.warning(
                self, 
                "Sin Muestras", 
                "No hay muestras capturadas para procesar.\n\n"
                "Primero captura algunas muestras del gesto."
            )
            return
        
        reply = QMessageBox.question(
            self, 
            "Procesar Muestras", 
            f"¿Procesar las {sample_count} muestras capturadas de '{self.gesture_name}'?\n\n"
            f"Esto realizará:\n"
            f"• Normalización a {20} frames\n"
            f"• Creación de keypoints\n"
            f"• Preparación para entrenamiento",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.process_gesture()

    def count_captured_samples(self):
        """Contar el número de muestras capturadas"""
        if not os.path.exists(self.gesture_path):
            return 0
        
        sample_dirs = [d for d in os.listdir(self.gesture_path) 
                      if os.path.isdir(os.path.join(self.gesture_path, d))]
        return len(sample_dirs)

    def closeEvent(self, event):
        # Detener el hilo de procesamiento si está corriendo
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.terminate()
            self.processing_thread.wait()
        
        # Limpiar recursos de forma segura
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        
        if hasattr(self, 'capture') and self.capture:
            self.capture.release()
        
        if hasattr(self, 'holistic_model') and self.holistic_model:
            self.holistic_model.close()
        
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if not os.path.exists(os.path.join(FRAME_ACTIONS_PATH, "test_gesture")):
        os.makedirs(os.path.join(FRAME_ACTIONS_PATH, "test_gesture"))
    
    window = CaptureWindow("test_gesture")
    window.show()
    sys.exit(app.exec_()) 