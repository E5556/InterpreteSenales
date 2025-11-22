import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QPushButton, QInputDialog, QMessageBox, QProgressDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from constants import FRAME_ACTIONS_PATH
from training_utils import get_gestures_with_samples, get_all_gesture_folders

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

class GestureManagerWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.capture_win = None # Referencia

        self.setWindowTitle("Gestor de Gestos y Entrenamiento")
        self.setGeometry(200, 200, 600, 500)
        
        # Asegurar que esta ventana no termine la aplicación al cerrarse
        self.setAttribute(Qt.WA_QuitOnClose, False)

        layout = QVBoxLayout(self)

        # Lista de Gestos
        self.gestures_list = QListWidget()

        # Botones de Acción de Gestos
        gesture_buttons_layout = QHBoxLayout()
        self.add_gesture_button = QPushButton("Crear Nuevo Gesto")
        self.add_samples_button = QPushButton("Agregar Muestras")
        self.delete_gesture_button = QPushButton("Eliminar Gesto")
        self.process_gesture_button = QPushButton("Procesar Gesto Seleccionado")
        gesture_buttons_layout.addWidget(self.add_gesture_button)
        gesture_buttons_layout.addWidget(self.add_samples_button)
        gesture_buttons_layout.addWidget(self.delete_gesture_button)
        gesture_buttons_layout.addWidget(self.process_gesture_button)

        # Botón de Entrenamiento
        self.train_button = QPushButton("Ir al Panel de Entrenamiento")

        layout.addWidget(self.gestures_list)
        layout.addLayout(gesture_buttons_layout)
        layout.addWidget(self.train_button)

        self.populate_gestures_list()

        # Conexiones
        self.add_gesture_button.clicked.connect(self.handle_add_gesture)
        self.delete_gesture_button.clicked.connect(self.handle_delete_gesture)
        self.add_samples_button.clicked.connect(self.handle_add_samples)
        self.process_gesture_button.clicked.connect(self.handle_process_gesture)
        self.train_button.clicked.connect(self.handle_go_to_training)
        
        # Variables para procesamiento
        self.processing_thread = None

    def populate_gestures_list(self):
        """Llenar la lista con TODOS los gestos disponibles (con y sin muestras)"""
        self.gestures_list.clear()
        
        # Obtener todos los gestos (incluso vacíos)
        all_gestures = get_all_gesture_folders()
        # Obtener solo gestos con muestras
        gestures_with_samples = get_gestures_with_samples()
        
        for gesture_name in all_gestures:
            # Crear item con indicador visual
            if gesture_name in gestures_with_samples:
                display_text = f"✅ {gesture_name} (con muestras)"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, gesture_name)  # Guardar nombre real
                # Color verde para gestos con muestras
                item.setBackground(self.palette().color(self.palette().AlternateBase))
            else:
                display_text = f"📁 {gesture_name} (sin muestras)"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, gesture_name)  # Guardar nombre real
                # Color gris para gestos sin muestras
                item.setForeground(self.palette().color(self.palette().Mid))
            
            self.gestures_list.addItem(item)

    def handle_add_gesture(self):
        """Maneja la creación de un nuevo gesto"""
        gesture_name, ok = QInputDialog.getText(self, 'Crear Gesto', 'Nombre del nuevo gesto (use _ para espacios):')
        
        if ok and gesture_name.strip():
            gesture_name = gesture_name.strip().lower().replace(' ', '_')
            gesture_path = os.path.join(FRAME_ACTIONS_PATH, gesture_name)
            
            if os.path.exists(gesture_path):
                QMessageBox.warning(self, "Error", f"El gesto '{gesture_name}' ya existe.")
                return
            
            try:
                # Crear carpeta simple
                os.makedirs(gesture_path)
                
                # Refrescar la lista (se actualizará automáticamente cuando haya muestras)
                self.populate_gestures_list()
                
                QMessageBox.information(self, "Éxito", 
                    f"Gesto '{gesture_name}' creado exitosamente.\n"
                    f"Carpeta: {gesture_path}\n"
                    f"Ahora puedes agregar muestras para este gesto.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al crear el gesto: {str(e)}")

    def handle_delete_gesture(self):
        """Maneja la eliminación de un gesto seleccionado"""
        current_item = self.gestures_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un gesto para eliminar.")
            return
        
        gesture_name = current_item.data(Qt.UserRole)  # Obtener nombre real
        
        reply = QMessageBox.question(self, 'Confirmar Eliminación', 
                                   f"¿Estás seguro de que quieres eliminar el gesto '{gesture_name}'?\n"
                                   f"Se eliminarán:\n"
                                   f"- La carpeta con todas las muestras\n"
                                   f"- Los archivos de keypoints\n\n"
                                   f"Esta acción no se puede deshacer.",
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # Eliminar carpeta de muestras
                gesture_path = os.path.join(FRAME_ACTIONS_PATH, gesture_name)
                if os.path.exists(gesture_path):
                    import shutil
                    shutil.rmtree(gesture_path)
                
                # Eliminar archivo de keypoints si existe
                keypoints_path = os.path.join("data", "keypoints", f"{gesture_name}.h5")
                if os.path.exists(keypoints_path):
                    os.remove(keypoints_path)
                
                # Refrescar la lista
                self.populate_gestures_list()
                
                QMessageBox.information(self, "Éxito", 
                    f"Gesto '{gesture_name}' eliminado completamente.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al eliminar el gesto: {str(e)}")

    def handle_add_samples(self):
        selected_items = self.gestures_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un gesto para agregarle muestras.")
            return

        gesture_name = selected_items[0].data(Qt.UserRole)  # Obtener nombre real
        self.controller.show_capture_window(gesture_name)

    def handle_process_gesture(self):
        """Procesar gesto seleccionado (normalizar + keypoints)"""
        selected_items = self.gestures_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un gesto para procesar.")
            return
        
        gesture_name = selected_items[0].data(Qt.UserRole)  # Obtener nombre real
        
        # Verificar que el gesto tenga muestras antes de procesar
        gestures_with_samples = get_gestures_with_samples()
        if gesture_name not in gestures_with_samples:
            QMessageBox.warning(self, "Sin Muestras", 
                              f"El gesto '{gesture_name}' no tiene muestras para procesar.\n\n"
                              f"Primero agrega muestras usando el botón 'Agregar Muestras'.")
            return
        
        # Confirmar procesamiento
        reply = QMessageBox.question(self, 'Confirmar Procesamiento', 
                                   f"¿Procesar el gesto '{gesture_name}'?\n\n"
                                   f"Esto realizará:\n"
                                   f"• Normalización de muestras (15 frames)\n"
                                   f"• Creación de keypoints\n\n"
                                   f"Esto puede tomar unos minutos...",
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.Yes)
        
        if reply == QMessageBox.Yes:
            self.start_processing(gesture_name)
    
    def start_processing(self, gesture_name):
        """Iniciar procesamiento en hilo separado"""
        if self.processing_thread and self.processing_thread.isRunning():
            QMessageBox.warning(self, "Procesamiento en Curso", 
                              "Ya hay un procesamiento en curso. Espere a que termine.")
            return
        
        # Crear diálogo de progreso
        self.progress_dialog = QProgressDialog(f"Procesando '{gesture_name}'...", "Cancelar", 0, 100, self)
        self.progress_dialog.setWindowTitle("Procesamiento de Gesto")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.canceled.connect(self.cancel_processing)
        self.progress_dialog.show()
        
        # Deshabilitar botones durante procesamiento
        self.process_gesture_button.setEnabled(False)
        self.add_gesture_button.setEnabled(False)
        self.delete_gesture_button.setEnabled(False)
        
        # Iniciar hilo de procesamiento
        self.processing_thread = ProcessingThread(gesture_name)
        self.processing_thread.progress_updated.connect(self.on_processing_progress)
        self.processing_thread.finished_successfully.connect(self.on_processing_finished)
        self.processing_thread.start()
    
    def on_processing_progress(self, progress, message):
        """Actualizar progreso"""
        progress_percent = int(progress * 100)
        self.progress_dialog.setValue(progress_percent)
        self.progress_dialog.setLabelText(f"[{progress_percent}%] {message}")
    
    def on_processing_finished(self, success):
        """Procesamiento terminado"""
        # Habilitar botones
        self.process_gesture_button.setEnabled(True)
        self.add_gesture_button.setEnabled(True)
        self.delete_gesture_button.setEnabled(True)
        
        # Cerrar diálogo de progreso
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        
        if success:
            QMessageBox.information(self, "Éxito", 
                                  "¡Gesto procesado exitosamente!\n\n"
                                  "• Muestras normalizadas a 15 frames\n"
                                  "• Keypoints generados\n"
                                  "• Listo para entrenamiento")
        else:
            QMessageBox.warning(self, "Error", 
                              "Hubo un error procesando el gesto.\n\n"
                              "Verifica que el gesto tenga muestras válidas.")
    
    def cancel_processing(self):
        """Cancelar procesamiento"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.terminate()
            self.processing_thread.wait()
        
        # Habilitar botones
        self.process_gesture_button.setEnabled(True)
        self.add_gesture_button.setEnabled(True)
        self.delete_gesture_button.setEnabled(True)

    def handle_go_to_training(self):
        self.controller.show_training_dashboard()
        self.close()

if __name__ == '__main__':
    class MockController:
        def show_capture_window(self, gesture_name):
            print(f"Controller: Abrir ventana de captura para '{gesture_name}'")
        def show_training_dashboard(self):
            print("Controller: Abrir panel de entrenamiento")

    app = QApplication(sys.argv)
    window = GestureManagerWindow(MockController())
    window.show()
    sys.exit(app.exec_()) 