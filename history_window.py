import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QLabel, QPushButton)
from PyQt5.QtCore import Qt
from database import get_session_interpretations, DATABASE_NAME
import sqlite3

class HistoryWindow(QWidget):
    def __init__(self, session_id, controller):
        super().__init__()
        self.session_id = session_id
        self.controller = controller
        
        # Necesitamos saber quién es el usuario para poder volver.
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,))
        result = cursor.fetchone()
        self.user_id = result[0] if result else None
        conn.close()
        
        self.setWindowTitle(f"Historial de la Sesión #{session_id}")
        self.setGeometry(400, 400, 500, 400)
        
        layout = QVBoxLayout(self)
        
        title_label = QLabel(f"<h2>Interpretaciones de la Sesión #{session_id}</h2>")
        self.interpretations_list = QListWidget(self)
        self.populate_interpretations()
        
        # Botones de navegación
        button_layout = QHBoxLayout()
        self.back_button = QPushButton("Volver al Menú de Sesiones", self)
        self.logout_button = QPushButton("Cerrar Sesión", self)
        button_layout.addWidget(self.back_button)
        button_layout.addWidget(self.logout_button)
        
        layout.addWidget(title_label)
        layout.addWidget(self.interpretations_list)
        layout.addLayout(button_layout)
        
        # Conexiones
        self.back_button.clicked.connect(self.go_back)
        self.logout_button.clicked.connect(self.logout)

    def populate_interpretations(self):
        self.interpretations_list.clear()
        interpretations = get_session_interpretations(self.session_id)
        if not interpretations:
            self.interpretations_list.addItem("No hay interpretaciones en esta sesión.")
        else:
            for i, interpretation in enumerate(interpretations):
                word, timestamp = interpretation
                item = QListWidgetItem(f"{i+1}. {word}  ({timestamp})")
                self.interpretations_list.addItem(item)

    def go_back(self):
        if self.user_id:
            self.controller.go_back_to_sessions(self.user_id)
            self.close()

    def logout(self):
        self.controller.logout()
        self.close()

# Para probar la ventana de forma independiente
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Necesitamos datos de prueba para ver algo
    from database import init_db, add_user, check_user, create_session, add_interpretation
    import sqlite3 # Necesario para la prueba
    DATABASE_NAME = "usuarios.db" # Necesario para la prueba

    class MockController:
        def go_back_to_sessions(self, user_id):
            print(f"Controller: Volver a sesiones para el usuario {user_id}")
        def logout(self):
            print("Controller: Cerrar sesión")

    init_db()
    if not check_user("hist_tester", "test"):
        add_user("hist_tester", "test")
    user_id = check_user("hist_tester", "test")
    if user_id:
        session_id = create_session(user_id)
        add_interpretation(session_id, "HOLA")
        add_interpretation(session_id, "PRUEBA")
        add_interpretation(session_id, "ADIOS")
    
    history_win = HistoryWindow(session_id=session_id, controller=MockController())
    history_win.show()
    sys.exit(app.exec_()) 