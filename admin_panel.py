import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt
from database import get_all_users, delete_user
from user_form_window import UserFormWindow

class AdminPanel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.user_form_win = None
        self.sessions_win = None # Referencia a la ventana de sesiones
        self.gesture_manager_win = None # Referencia
        
        self.setWindowTitle("Panel de Administración")
        self.setGeometry(150, 150, 800, 600)
        
        # AdminPanel ES una ventana principal - puede cerrar la aplicación
        
        layout = QVBoxLayout(self)
        
        # Tabla de usuarios
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Nombre", "Apellido", "Email", "Rol"])
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        self.add_user_button = QPushButton("Agregar Usuario")
        self.edit_user_button = QPushButton("Editar Usuario")
        self.delete_user_button = QPushButton("Eliminar Usuario")
        self.view_sessions_button = QPushButton("Ver Sesiones")
        self.manage_gestures_button = QPushButton("Gestionar Gestos") # Nuevo botón
        self.logout_button = QPushButton("Cerrar Sesión")
        
        buttons_layout.addWidget(self.add_user_button)
        buttons_layout.addWidget(self.edit_user_button)
        buttons_layout.addWidget(self.delete_user_button)
        buttons_layout.addWidget(self.view_sessions_button)
        buttons_layout.addWidget(self.manage_gestures_button) # Añadido
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.logout_button)
        
        layout.addWidget(self.users_table)
        layout.addLayout(buttons_layout)
        
        self.populate_users_table()
        
        # Conexiones
        self.logout_button.clicked.connect(self.logout)
        self.delete_user_button.clicked.connect(self.handle_delete_user)
        self.add_user_button.clicked.connect(self.handle_add_user)
        self.edit_user_button.clicked.connect(self.handle_edit_user)
        self.view_sessions_button.clicked.connect(self.handle_view_sessions)
        self.manage_gestures_button.clicked.connect(self.handle_manage_gestures) # Nueva conexión

    def populate_users_table(self):
        self.users_table.setRowCount(0)
        users = get_all_users()
        for row_num, user_data in enumerate(users):
            self.users_table.insertRow(row_num)
            for col_num, data in enumerate(user_data):
                item = QTableWidgetItem(str(data))
                # Guardamos el ID del usuario en la primera columna
                if col_num == 0:
                    item.setData(Qt.UserRole, user_data[0])
                self.users_table.setItem(row_num, col_num, item)

    def handle_add_user(self):
        self.user_form_win = UserFormWindow(admin_panel=self)
        self.user_form_win.show()

    def handle_edit_user(self):
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un usuario para editar.")
            return

        selected_row = selected_rows[0].row()
        user_id = self.users_table.item(selected_row, 0).data(Qt.UserRole)
        
        self.user_form_win = UserFormWindow(user_id=user_id, admin_panel=self)
        self.user_form_win.show()

    def handle_manage_gestures(self):
        self.controller.show_gesture_manager()

    def handle_view_sessions(self):
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un usuario para ver sus sesiones.")
            return

        selected_row = selected_rows[0].row()
        user_id = self.users_table.item(selected_row, 0).data(Qt.UserRole)
        username = self.users_table.item(selected_row, 1).text()
        
        self.controller.show_user_sessions_for_admin(user_id, username)

    def handle_delete_user(self):
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un usuario para eliminar.")
            return

        selected_row = selected_rows[0].row()
        user_id = self.users_table.item(selected_row, 0).data(Qt.UserRole)
        username = self.users_table.item(selected_row, 1).text()
        
        if username == 'admin':
            QMessageBox.critical(self, "Error", "No se puede eliminar al usuario administrador.")
            return

        reply = QMessageBox.question(self, "Confirmar Eliminación", 
                                     f"¿Estás seguro de que quieres eliminar al usuario '{username}'?\n¡Esta acción es irreversible y borrará todas sus sesiones!",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            delete_user(user_id)
            QMessageBox.information(self, "Éxito", f"Usuario '{username}' eliminado correctamente.")
            self.populate_users_table() # Refrescar la tabla

    def logout(self):
        self.controller.logout()
        self.close()

if __name__ == '__main__':
    class MockController:
        def logout(self):
            print("Controller: Cerrar sesión")

    app = QApplication(sys.argv)
    admin_panel = AdminPanel(MockController())
    admin_panel.show()
    sys.exit(app.exec_()) 