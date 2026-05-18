import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
from database import update_user_password

class ChangePasswordWindow(QWidget):
    def __init__(self, user_id, controller):
        super().__init__()
        self.user_id = user_id
        self.controller = controller
        
        self.setWindowTitle("🔒 Intérprete LSC - Cambio de Contraseña Obligatorio")
        self.setGeometry(400, 400, 450, 250)
        
        # Configurar icono de la ventana
        self.setWindowIcon(self.create_password_icon())
        
        layout = QVBoxLayout(self)
        
        self.new_password_input = QLineEdit(echoMode=QLineEdit.Password, placeholderText="Nueva Contraseña")
        self.confirm_password_input = QLineEdit(echoMode=QLineEdit.Password, placeholderText="Confirmar Nueva Contraseña")
        self.change_button = QPushButton("🔒 Cambiar Contraseña", self)
        
        title_label = QLabel("<h2>🔒 Cambio de Contraseña Obligatorio</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        subtitle_label = QLabel("🛡️ Por seguridad, es necesario que establezca una nueva contraseña.")
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(self.new_password_input)
        layout.addWidget(self.confirm_password_input)
        layout.addWidget(self.change_button)
        
        self.change_button.clicked.connect(self.handle_change_password)

    def handle_change_password(self):
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not new_password or not confirm_password:
            QMessageBox.warning(self, "Error", "Los campos no pueden estar vacíos.")
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "Error", "Las contraseñas no coinciden.")
            return
            
        # Actualizar en la base de datos
        update_user_password(self.user_id, new_password)
        
        QMessageBox.information(self, "Éxito", "Contraseña actualizada correctamente. Por favor, inicie sesión de nuevo.")
        self.controller.logout() # Forzamos logout para que reingrese con la nueva pass
        self.close()

    def create_password_icon(self):
        """Crear icono para la ventana de cambio de contraseña"""
        # Crear un icono simple usando texto/emoji
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Para probar, necesitaríamos un mock controller y un user_id
    change_win = ChangePasswordWindow(user_id=1, controller=None) # Ejemplo
    change_win.show()
    sys.exit(app.exec_()) 