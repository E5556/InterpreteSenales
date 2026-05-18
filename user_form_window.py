import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QDateEdit,
                             QTextEdit, QCheckBox, QSpinBox, QFileDialog, QScrollArea, QGroupBox, QFrame)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QPixmap
from api_client import get_countries
from database import add_user, update_user_details, get_user_details_by_id
from config import get_database_version
from database_v2 import DatabaseManager


def get_countries_safe():
    """Función auxiliar para obtener lista de países de forma segura"""
    try:
        return get_countries()
    except Exception as e:
        print(f"Error al obtener países de API: {e}")
        # Lista de países por defecto si falla la función original
        return [
            "Afghanistan", "Albania", "Algeria", "Argentina", "Armenia", "Australia",
            "Austria", "Azerbaijan", "Bahrain", "Bangladesh", "Belarus", "Belgium",
            "Bolivia", "Brazil", "Bulgaria", "Canada", "Chile", "China", "Colombia",
            "Costa Rica", "Croatia", "Cuba", "Czech Republic", "Denmark", "Ecuador",
            "Egypt", "El Salvador", "Estonia", "Finland", "France", "Germany",
            "Greece", "Guatemala", "Honduras", "Hungary", "Iceland", "India",
            "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Japan",
            "Jordan", "Kazakhstan", "Kenya", "Kuwait", "Latvia", "Lebanon",
            "Lithuania", "Luxembourg", "Malaysia", "Mexico", "Morocco", "Netherlands",
            "New Zealand", "Nicaragua", "Norway", "Pakistan", "Panama", "Paraguay",
            "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania",
            "Russia", "Saudi Arabia", "South Africa", "South Korea", "Spain",
            "Sri Lanka", "Sweden", "Switzerland", "Thailand", "Turkey", "Ukraine",
            "United Arab Emirates", "United Kingdom", "United States", "Uruguay",
            "Venezuela", "Vietnam"
        ]


