import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
from database import check_user
from config import get_database_version
from database_v2 import DatabaseManager
from user_form_window import UserFormWindow

class LoginWindow(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.user_form_win = None # Cambiado de register_win
        self.setWindowTitle("🔐 Intérprete LSC - Inicio de Sesión")
        self.setGeometry(400, 400, 450, 250)
        
        # Configurar icono de la ventana
        self.setWindowIcon(self.create_login_icon())
        
        # Layout principal
        layout = QVBoxLayout(self)
        
        # Campo de Usuario
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Nombre de Usuario")
        
        # Campo de Contraseña
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # Botones
        buttons_layout = QHBoxLayout()
        self.login_button = QPushButton("Iniciar Sesión", self)
        self.register_button = QPushButton("Registrarse", self)
        
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.register_button)
        
        # Añadir widgets al layout
        title_label = QLabel("<h2>🔐 Acceso al Sistema</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addLayout(buttons_layout)
        
        # Conectar señales
        self.login_button.clicked.connect(self.handle_login)
        self.register_button.clicked.connect(self.handle_register_show)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Por favor, ingresa usuario y contraseña.")
            return

        # Verificar si estamos usando la base de datos expandida
        if get_database_version() == "expanded":
            try:
                db_manager = DatabaseManager()
                login_result = db_manager.check_user_login(username, password)
                print(f"[LOGIN DEBUG] user={repr(username)} resultado={login_result}")
            except Exception as e:
                print(f"[LOGIN ERROR] {e}")
                import traceback; traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Error en base de datos:\n{e}")
                return

            if login_result:
                # Verificar si el usuario está autorizado
                if login_result.get('authorized', True) == False:
                    QMessageBox.warning(self, "Acceso Denegado", 
                                      "El administrador aún debe autorizar tu ingreso al sistema.\n"
                                      "Por favor, contacta al administrador para activar tu cuenta.")
                    return
                
                QMessageBox.information(self, "Éxito", f"¡Bienvenido, {username}!")
                if self.controller:
                    self.hide()
                    self.controller.handle_successful_login(
                        login_result['user_id'], 
                        login_result['role'], 
                        login_result['must_change_password']
                    )
                    self.close()
            else:
                QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos.")
        else:
            # Usar función original para base de datos básica
            login_result = check_user(username, password)
            if login_result:
                user_id, role, must_change_password = login_result
                QMessageBox.information(self, "Éxito", f"¡Bienvenido, {username}!")
                if self.controller:
                    self.hide()
                    self.controller.handle_successful_login(user_id, role, must_change_password)
                    self.close()
            else:
                QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos.")
            
    def handle_register_show(self):
        # Pasar None como current_user_role porque es registro público
        self.user_form_win = UserFormWindow(current_user_role=None)
        self.user_form_win.show()

    def create_login_icon(self):
        """Crear icono para la ventana de login"""
        # Crear un icono simple usando texto/emoji
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

# Esto es para probar la ventana de forma independiente
if __name__ == '__main__':
    app = QApplication(sys.argv)
    login_win = LoginWindow()
    login_win.show()
    sys.exit(app.exec_()) 