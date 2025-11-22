import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QDateEdit)
from PyQt5.QtCore import QDate
from api_client import get_countries
from database import add_user, update_user_details, get_user_details_by_id

class UserFormWindow(QWidget):
    def __init__(self, user_id=None, admin_panel=None):
        super().__init__()
        self.user_id = user_id
        self.admin_panel = admin_panel # Para poder refrescar la tabla
        self.is_edit_mode = self.user_id is not None
        
        # --- Configuración de la ventana ---
        title = "Editar Usuario" if self.is_edit_mode else "Registro de Nuevo Usuario"
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout(self)
        grid_layout = QGridLayout()

        # Campos del formulario
        self.username_input = QLineEdit(placeholderText="Nombre de Usuario")
        self.email_input = QLineEdit(placeholderText="Correo Electrónico")
        self.password_input = QLineEdit(echoMode=QLineEdit.Password, placeholderText="Contraseña")
        self.confirm_password_input = QLineEdit(echoMode=QLineEdit.Password, placeholderText="Confirmar Contraseña")
        self.first_name_input = QLineEdit(placeholderText="Nombres")
        self.last_name_input = QLineEdit(placeholderText="Apellidos")
        self.birth_date_input = QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd")
        self.birth_date_input.setDate(QDate.currentDate().addYears(-18))
        self.birth_city_input = QLineEdit(placeholderText="Ciudad de Nacimiento")
        self.residence_city_input = QLineEdit(placeholderText="Ciudad de Residencia")

        # Selectores de países
        self.birth_country_input = QComboBox()
        self.residence_country_input = QComboBox()
        
        # Añadir widgets al grid
        grid_layout.addWidget(QLabel("Usuario:"), 0, 0)
        grid_layout.addWidget(self.username_input, 0, 1)
        grid_layout.addWidget(QLabel("Email:"), 0, 2)
        grid_layout.addWidget(self.email_input, 0, 3)
        grid_layout.addWidget(QLabel("Contraseña:"), 1, 0)
        grid_layout.addWidget(self.password_input, 1, 1)
        grid_layout.addWidget(QLabel("Confirmar Contraseña:"), 1, 2)
        grid_layout.addWidget(self.confirm_password_input, 1, 3)
        grid_layout.addWidget(QLabel("Nombres:"), 2, 0)
        grid_layout.addWidget(self.first_name_input, 2, 1)
        grid_layout.addWidget(QLabel("Apellidos:"), 2, 2)
        grid_layout.addWidget(self.last_name_input, 2, 3)
        grid_layout.addWidget(QLabel("Fecha de Nacimiento:"), 3, 0)
        grid_layout.addWidget(self.birth_date_input, 3, 1)
        grid_layout.addWidget(QLabel("País de Nacimiento:"), 4, 0)
        grid_layout.addWidget(self.birth_country_input, 4, 1)
        grid_layout.addWidget(QLabel("Ciudad de Nacimiento:"), 4, 2)
        grid_layout.addWidget(self.birth_city_input, 4, 3)
        grid_layout.addWidget(QLabel("País de Residencia:"), 5, 0)
        grid_layout.addWidget(self.residence_country_input, 5, 1)
        grid_layout.addWidget(QLabel("Ciudad de Residencia:"), 5, 2)
        grid_layout.addWidget(self.residence_city_input, 5, 3)
        grid_layout.addWidget(QLabel("Rol:"), 6, 0)
        grid_layout.addWidget(self.role_input, 6, 1)

        # Si estamos en modo edición, deshabilitamos la edición de contraseña
        if self.is_edit_mode:
            self.password_input.setDisabled(True)
            self.confirm_password_input.setDisabled(True)
            self.password_input.setPlaceholderText("(No se puede cambiar aquí)")
            self.confirm_password_input.setPlaceholderText("(No se puede cambiar aquí)")
        
        button_text = "Guardar Cambios" if self.is_edit_mode else "Registrar Usuario"
        self.save_button = QPushButton(button_text)
        
        layout.addLayout(grid_layout)
        layout.addWidget(self.save_button)
        
        self.save_button.clicked.connect(self.handle_save)
        
        self.load_countries()
        
        if self.is_edit_mode:
            self.load_user_data()

    def load_countries(self):
        countries = get_countries()
        self.birth_country_input.addItems(["Seleccionar país..."] + countries)
        self.residence_country_input.addItems(["Seleccionar país..."] + countries)

    def load_user_data(self):
        user_data = get_user_details_by_id(self.user_id)
        if user_data:
            # Rellenar el formulario con los datos del usuario
            self.username_input.setText(user_data['username'])
            self.email_input.setText(user_data['email'])
            self.first_name_input.setText(user_data['first_name'])
            self.last_name_input.setText(user_data['last_name'])
            self.birth_date_input.setDate(QDate.fromString(user_data['birth_date'], "yyyy-MM-dd"))
            self.birth_city_input.setText(user_data['birth_city'])
            self.birth_country_input.setCurrentText(user_data['birth_country'])
            self.residence_city_input.setText(user_data['residence_city'])
            self.residence_country_input.setCurrentText(user_data['residence_country'])
            self.role_input.setCurrentText(user_data['role'])

    def handle_save(self):
        # Recolectar todos los datos del formulario
        username = self.username_input.text()
        email = self.email_input.text()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        first_name = self.first_name_input.text()
        last_name = self.last_name_input.text()
        birth_date = self.birth_date_input.date().toString("yyyy-MM-dd")
        birth_country = self.birth_country_input.currentText()
        birth_city = self.birth_city_input.text()
        residence_country = self.residence_country_input.currentText()
        residence_city = self.residence_city_input.text()
        role = self.role_input.currentText()

        # --- Validaciones ---
        if not all([username, email, first_name, last_name, birth_city, residence_city]):
            QMessageBox.warning(self, "Campos Incompletos", "Por favor, rellena todos los campos.")
            return
        
        if self.birth_country_input.currentIndex() == 0 or self.residence_country_input.currentIndex() == 0:
            QMessageBox.warning(self, "Selección Incompleta", "Por favor, selecciona los países.")
            return

        if not self.is_edit_mode and password != confirm_password:
            QMessageBox.warning(self, "Error de Contraseña", "Las contraseñas no coinciden.")
            return

        # --- Intentar registrar al usuario ---
        if self.is_edit_mode:
            # Lógica de Actualización
            success = update_user_details(
                self.user_id, username, password, first_name, last_name, email,
                birth_date, birth_country, birth_city, residence_country, residence_city, role
            )
            if success:
                QMessageBox.information(self, "Éxito", "Usuario actualizado correctamente.")
                if self.admin_panel:
                    self.admin_panel.populate_users_table() # Refrescar
                self.close()
            else:
                QMessageBox.critical(self, "Error", "El nombre de usuario o email ya existe.")
        else:
            # Lógica de Creación (la que ya teníamos)
            success = add_user(
                username, password, first_name, last_name, email,
                birth_date, birth_country, birth_city, residence_country, residence_city, role
            )

            if success:
                QMessageBox.information(self, "Registro Exitoso", "¡Usuario registrado correctamente! Ya puedes cerrar esta ventana e iniciar sesión.")
                self.close()
            else:
                QMessageBox.critical(self, "Error de Registro", "El nombre de usuario o el correo electrónico ya están en uso.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # register_win = RegisterWindow() # This line is no longer needed
    # register_win.show()
    # sys.exit(app.exec_()) 