class UserFormWindow(QWidget):
    def __init__(self, user_id=None, admin_panel=None, current_user_role=None):
        super().__init__()
        self.user_id = user_id
        self.admin_panel = admin_panel
        self.current_user_role = current_user_role  # Rol del usuario actual que está creando/editando
        self.is_edit_mode = self.user_id is not None
        self.db_manager = DatabaseManager() if get_database_version() == "expanded" else None
        self.profile_picture_url = ""
        
        # Configuración de la ventana
        self.setWindowTitle("Editar Usuario" if self.is_edit_mode else "Registrar Usuario")
        self.setGeometry(100, 100, 800, 600)
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializar la interfaz de usuario"""
        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Scroll area para manejar muchos campos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll.setWidget(scroll_widget)
        
        # Layout del contenido con scroll
        layout = QVBoxLayout(scroll_widget)
        
        # === TÍTULO ===
        title = QLabel("Editar Usuario" if self.is_edit_mode else "Nuevo Usuario")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # === INFORMACIÓN BÁSICA ===
        basic_group = QGroupBox("📋 Información Básica")
        basic_layout = QGridLayout(basic_group)
        
        # Campos básicos
        self.username_input = QLineEdit(placeholderText="Nombre de usuario")
        self.email_input = QLineEdit(placeholderText="Correo electrónico")
        self.password_input = QLineEdit(placeholderText="Contraseña")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input = QLineEdit(placeholderText="Confirmar contraseña")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.first_name_input = QLineEdit(placeholderText="Nombres")
        self.last_name_input = QLineEdit(placeholderText="Apellidos")
        
        # Agregar campos básicos al layout
        basic_layout.addWidget(QLabel("Usuario:"), 0, 0)
        basic_layout.addWidget(self.username_input, 0, 1)
        basic_layout.addWidget(QLabel("Email:"), 0, 2)
        basic_layout.addWidget(self.email_input, 0, 3)
        basic_layout.addWidget(QLabel("Nombres:"), 1, 0)
        basic_layout.addWidget(self.first_name_input, 1, 1)
        basic_layout.addWidget(QLabel("Apellidos:"), 1, 2)
        basic_layout.addWidget(self.last_name_input, 1, 3)
        
        # Contraseñas (solo en modo registro)
        if not self.is_edit_mode:
            basic_layout.addWidget(QLabel("Contraseña:"), 2, 0)
            basic_layout.addWidget(self.password_input, 2, 1)
            basic_layout.addWidget(QLabel("Confirmar:"), 2, 2)
            basic_layout.addWidget(self.confirm_password_input, 2, 3)
        
        layout.addWidget(basic_group)
        
        # === INFORMACIÓN PERSONAL ===
        personal_group = QGroupBox("👤 Información Personal")
        personal_layout = QGridLayout(personal_group)
        
        # Teléfono y fecha de nacimiento
        self.phone_input = QLineEdit(placeholderText="Teléfono")
        self.birth_date_input = QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd")
        self.birth_date_input.setDate(QDate.currentDate().addYears(-18))
        
        personal_layout.addWidget(QLabel("Teléfono:"), 0, 0)
        personal_layout.addWidget(self.phone_input, 0, 1)
        personal_layout.addWidget(QLabel("Fecha de Nacimiento:"), 0, 2)
        personal_layout.addWidget(self.birth_date_input, 0, 3)
        
        layout.addWidget(personal_group)
        
        # === INFORMACIÓN GEOGRÁFICA ===
        geo_group = QGroupBox("🌍 Información Geográfica")
        geo_layout = QGridLayout(geo_group)
        
        self.birth_city_input = QLineEdit(placeholderText="Ciudad de Nacimiento")
        self.residence_city_input = QLineEdit(placeholderText="Ciudad de Residencia")
        self.birth_country_input = QComboBox()
        self.residence_country_input = QComboBox()
        
        geo_layout.addWidget(QLabel("País de Nacimiento:"), 0, 0)
        geo_layout.addWidget(self.birth_country_input, 0, 1)
        geo_layout.addWidget(QLabel("Ciudad de Nacimiento:"), 0, 2)
        geo_layout.addWidget(self.birth_city_input, 0, 3)
        geo_layout.addWidget(QLabel("País de Residencia:"), 1, 0)
        geo_layout.addWidget(self.residence_country_input, 1, 1)
        geo_layout.addWidget(QLabel("Ciudad de Residencia:"), 1, 2)
        geo_layout.addWidget(self.residence_city_input, 1, 3)
        
        layout.addWidget(geo_group)
        
        # === CONFIGURACIONES DE PERFIL (BD expandida) ===
        if self.db_manager:
            profile_group = QGroupBox("⚙️ Configuraciones de Perfil")
            profile_layout = QGridLayout(profile_group)
            
            # Estado auditivo
            self.hearing_status_input = QComboBox()
            self.hearing_status_input.addItems(["hearing", "hard_of_hearing", "deaf"])
            
            # Idioma preferido
            self.preferred_language_input = QComboBox()
            self.preferred_language_input.addItems(["es", "en", "fr", "pt"])
            
            # Nivel de lengua de señas
            self.sign_language_level_input = QComboBox()
            self.sign_language_level_input.addItems(["beginner", "intermediate", "advanced", "native"])
            
            profile_layout.addWidget(QLabel("Estado Auditivo:"), 0, 0)
            profile_layout.addWidget(self.hearing_status_input, 0, 1)
            profile_layout.addWidget(QLabel("Idioma Preferido:"), 0, 2)
            profile_layout.addWidget(self.preferred_language_input, 0, 3)
            profile_layout.addWidget(QLabel("Nivel de Señas:"), 1, 0)
            profile_layout.addWidget(self.sign_language_level_input, 1, 1)
            
            # Foto de perfil
            self.profile_picture_label = QLabel("Sin imagen")
            self.profile_picture_label.setFixedSize(100, 100)
            self.profile_picture_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
            self.profile_picture_button = QPushButton("Seleccionar Imagen")
            
            profile_layout.addWidget(QLabel("Foto de Perfil:"), 1, 2)
            profile_layout.addWidget(self.profile_picture_label, 1, 3)
            profile_layout.addWidget(self.profile_picture_button, 2, 3)
            
            layout.addWidget(profile_group)
            
            # === INFORMACIÓN MÉDICA ===
            medical_group = QGroupBox("🏥 Información Médica")
            medical_layout = QGridLayout(medical_group)
            
            # Tipo y grado de pérdida auditiva
            self.hearing_loss_type_input = QComboBox()
            self.hearing_loss_type_input.addItems(["none", "conductive", "sensorineural", "mixed"])
            
            self.hearing_loss_degree_input = QComboBox()
            self.hearing_loss_degree_input.addItems(["none", "mild", "moderate", "severe", "profound"])
            
            medical_layout.addWidget(QLabel("Tipo de Pérdida:"), 0, 0)
            medical_layout.addWidget(self.hearing_loss_type_input, 0, 1)
            medical_layout.addWidget(QLabel("Grado de Pérdida:"), 0, 2)
            medical_layout.addWidget(self.hearing_loss_degree_input, 0, 3)
            
            # Dispositivos auditivos
            self.uses_hearing_aids_checkbox = QCheckBox("Usa audífonos")
            self.has_cochlear_implant_checkbox = QCheckBox("Tiene implante coclear")
            
            medical_layout.addWidget(self.uses_hearing_aids_checkbox, 1, 0, 1, 2)
            medical_layout.addWidget(self.has_cochlear_implant_checkbox, 1, 2, 1, 2)
            
            # Preferencias y notas
            self.communication_preferences_input = QTextEdit()
            self.communication_preferences_input.setMaximumHeight(60)
            self.communication_preferences_input.setPlaceholderText("Preferencias de comunicación...")
            
            self.medical_notes_input = QTextEdit()
            self.medical_notes_input.setMaximumHeight(60)
            self.medical_notes_input.setPlaceholderText("Notas médicas adicionales...")
            
            medical_layout.addWidget(QLabel("Preferencias de Comunicación:"), 2, 0)
            medical_layout.addWidget(self.communication_preferences_input, 2, 1, 1, 3)
            medical_layout.addWidget(QLabel("Notas Médicas:"), 3, 0)
            medical_layout.addWidget(self.medical_notes_input, 3, 1, 1, 3)
            
            layout.addWidget(medical_group)
        
        # === CONFIGURACIÓN ADMINISTRATIVA ===
        admin_group = QGroupBox("🔧 Configuración Administrativa")
        admin_layout = QGridLayout(admin_group)
        
        # Rol
        self.role_input = QComboBox()
        self.role_input.addItems(["user", "instructor", "admin", "therapist"])
        
        admin_layout.addWidget(QLabel("Rol:"), 0, 0)
        admin_layout.addWidget(self.role_input, 0, 1)
        
        # Checkboxes administrativos (solo BD expandida)
        if self.db_manager:
            self.is_active_checkbox = QCheckBox("Usuario activo")
            self.is_active_checkbox.setChecked(False)  # Por defecto desactivado
            self.email_verified_checkbox = QCheckBox("Email verificado")
            self.email_verified_checkbox.setChecked(False)  # Por defecto desactivado
            self.must_change_password_checkbox = QCheckBox("Debe cambiar contraseña")
            
            # Solo el administrador puede activar/desactivar estos checkboxes
            is_admin = self.current_user_role == 'admin'
            self.is_active_checkbox.setEnabled(is_admin)
            self.email_verified_checkbox.setEnabled(is_admin)
            
            # Si no es admin, mostrar tooltip explicativo
            if not is_admin:
                self.is_active_checkbox.setToolTip("Solo el administrador puede activar usuarios")
                self.email_verified_checkbox.setToolTip("Solo el administrador puede verificar emails")
            
            admin_layout.addWidget(self.is_active_checkbox, 0, 2)
            admin_layout.addWidget(self.email_verified_checkbox, 0, 3)
            admin_layout.addWidget(self.must_change_password_checkbox, 1, 0, 1, 2)
        
        layout.addWidget(admin_group)
        
        # === BOTÓN DE GUARDAR ===
        button_text = "Guardar Cambios" if self.is_edit_mode else "Registrar Usuario"
        self.save_button = QPushButton(button_text)
        self.save_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        
        layout.addWidget(self.save_button)
        
        # Agregar scroll al layout principal
        main_layout.addWidget(scroll)
        
        # Conectar señales
        self.save_button.clicked.connect(self.handle_save)
        if self.db_manager:
            self.profile_picture_button.clicked.connect(self.select_profile_picture)
        
        # Cargar datos
        self.load_countries()
        if self.is_edit_mode:
            self.load_user_data()

    def select_profile_picture(self):
        """Seleccionar imagen de perfil"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Seleccionar Imagen de Perfil", "", 
            "Archivos de imagen (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.profile_picture_url = file_path
            # Mostrar preview de la imagen
            pixmap = QPixmap(file_path)
            scaled_pixmap = pixmap.scaled(100, 100, aspectRatioMode=1)
            self.profile_picture_label.setPixmap(scaled_pixmap)
            self.profile_picture_label.setText("")
    
    def load_countries(self):
        """Cargar países en los combobox"""
        if self.db_manager:
            # Usar base de datos expandida
            countries = self.db_manager.execute_query("SELECT country_name FROM countries ORDER BY country_name")
            country_list = [country[0] for country in countries]
        else:
            # Usar API externa como fallback
            try:
                country_list = get_countries_safe()
            except:
                country_list = ["Colombia", "Estados Unidos", "México", "España", "Argentina"]
        
        self.birth_country_input.addItems(["Seleccionar país..."] + country_list)
        self.residence_country_input.addItems(["Seleccionar país..."] + country_list)
    
    def load_user_data(self):
        """Cargar datos del usuario para edición"""
        if self.db_manager:
            # Usar base de datos expandida
            user_data = self.db_manager.get_user_profile(self.user_id)
            if user_data:
                self.username_input.setText(user_data[1] or "")
                self.first_name_input.setText(user_data[3] or "")
                self.last_name_input.setText(user_data[4] or "")
                self.email_input.setText(user_data[5] or "")
                self.phone_input.setText(user_data[6] or "")
                
                # Fecha de nacimiento
                if user_data[7]:
                    self.birth_date_input.setDate(QDate.fromString(user_data[7], "yyyy-MM-dd"))
                
                # Estado auditivo y configuraciones
                self.hearing_status_input.setCurrentText(user_data[12] or "hearing")
                self.preferred_language_input.setCurrentText(user_data[13] or "es")
                self.sign_language_level_input.setCurrentText(user_data[14] or "beginner")
                self.role_input.setCurrentText(user_data[15] or "user")
                
                # Checkboxes
                self.is_active_checkbox.setChecked(bool(user_data[16]))
                self.email_verified_checkbox.setChecked(bool(user_data[17]))
                self.must_change_password_checkbox.setChecked(bool(user_data[18]))
                
                # Imagen de perfil
                if user_data[11]:  # profile_picture_url
                    self.profile_picture_url = user_data[11]
                    try:
                        pixmap = QPixmap(user_data[11])
                        scaled_pixmap = pixmap.scaled(100, 100, aspectRatioMode=1)
                        self.profile_picture_label.setPixmap(scaled_pixmap)
                        self.profile_picture_label.setText("")
                    except:
                        pass
                
                # Cargar perfil médico si existe
                medical_profile = self.db_manager.execute_query(
                    "SELECT * FROM user_medical_profiles WHERE user_id = ?", (self.user_id,)
                )
                if medical_profile and len(medical_profile) > 0:
                    profile = medical_profile[0]
                    self.hearing_loss_type_input.setCurrentText(profile[2] or "none")
                    self.hearing_loss_degree_input.setCurrentText(profile[3] or "none")
                    self.uses_hearing_aids_checkbox.setChecked(bool(profile[4]))
                    self.has_cochlear_implant_checkbox.setChecked(bool(profile[5]))
                    self.communication_preferences_input.setPlainText(profile[6] or "")
                    self.medical_notes_input.setPlainText(profile[7] or "")
        else:
            # Usar base de datos original
            user_data = get_user_details_by_id(self.user_id)
            if user_data:
                self.username_input.setText(user_data['username'] or "")
                self.email_input.setText(user_data['email'] or "")
                self.first_name_input.setText(user_data['first_name'] or "")
                self.last_name_input.setText(user_data['last_name'] or "")
                if user_data['birth_date']:
                    self.birth_date_input.setDate(QDate.fromString(user_data['birth_date'], "yyyy-MM-dd"))
                self.birth_city_input.setText(user_data['birth_city'] or "")
                self.birth_country_input.setCurrentText(user_data['birth_country'] or "")
                self.residence_city_input.setText(user_data['residence_city'] or "")
                self.residence_country_input.setCurrentText(user_data['residence_country'] or "")
                self.role_input.setCurrentText(user_data['role'] or "user")
    
    def handle_save(self):
        """Manejar guardado del usuario con todos los campos"""
        # Recolectar datos básicos
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        
        # Validaciones básicas
        if not all([username, email, first_name, last_name]):
            QMessageBox.warning(self, "Campos Incompletos", 
                               "Por favor, completa al menos: usuario, email, nombres y apellidos.")
            return
        
        if not self.is_edit_mode:
            password = self.password_input.text()
            confirm_password = self.confirm_password_input.text()
            
            if not password:
                QMessageBox.warning(self, "Contraseña Requerida", "Por favor, ingresa una contraseña.")
                return
            
            if password != confirm_password:
                QMessageBox.warning(self, "Contraseñas No Coinciden", 
                                   "La contraseña y la confirmación no coinciden.")
                return
        
        try:
            if self.db_manager:
                # Usar base de datos expandida
                self.save_user_expanded()
            else:
                # Usar base de datos original
                self.save_user_original()
            
            QMessageBox.information(self, "Éxito", 
                                   "Usuario guardado correctamente." if self.is_edit_mode 
                                   else "Usuario registrado correctamente.")
            
            if self.admin_panel:
                self.admin_panel.populate_users_table()
            
            self.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar usuario: {str(e)}")
    
    def save_user_expanded(self):
        """Guardar usuario en base de datos expandida"""
        if self.is_edit_mode:
            # Actualizar usuario existente
            user_data = {
                'username': self.username_input.text().strip(),
                'first_name': self.first_name_input.text().strip(),
                'last_name': self.last_name_input.text().strip(),
                'email': self.email_input.text().strip(),
                'phone': self.phone_input.text().strip(),
                'hearing_status': self.hearing_status_input.currentText(),
                'preferred_language': self.preferred_language_input.currentText(),
                'sign_language_level': self.sign_language_level_input.currentText(),
                'profile_picture_url': self.profile_picture_url,
                'role': self.role_input.currentText(),
                'is_active': self.is_active_checkbox.isChecked(),
                'email_verified': self.email_verified_checkbox.isChecked(),
                'must_change_password': self.must_change_password_checkbox.isChecked()
            }
            
            # Solo permitir cambios de activación si es administrador
            is_admin = self.current_user_role == 'admin'
            if not is_admin:
                # Si no es admin, mantener los valores actuales de activación
                current_user = self.db_manager.get_user_profile(self.user_id)
                if current_user:
                    user_data['is_active'] = bool(current_user[16])  # is_active
                    user_data['email_verified'] = bool(current_user[17])  # email_verified
            
            # Actualizar en base de datos
            self.db_manager.execute_query("""
                UPDATE users SET 
                    username = ?, first_name = ?, last_name = ?, email = ?, phone = ?,
                    hearing_status = ?, preferred_language = ?, sign_language_level = ?,
                    profile_picture_url = ?, role = ?, is_active = ?, email_verified = ?,
                    must_change_password = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                user_data['username'], user_data['first_name'], user_data['last_name'],
                user_data['email'], user_data['phone'], user_data['hearing_status'],
                user_data['preferred_language'], user_data['sign_language_level'],
                user_data['profile_picture_url'], user_data['role'], user_data['is_active'],
                user_data['email_verified'], user_data['must_change_password'], self.user_id
            ))
            
            # Actualizar perfil médico
            if hasattr(self, 'hearing_loss_type_input'):
                self.db_manager.execute_query("""
                    INSERT OR REPLACE INTO user_medical_profiles (
                        user_id, hearing_loss_type, hearing_loss_degree, uses_hearing_aids,
                        has_cochlear_implant, communication_preferences, medical_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.user_id,
                    self.hearing_loss_type_input.currentText(),
                    self.hearing_loss_degree_input.currentText(),
                    self.uses_hearing_aids_checkbox.isChecked(),
                    self.has_cochlear_implant_checkbox.isChecked(),
                    self.communication_preferences_input.toPlainText(),
                    self.medical_notes_input.toPlainText()
                ))
        else:
            # Crear nuevo usuario
            import hashlib
            password_hash = hashlib.sha256(self.password_input.text().encode()).hexdigest()
            
            user_id = self.db_manager.add_user(
                username=self.username_input.text().strip(),
                password_hash=password_hash,
                first_name=self.first_name_input.text().strip(),
                last_name=self.last_name_input.text().strip(),
                email=self.email_input.text().strip(),
                phone=self.phone_input.text().strip(),
                role=self.role_input.currentText(),
                hearing_status=self.hearing_status_input.currentText(),
                preferred_language=self.preferred_language_input.currentText()
            )
            
            # Establecer estado de activación según el rol del usuario actual
            is_admin = self.current_user_role == 'admin'
            is_active = self.is_active_checkbox.isChecked() if is_admin else False
            email_verified = self.email_verified_checkbox.isChecked() if is_admin else False
            
            # Actualizar el estado de activación del usuario recién creado
            self.db_manager.execute_query("""
                UPDATE users SET is_active = ?, email_verified = ?
                WHERE id = ?
            """, (is_active, email_verified, user_id))
            
            # Crear perfil médico si hay datos
            if hasattr(self, 'hearing_loss_type_input'):
                self.db_manager.execute_query("""
                    INSERT INTO user_medical_profiles (
                        user_id, hearing_loss_type, hearing_loss_degree, uses_hearing_aids,
                        has_cochlear_implant, communication_preferences, medical_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    self.hearing_loss_type_input.currentText(),
                    self.hearing_loss_degree_input.currentText(),
                    self.uses_hearing_aids_checkbox.isChecked(),
                    self.has_cochlear_implant_checkbox.isChecked(),
                    self.communication_preferences_input.toPlainText(),
                    self.medical_notes_input.toPlainText()
                ))
    
    def save_user_original(self):
        """Guardar usuario en base de datos original"""
        if self.is_edit_mode:
            # Actualizar usuario existente
            success = update_user_details(
                self.user_id,
                self.username_input.text().strip(),
                self.first_name_input.text().strip(),
                self.last_name_input.text().strip(),
                self.email_input.text().strip(),
                self.role_input.currentText()
            )
            if not success:
                raise Exception("El nombre de usuario o email ya existe")
        else:
            # Crear nuevo usuario
            birth_date = self.birth_date_input.date().toString("yyyy-MM-dd")
            birth_country = self.birth_country_input.currentText()
            birth_city = self.birth_city_input.text().strip()
            residence_country = self.residence_country_input.currentText()
            residence_city = self.residence_city_input.text().strip()
            
            success = add_user(
                self.username_input.text().strip(),
                self.password_input.text(),
                self.first_name_input.text().strip(),
                self.last_name_input.text().strip(),
                self.email_input.text().strip(),
                birth_date,
                birth_country if birth_country != "Seleccionar país..." else "",
                birth_city,
                residence_country if residence_country != "Seleccionar país..." else "",
                residence_city,
                self.role_input.currentText()
            )
            
            if not success:
                raise Exception("El usuario o email ya existe")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = UserFormWindow()
    window.show()
    sys.exit(app.exec_())
