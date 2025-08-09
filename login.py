import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox)
from database import check_user
from user_form_window import UserFormWindow # Cambiado de register_window

class LoginWindow(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.user_form_win = None # Cambiado de register_win
        self.setWindowTitle("Inicio de Sesión")
        self.setGeometry(400, 400, 400, 200)
        
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
        layout.addWidget(QLabel("<h2>Acceso de Usuario</h2>"))
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

        login_result = check_user(username, password)
        if login_result:
            user_id, role, must_change_password = login_result
            QMessageBox.information(self, "Éxito", f"¡Bienvenido, {username}!")
            if self.controller:
                # Ocultar login antes de abrir nueva ventana principal
                self.hide()
                self.controller.handle_successful_login(user_id, role, must_change_password)
                # Cerrar login después de que la nueva ventana esté establecida
                self.close()
        else:
            QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos.")
            
    def handle_register_show(self):
        self.user_form_win = UserFormWindow() # Cambiado de RegisterWindow
        self.user_form_win.show()

# Esto es para probar la ventana de forma independiente
if __name__ == '__main__':
    app = QApplication(sys.argv)
    login_win = LoginWindow()
    login_win.show()
    sys.exit(app.exec_()) 