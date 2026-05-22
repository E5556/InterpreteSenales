import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QSpinBox, QTextEdit, QScrollArea,
                             QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
from training_utils import (create_keypoints_for_all_gestures, normalize_and_create_keypoints,
                            train_model_logic, plot_training_history, generate_confusion_matrix_logic)
import os
from constants import FRAME_ACTIONS_PATH

# Worker para ejecutar tareas pesadas en un hilo separado
class WorkerThread(QThread):
    progress = pyqtSignal(float, str)
    # Cambiamos la señal para que emita una cadena de texto formateada
    epoch_log_update = pyqtSignal(str) 
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, task, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        # Pasamos una referencia del hilo al callback del entrenamiento
        if 'epoch_callback' in self.kwargs:
            self.kwargs['epoch_callback'] = self.emit_epoch_log
        
        # Si hay un progress_callback, lo reemplazamos con nuestro método que emite señales
        if 'progress_callback' in self.kwargs:
            if self.kwargs['progress_callback'] is True or self.kwargs['progress_callback'] is not None:
                self.kwargs['progress_callback'] = self.emit_progress
            else:
                # Si es None o False, lo eliminamos para evitar errores
                del self.kwargs['progress_callback']

    def emit_progress(self, value, message):
        """Emite señal de progreso (thread-safe)"""
        self.progress.emit(value, message)

    def emit_epoch_log(self, epoch, logs):
        log_msg = (f"Época {epoch}: "
                   f"loss: {logs.get('loss', 0):.4f}, "
                   f"accuracy: {logs.get('accuracy', 0):.4f}, "
                   f"val_loss: {logs.get('val_loss', 0):.4f}, "
                   f"val_accuracy: {logs.get('val_accuracy', 0):.4f}")
        self.epoch_log_update.emit(log_msg)

    def run(self):
        try:
            result = self.task(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class TrainingDashboardWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("🧠 Intérprete LSC - Panel de Entrenamiento del Modelo")
        self.setGeometry(300, 300, 1300, 950)  # Ventana más grande para las imágenes
        self.thread = None
        
        # Configurar icono de la ventana
        self.setWindowIcon(self.create_training_icon())
        
        # Asegurar que esta ventana no termine la aplicación al cerrarse
        self.setAttribute(Qt.WA_QuitOnClose, False)

        # --- Layouts y Widgets ---
        main_layout = QVBoxLayout(self)
        
        # Título del panel
        title_label = QLabel("<h2>🧠 Panel de Entrenamiento del Modelo LSC</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Crear área de scroll para el contenido principal
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(400)  # Altura mínima para el área de scroll
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ccc;
                background-color: white;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
            }
        """)
        
        # Widget contenedor para el contenido scrolleable
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)  # Espaciado entre elementos
        scroll_layout.setContentsMargins(10, 10, 10, 10)  # Márgenes internos
        
        top_controls_layout = QHBoxLayout()
        
        # Controles de entrenamiento
        self.epochs_input = QSpinBox()
        self.epochs_input.setRange(1, 2000)
        self.epochs_input.setValue(500)
        self.process_keypoints_button = QPushButton("⚙️ 1. Normalizar + Procesar Keypoints")
        self.process_keypoints_button.setToolTip("Normaliza muestras a 15 frames y crea keypoints")
        self.train_button = QPushButton("🚀 2. Iniciar Entrenamiento")

        from PyQt5.QtWidgets import QCheckBox
        self.force_reprocess_checkbox = QCheckBox("Forzar reprocesamiento completo")
        self.force_reprocess_checkbox.setChecked(False)
        self.force_reprocess_checkbox.setToolTip(
            "Desmarcado: salta gestos cuyo .h5 ya está actualizado (más rápido).\n"
            "Marcado: reprocesa todos los gestos desde cero."
        )

        top_controls_layout.addWidget(QLabel("Épocas de Entrenamiento:"))
        top_controls_layout.addWidget(self.epochs_input)
        top_controls_layout.addWidget(self.process_keypoints_button)
        top_controls_layout.addWidget(self.force_reprocess_checkbox)
        top_controls_layout.addWidget(self.train_button)

        # Log y Progreso
        self.progress_bar = QProgressBar()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(200)  # Altura mínima para el área de logs
        
        # Visor de Gráficas
        self.history_plot_label = QLabel("La gráfica del historial de entrenamiento aparecerá aquí.")
        self.history_plot_label.setAlignment(Qt.AlignCenter)
        self.history_plot_label.setMinimumSize(800, 300)  # Tamaño mínimo más grande
        self.history_plot_label.setStyleSheet("QLabel { border: 2px solid #ccc; background-color: #f9f9f9; }")
        
        self.matrix_plot_label = QLabel("La matriz de confusión aparecerá aquí.")
        self.matrix_plot_label.setAlignment(Qt.AlignCenter)
        self.matrix_plot_label.setMinimumSize(600, 600)  # Tamaño mínimo más grande para matriz cuadrada
        self.matrix_plot_label.setStyleSheet("QLabel { border: 2px solid #ccc; background-color: #f9f9f9; }")
        
        self.show_matrix_button = QPushButton("📊 Mostrar Matriz de Confusión (Post-Entrenamiento)")

        # Añadir elementos al layout de scroll con separadores
        scroll_layout.addLayout(top_controls_layout)
        scroll_layout.addWidget(self.progress_bar)
        
        # Separador visual para el área de logs
        logs_label = QLabel("<h3>📝 Logs de Procesamiento</h3>")
        logs_label.setStyleSheet("color: #333; margin-top: 10px;")
        scroll_layout.addWidget(logs_label)
        scroll_layout.addWidget(self.log_area)
        
        # Separador visual para las gráficas
        graphs_label = QLabel("<h3>📊 Gráficas de Entrenamiento</h3>")
        graphs_label.setStyleSheet("color: #333; margin-top: 10px;")
        scroll_layout.addWidget(graphs_label)
        scroll_layout.addWidget(self.history_plot_label)
        
        # Separador visual para la matriz de confusión
        matrix_label = QLabel("<h3>🎯 Matriz de Confusión</h3>")
        matrix_label.setStyleSheet("color: #333; margin-top: 10px;")
        scroll_layout.addWidget(matrix_label)
        scroll_layout.addWidget(self.matrix_plot_label)
        scroll_layout.addWidget(self.show_matrix_button)
        
        # Configurar el área de scroll
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Conexiones
        self.process_keypoints_button.clicked.connect(self.start_keypoint_processing)
        self.train_button.clicked.connect(self.start_training)
        self.show_matrix_button.clicked.connect(self.show_confusion_matrix)

    def start_keypoint_processing(self):
        skip = not self.force_reprocess_checkbox.isChecked()
        mode = "completo (reprocesa todo)" if not skip else "incremental (salta gestos sin cambios)"
        self.log_area.setText(f"Iniciando procesamiento {mode}...")
        self.log_area.append("1. Detectar gestos disponibles")
        self.log_area.append("2. Normalizar muestras a 15 frames")
        self.log_area.append("3. Crear keypoints para entrenamiento")
        self.log_area.append("")

        self.process_keypoints_button.setDisabled(True)

        self.thread = WorkerThread(normalize_and_create_keypoints, progress_callback=True, skip_existing=skip)
        self.thread.progress.connect(self.update_progress_from_signal)
        self.thread.finished.connect(self.on_keypoint_processing_finished)
        self.thread.error.connect(self.on_task_error)
        self.thread.start()

    def update_progress_from_signal(self, value, message):
        """Actualiza el progreso desde una señal Qt (thread-safe)"""
        self.progress_bar.setValue(int(value * 100))
        self.log_area.append(message)

    def on_keypoint_processing_finished(self, result):
        self.log_area.append("\n¡Procesamiento de keypoints completado!")
        self.process_keypoints_button.setDisabled(False)
        QMessageBox.information(self, "Éxito", "Todos los keypoints han sido procesados y guardados.")

    def start_training(self):
        epochs = self.epochs_input.value()
        self.log_area.clear()
        self.log_area.append(f"Iniciando entrenamiento por {epochs} épocas...")
        self.train_button.setDisabled(True)
        
        # Ya no pasamos el callback directamente aquí
        self.thread = WorkerThread(train_model_logic, epochs=epochs, epoch_callback=True)
        self.thread.epoch_log_update.connect(self.update_log_from_thread) # Nueva conexión
        self.thread.finished.connect(self.on_training_finished)
        self.thread.error.connect(self.on_task_error)
        self.thread.start()

    def update_log_from_thread(self, log_msg):
        self.log_area.append(log_msg)
        # Actualizar la barra de progreso
        try:
            epoch_str = log_msg.split(':')[0].replace('Época', '').strip()
            epoch_num = int(epoch_str)
            self.progress_bar.setValue(int((epoch_num / self.epochs_input.value()) * 100))
        except (ValueError, IndexError):
            pass # Ignorar si el formato no es el esperado

    def on_training_finished(self, history):
        self.log_area.append("\n¡Entrenamiento completado!")
        self.train_button.setDisabled(False)
        self.progress_bar.setValue(100)
        
        plot_path = plot_training_history(history)
        pixmap = QPixmap(plot_path)
        # Escalar la imagen para que se ajuste al label manteniendo proporción
        scaled_pixmap = pixmap.scaled(self.history_plot_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.history_plot_label.setPixmap(scaled_pixmap)
        self.history_plot_label.setToolTip(f"Gráfica guardada en: {plot_path}")
        QMessageBox.information(self, "Éxito", "El modelo ha sido entrenado y guardado correctamente.")

    def show_confusion_matrix(self):
        self.log_area.append("\nGenerando matriz de confusión...")
        self.show_matrix_button.setDisabled(True)
        
        self.thread = WorkerThread(generate_confusion_matrix_logic)
        self.thread.finished.connect(self.on_matrix_finished)
        self.thread.error.connect(self.on_task_error)
        self.thread.start()

    def on_matrix_finished(self, matrix_path):
        self.log_area.append(f"Matriz guardada en {matrix_path}")
        self.show_matrix_button.setDisabled(False)
        pixmap = QPixmap(matrix_path)
        # Escalar la imagen para que se ajuste al label manteniendo proporción
        scaled_pixmap = pixmap.scaled(self.matrix_plot_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.matrix_plot_label.setPixmap(scaled_pixmap)
        self.matrix_plot_label.setToolTip(f"Matriz guardada en: {matrix_path}")

    def on_task_error(self, error_message):
        QMessageBox.critical(self, "Error en Tarea", f"Ocurrió un error: {error_message}")
        # Habilitar todos los botones en caso de error
        self.train_button.setDisabled(False)
        self.process_keypoints_button.setDisabled(False)
        self.show_matrix_button.setDisabled(False)

    def create_training_icon(self):
        """Crear icono para la ventana de entrenamiento"""
        # Crear un icono simple usando texto/emoji
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TrainingDashboardWindow(None)
    window.show()
    sys.exit(app.exec_()) 