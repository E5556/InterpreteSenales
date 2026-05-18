import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QMessageBox, QHeaderView, QCheckBox, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
from database import get_all_users, delete_user
from config import get_database_version
from database_v2 import DatabaseManager
from user_form_window import UserFormWindow
from estadisticas_integrada_final import show_integrated_statistics

class AdminPanel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.user_form_win = None
        self.sessions_win = None # Referencia a la ventana de sesiones
        self.gesture_manager_win = None # Referencia
        
        self.setWindowTitle("⚙️ Intérprete LSC - Panel de Administración")
        self.setGeometry(150, 150, 900, 700)
        
        # Configurar icono de la ventana
        self.setWindowIcon(self.create_admin_icon())
        
        # AdminPanel ES una ventana principal - puede cerrar la aplicación
        
        layout = QVBoxLayout(self)
        
        # Título del panel
        title_label = QLabel("<h2>⚙️ Panel de Administración del Sistema</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Tabla de usuarios
        self.users_table = QTableWidget()
        if get_database_version() == "expanded":
            self.users_table.setColumnCount(8)
            self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Nombre", "Apellido", "Email", "Rol", "Activo", "Email Verificado"])
        else:
            self.users_table.setColumnCount(6)
            self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Nombre", "Apellido", "Email", "Rol"])
        
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        self.add_user_button = QPushButton("👤 Agregar Usuario")
        self.edit_user_button = QPushButton("✏️ Editar Usuario")
        self.delete_user_button = QPushButton("🗑️ Eliminar Usuario")
        self.view_sessions_button = QPushButton("📋 Ver Sesiones")
        self.manage_gestures_button = QPushButton("🤲 Gestionar Gestos")
        self.statistics_button = QPushButton("📊 Estadísticas del Sistema")
        
        # Botones específicos para activación (solo BD expandida)
        if get_database_version() == "expanded":
            self.activate_user_button = QPushButton("✅ Activar Usuario")
            self.deactivate_user_button = QPushButton("❌ Desactivar Usuario")
            self.verify_email_button = QPushButton("📧 Verificar Email")
        
        self.logout_button = QPushButton("🚪 Cerrar Sesión")
        
        buttons_layout.addWidget(self.add_user_button)
        buttons_layout.addWidget(self.edit_user_button)
        buttons_layout.addWidget(self.delete_user_button)
        buttons_layout.addWidget(self.view_sessions_button)
        buttons_layout.addWidget(self.manage_gestures_button)
        buttons_layout.addWidget(self.statistics_button)
        
        # Agregar botones de activación si es BD expandida
        if get_database_version() == "expanded":
            buttons_layout.addWidget(self.activate_user_button)
            buttons_layout.addWidget(self.deactivate_user_button)
            buttons_layout.addWidget(self.verify_email_button)
        
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
        self.manage_gestures_button.clicked.connect(self.handle_manage_gestures)
        self.statistics_button.clicked.connect(self.handle_show_statistics)
        
        # Conexiones para botones de activación (solo BD expandida)
        if get_database_version() == "expanded":
            self.activate_user_button.clicked.connect(self.handle_activate_user)
            self.deactivate_user_button.clicked.connect(self.handle_deactivate_user)
            self.verify_email_button.clicked.connect(self.handle_verify_email)

    def populate_users_table(self):
        self.users_table.setRowCount(0)
        
        if get_database_version() == "expanded":
            # Usar base de datos expandida
            db_manager = DatabaseManager()
            users = db_manager.execute_query("""
                SELECT id, username, first_name, last_name, email, role, is_active, email_verified
                FROM users ORDER BY username
            """)
            
            for row_num, user_data in enumerate(users):
                self.users_table.insertRow(row_num)
                
                # Datos básicos
                for col_num in range(6):  # ID, Username, Nombre, Apellido, Email, Rol
                    item = QTableWidgetItem(str(user_data[col_num] or ""))
                    if col_num == 0:  # ID
                        item.setData(Qt.UserRole, user_data[0])
                    self.users_table.setItem(row_num, col_num, item)
                
                # Estado de activación
                is_active_item = QTableWidgetItem("Sí" if user_data[6] else "No")
                is_active_item.setTextAlignment(Qt.AlignCenter)
                self.users_table.setItem(row_num, 6, is_active_item)
                
                # Estado de verificación de email
                email_verified_item = QTableWidgetItem("Sí" if user_data[7] else "No")
                email_verified_item.setTextAlignment(Qt.AlignCenter)
                self.users_table.setItem(row_num, 7, email_verified_item)
        else:
            # Usar base de datos original
            users = get_all_users()
            for row_num, user_data in enumerate(users):
                self.users_table.insertRow(row_num)
                for col_num, data in enumerate(user_data):
                    item = QTableWidgetItem(str(data))
                    if col_num == 0:
                        item.setData(Qt.UserRole, user_data[0])
                    self.users_table.setItem(row_num, col_num, item)

    def handle_add_user(self):
        self.user_form_win = UserFormWindow(admin_panel=self, current_user_role='admin')
        self.user_form_win.show()

    def handle_edit_user(self):
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un usuario para editar.")
            return

        selected_row = selected_rows[0].row()
        user_id = self.users_table.item(selected_row, 0).data(Qt.UserRole)
        
        self.user_form_win = UserFormWindow(user_id=user_id, admin_panel=self, current_user_role='admin')
        self.user_form_win.show()

    def handle_manage_gestures(self):
        self.controller.show_gesture_manager()
    
    def handle_show_statistics(self):
        """Muestra la ventana de estadísticas del sistema"""
        try:
            show_integrated_statistics()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir las estadísticas: {str(e)}")

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

    def handle_activate_user(self):
        """Activar usuario seleccionado"""
        if get_database_version() != "expanded":
            return
            
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un usuario para activar.")
            return

        selected_row = selected_rows[0].row()
        user_id = self.users_table.item(selected_row, 0).data(Qt.UserRole)
        username = self.users_table.item(selected_row, 1).text()
        
        db_manager = DatabaseManager()
        db_manager.execute_query("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
        
        QMessageBox.information(self, "Éxito", f"Usuario '{username}' activado correctamente.")
        self.populate_users_table()

    def handle_deactivate_user(self):
        """Desactivar usuario seleccionado"""
        if get_database_version() != "expanded":
            return
            
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un usuario para desactivar.")
            return

        selected_row = selected_rows[0].row()
        user_id = self.users_table.item(selected_row, 0).data(Qt.UserRole)
        username = self.users_table.item(selected_row, 1).text()
        
        if username == 'admin':
            QMessageBox.critical(self, "Error", "No se puede desactivar al usuario administrador.")
            return
        
        db_manager = DatabaseManager()
        db_manager.execute_query("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        
        QMessageBox.information(self, "Éxito", f"Usuario '{username}' desactivado correctamente.")
        self.populate_users_table()

    def handle_verify_email(self):
        """Verificar email del usuario seleccionado"""
        if get_database_version() != "expanded":
            return
            
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selección Requerida", "Por favor, selecciona un usuario para verificar su email.")
            return

        selected_row = selected_rows[0].row()
        user_id = self.users_table.item(selected_row, 0).data(Qt.UserRole)
        username = self.users_table.item(selected_row, 1).text()
        
        db_manager = DatabaseManager()
        db_manager.execute_query("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
        
        QMessageBox.information(self, "Éxito", f"Email del usuario '{username}' verificado correctamente.")
        self.populate_users_table()

    def logout(self):
        self.controller.logout()
        self.close()

    def create_admin_icon(self):
        """Crear icono para la ventana de administración"""
        # Crear un icono simple usando texto/emoji
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

if __name__ == '__main__':
    class MockController:
        def logout(self):
            print("Controller: Cerrar sesión")

    app = QApplication(sys.argv)
    admin_panel = AdminPanel(MockController())
    admin_panel.show()
    sys.exit(app.exec_()) 