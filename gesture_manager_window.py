import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QPushButton, QInputDialog, QMessageBox, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QColor
from constants import FRAME_ACTIONS_PATH
from training_utils import get_gestures_with_samples, get_all_gesture_folders


class GestureManagerWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.capture_win = None # Referencia

        self.setWindowTitle("🤲 Intérprete LSC - Gestor de Gestos y Entrenamiento")
        self.setGeometry(200, 200, 700, 600)
        
        # Configurar icono de la ventana
        self.setWindowIcon(self.create_gesture_manager_icon())
        
        # Asegurar que esta ventana no termine la aplicación al cerrarse
        self.setAttribute(Qt.WA_QuitOnClose, False)

        layout = QVBoxLayout(self)
        
        # Título del panel
        title_label = QLabel("<h2>🤲 Gestor de Gestos y Entrenamiento</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Lista de Gestos
        self.gestures_list = QListWidget()

        # Botones de Acción de Gestos
        gesture_buttons_layout = QHBoxLayout()
        self.add_gesture_button = QPushButton("➕ Crear Nuevo Gesto")
        self.add_samples_button = QPushButton("📹 Agregar Muestras")
        self.delete_gesture_button = QPushButton("🗑️ Eliminar Gesto")
        gesture_buttons_layout.addWidget(self.add_gesture_button)
        gesture_buttons_layout.addWidget(self.add_samples_button)
        gesture_buttons_layout.addWidget(self.delete_gesture_button)

        # Botón de Entrenamiento
        self.train_button = QPushButton("🧠 Ir al Panel de Entrenamiento")

        layout.addWidget(self.gestures_list)
        layout.addLayout(gesture_buttons_layout)
        layout.addWidget(self.train_button)

        self.populate_gestures_list()

        # Conexiones
        self.add_gesture_button.clicked.connect(self.handle_add_gesture)
        self.delete_gesture_button.clicked.connect(self.handle_delete_gesture)
        self.add_samples_button.clicked.connect(self.handle_add_samples)
        self.train_button.clicked.connect(self.handle_go_to_training)
        

    def populate_gestures_list(self):
        """Llenar la lista con TODOS los gestos disponibles mostrando su estado de procesamiento"""
        self.gestures_list.clear()
        
        # Obtener todos los gestos (incluso vacíos)
        all_gestures = get_all_gesture_folders()
        # Obtener solo gestos con muestras
        gestures_with_samples = get_gestures_with_samples()
        
        for gesture_name in all_gestures:
            # Verificar estado del gesto
            has_samples = gesture_name in gestures_with_samples
            has_keypoints = self.check_gesture_has_keypoints(gesture_name)
            
            # Crear item con indicador visual según el estado
            if not has_samples:
                # Gesto sin muestras
                display_text = f"📁 {gesture_name} (sin muestras)"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, gesture_name)
                item.setForeground(self.palette().color(self.palette().Mid))
            elif has_samples and not has_keypoints:
                # Gesto con muestras pero sin procesar (NUEVO/PENDIENTE)
                display_text = f"🆕 {gesture_name} (muestras nuevas - sin procesar)"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, gesture_name)
                # Color naranja/amarillo para gestos pendientes de procesar
                item.setBackground(QColor(255, 248, 220))  # Amarillo claro
                item.setForeground(QColor(255, 140, 0))    # Naranja
            elif has_samples and has_keypoints:
                # Gesto completamente procesado
                display_text = f"✅ {gesture_name} (procesado y listo)"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, gesture_name)
                # Color verde para gestos procesados
                item.setBackground(QColor(240, 255, 240))  # Verde claro
                item.setForeground(QColor(0, 128, 0))      # Verde oscuro
            
            self.gestures_list.addItem(item)
    
    def check_gesture_has_keypoints(self, gesture_name):
        """Verificar si un gesto tiene keypoints procesados"""
        from constants import KEYPOINTS_PATH
        keypoints_path = os.path.join(KEYPOINTS_PATH, f"{gesture_name}.h5")
        return os.path.exists(keypoints_path)
    
    def refresh_gestures_list(self):
        """Actualizar la lista de gestos (útil para refrescar después de cambios)"""
        self.populate_gestures_list()

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
        
        # Actualizar la lista cuando se regrese de la ventana de captura
        # Esto se ejecutará cuando la ventana de captura se cierre
        self.refresh_gestures_list()


    def handle_go_to_training(self):
        self.controller.show_training_dashboard()
        self.close()

    def create_gesture_manager_icon(self):
        """Crear icono para la ventana de gestión de gestos"""
        # Crear un icono simple usando texto/emoji
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

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