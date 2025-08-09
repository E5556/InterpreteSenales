import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QListWidget, QListWidgetItem, QMessageBox, QHBoxLayout)
from PyQt5.QtCore import Qt
from database import get_user_sessions, delete_session

class SessionsWindow(QWidget):
    def __init__(self, user_id, controller, is_admin_mode=False):
        super().__init__()
        self.user_id = user_id
        self.controller = controller
        self.is_admin_mode = is_admin_mode
        
        self.setWindowTitle("Historial de Sesiones")
        self.setGeometry(300, 300, 500, 400)
        
        # SessionsWindow ES una ventana principal - puede cerrar la aplicación
        
        layout = QVBoxLayout(self)
        
        self.sessions_list = QListWidget(self)
        self.populate_sessions()
        
        # Botones
        button_layout = QHBoxLayout()
        self.new_session_button = QPushButton("Iniciar Nueva Sesión", self)
        self.logout_button = QPushButton("Cerrar Sesión", self)
        self.delete_session_button = QPushButton("Eliminar Sesión Seleccionada", self)

        # Lógica de visibilidad
        if self.is_admin_mode:
            self.new_session_button.hide() # El admin no inicia sesiones para otros
            self.logout_button.hide()
        else:
            self.delete_session_button.hide()

        button_layout.addWidget(self.new_session_button)
        button_layout.addWidget(self.delete_session_button)
        button_layout.addStretch()
        button_layout.addWidget(self.logout_button)
        
        layout.addWidget(self.sessions_list)
        layout.addLayout(button_layout)
        
        # Conexiones
        self.new_session_button.clicked.connect(self.start_new_session)
        self.logout_button.clicked.connect(self.logout)
        self.sessions_list.itemClicked.connect(self.view_session_history)
        self.delete_session_button.clicked.connect(self.handle_delete_session)

    def populate_sessions(self):
        self.sessions_list.clear()
        sessions = get_user_sessions(self.user_id)
        if not sessions:
            self.sessions_list.addItem("No hay sesiones anteriores.")
        else:
            for session in sessions:
                session_id, timestamp = session
                item = QListWidgetItem(f"Sesión iniciada el: {timestamp}")
                item.setData(Qt.UserRole, session_id) # Guardamos el ID en el item
                self.sessions_list.addItem(item)

    def start_new_session(self):
        self.controller.start_new_interpreter_session(self.user_id)
        self.close()
        
    def view_session_history(self, item):
        session_id = item.data(Qt.UserRole)
        if session_id:
            self.controller.show_history_window(session_id)
            self.close()

    def handle_delete_session(self):
        selected_items = self.sessions_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona una sesión para eliminar.")
            return 



        session_id = selected_items[0].data(Qt.UserRole)
        timestamp = selected_items[0].text()

        reply = QMessageBox.question(self, "Confirmar Eliminación", 
                                     f"¿Estás seguro de que quieres eliminar esta sesión?\n({timestamp})\n¡Esta acción es irreversible!",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            delete_session(session_id)
            QMessageBox.information(self, "Éxito", "Sesión eliminada correctamente.")
            self.populate_sessions() # Refrescar la lista
            
    def logout(self):
        self.controller.logout()
        self.close()

# Para probar la ventana de forma independiente
if __name__ == '__main__':
    from PyQt5.QtCore import Qt

    class MockController:
        def start_new_interpreter_session(self, user_id):
            print(f"Controller: Iniciar nueva sesión para el usuario {user_id}")
        def show_history_window(self, session_id):
            print(f"Controller: Mostrar historial para la sesión {session_id}")
        def logout(self):
            print("Controller: Cerrar sesión")

    app = QApplication(sys.argv)
    # Necesitamos un usuario y una sesión de ejemplo para probar
    from database import init_db, add_user, check_user, create_session
    init_db()
    add_user("tester", "test")
    user_id = check_user("tester", "test")
    if user_id:
        create_session(user_id)
    
    sessions_win = SessionsWindow(user_id=user_id, controller=MockController())
    sessions_win.show()
    sys.exit(app.exec_()) 