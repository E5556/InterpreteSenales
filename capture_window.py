import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QMessageBox, QPushButton, QCheckBox)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from mediapipe.python.solutions.holistic import Holistic
from datetime import datetime
from helpers import create_folder, draw_keypoints, mediapipe_detection, save_frames, there_hand
from constants import FRAME_ACTIONS_PATH, MIN_LENGTH_FRAMES

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

        self.setWindowTitle(f"Toma de muestras para '{self.gesture_name}'")
        self.setGeometry(100, 100, 900, 700)  # Ventana más grande para video completo
        
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
        
        # Video área (tamaño real de cámara)
        self.video_label = QLabel("Iniciando cámara...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)  # Tamaño estándar de cámara
        self.video_label.setStyleSheet("border: 1px solid #ccc; background-color: black;")
        
        # Frame counter y status en una línea horizontal
        info_layout = QHBoxLayout()
        
        self.frame_counter_label = QLabel("Frames: 0")
        self.frame_counter_label.setStyleSheet("font-weight: bold; color: #333;")
        
        self.status_label = QLabel("Listo para capturar. Muestre una seña a la cámara.")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        info_layout.addWidget(self.frame_counter_label)
        info_layout.addStretch()
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()
        
        # Agregar todo al layout principal
        main_layout.addWidget(self.video_label)
        main_layout.addLayout(info_layout)
        
        # Variables para procesamiento manual (si se necesita en el futuro)
        self.processing_thread = None

        # --- Cámara y Timer ---
        try:
            self.capture = cv2.VideoCapture(0)
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
                self.frame_counter_label.setText(f"Frames: {len(self.frames_sequence)}")
                self.status_label.setText(f"¡GRABANDO! Frames capturados: {len(self.frames_sequence)}")
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
                self.status_label.setText("Listo para capturar. Muestre una seña a la cámara.")

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
            self.status_label.setText(f"¡Muestra guardada! ({len(frames_to_save)} frames). Listo para la siguiente.")
        else:
            self.status_label.setText(f"Captura muy corta, no guardada. Inténtelo de nuevo.")
    
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
            self.status_label.setText(f"¡Procesamiento completado! Listo para capturar más.")
        else:
            self.status_label.setText("Error en procesamiento automático. Continúe capturando.")

    def reset_capture_state(self):
        self.in_delay_period = False
        self.fix_frames = 0
        self.frames_sequence = []
        self.count_frame = 0
        # Reiniciar contador visual
        self.frame_counter_label.setText("Frames: 0")

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