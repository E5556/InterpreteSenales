import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox)
from database import add_user, check_user

class LoginWindow(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
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
        self.register_button.clicked.connect(self.handle_register)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Por favor, ingresa usuario y contraseña.")
            return

        user_id = check_user(username, password)
        if user_id:
            QMessageBox.information(self, "Éxito", f"¡Bienvenido, {username}!")
            if self.controller:
                self.controller.show_sessions_window(user_id) # Llama a la nueva función
            self.close()
        else:
            QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos.")
            
    def handle_register(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Por favor, ingresa usuario y contraseña para registrarte.")
            return

        if add_user(username, password):
            QMessageBox.information(self, "Éxito", "Usuario registrado correctamente. Ahora puedes iniciar sesión.")
        else:
            QMessageBox.warning(self, "Error", "El nombre de usuario ya existe.")

# Esto es para probar la ventana de forma independiente
if __name__ == '__main__':
    app = QApplication(sys.argv)
    login_win = LoginWindow()
    login_win.show()
    sys.exit(app.exec_()) 