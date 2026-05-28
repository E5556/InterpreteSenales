import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon
from database import get_user_sessions

# Paleta (misma que admin_panel y gamification_window)
C_SIDEBAR_BG   = "#1e1e2e"
C_ACCENT       = "#7c3aed"
C_ACCENT_LIGHT = "#a78bfa"
C_BG           = "#f8fafc"
C_CARD_BG      = "#ffffff"
C_TEXT_DARK    = "#1e293b"
C_TEXT_MUTED   = "#64748b"
C_BORDER       = "#e2e8f0"
C_DANGER       = "#ef4444"


class SidebarBtn(QPushButton):
    def __init__(self, icon, text):
        super().__init__(f"  {icon}  {text}")
        self.setCheckable(True)
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 13))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 10px;
                text-align: left;
                padding-left: 12px;
            }}
            QPushButton:hover {{
                background: rgba(124,58,237,0.18);
                color: {C_ACCENT_LIGHT};
            }}
            QPushButton:checked {{
                background: {C_ACCENT};
                color: white;
                font-weight: bold;
            }}
        """)


class SessionsWindow(QWidget):
    def __init__(self, user_id, controller, is_admin_mode=False):
        super().__init__()
        self.user_id = int(user_id)
        self.controller = controller
        self.is_admin_mode = is_admin_mode

        self.setWindowTitle("Intérprete LSC")
        self.setGeometry(200, 100, 950, 620)
        self.setMinimumSize(800, 500)
        self.setWindowIcon(self._blank_icon())

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background: {C_SIDEBAR_BG};")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(12, 28, 12, 24)
        sb.setSpacing(6)

        # Usuario en sidebar
        self._username_label = QLabel("...")
        self._username_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self._username_label.setStyleSheet("color: white; padding-bottom: 4px;")
        sb.addWidget(self._username_label)

        role_lbl = QLabel("Usuario" if not is_admin_mode else "Vista Admin")
        role_lbl.setFont(QFont("Segoe UI", 10))
        role_lbl.setStyleSheet(f"color: {C_ACCENT_LIGHT}; padding-bottom: 16px;")
        sb.addWidget(role_lbl)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: #2d2d44;")
        sb.addWidget(sep)
        sb.addSpacing(10)

        # Botones de navegación
        self.btn_sessions   = SidebarBtn("📋", "Mis Sesiones")
        self.btn_new        = SidebarBtn("🎬", "Nueva Sesión")
        self.btn_learning   = SidebarBtn("🎓", "Modo Aprendizaje")
        self.btn_logros     = SidebarBtn("🏆", "Mis Logros")

        self._nav_btns = [self.btn_sessions, self.btn_new, self.btn_learning, self.btn_logros]
        for btn in self._nav_btns:
            sb.addWidget(btn)

        if is_admin_mode:
            self.btn_new.hide()

        sb.addStretch()

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #2d2d44;")
        sb.addWidget(sep2)
        sb.addSpacing(8)

        self.btn_logout = QPushButton("  🚪  Cerrar Sesión")
        self.btn_logout.setFixedHeight(44)
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.setFont(QFont("Segoe UI", 12))
        self.btn_logout.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_DANGER};
                border: 1px solid {C_DANGER};
                border-radius: 8px;
                text-align: left;
                padding-left: 12px;
            }}
            QPushButton:hover {{ background: rgba(239,68,68,0.12); }}
        """)
        if is_admin_mode:
            self.btn_logout.hide()
        sb.addWidget(self.btn_logout)

        root.addWidget(sidebar)

        # ── CONTENIDO PRINCIPAL ──────────────────────────────────────
        self.content = QWidget()
        self.content.setStyleSheet(f"background: {C_BG};")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(36, 32, 36, 32)
        self.content_layout.setSpacing(18)
        root.addWidget(self.content)

        # Cabecera del contenido
        self.page_title = QLabel("Mis Sesiones de Interpretación")
        self.page_title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.page_title.setStyleSheet(f"color: {C_TEXT_DARK};")
        self.content_layout.addWidget(self.page_title)

        self.page_subtitle = QLabel("Haz clic en una sesión para ver su historial de interpretaciones")
        self.page_subtitle.setFont(QFont("Segoe UI", 11))
        self.page_subtitle.setStyleSheet(f"color: {C_TEXT_MUTED};")
        self.content_layout.addWidget(self.page_subtitle)

        # Lista de sesiones
        self.sessions_list = QListWidget()
        self.sessions_list.setStyleSheet(f"""
            QListWidget {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 12px;
                padding: 8px;
                font-size: 13px;
                color: {C_TEXT_DARK};
            }}
            QListWidget::item {{
                padding: 10px 14px;
                border-radius: 8px;
            }}
            QListWidget::item:hover {{
                background: #f1f5f9;
            }}
            QListWidget::item:selected {{
                background: {C_ACCENT};
                color: white;
            }}
        """)
        self.content_layout.addWidget(self.sessions_list)
        self.populate_sessions()

        # Conexiones
        self.btn_sessions.clicked.connect(lambda: self._select_nav(self.btn_sessions))
        self.btn_new.clicked.connect(self.start_new_session)
        self.btn_learning.clicked.connect(self.open_learning_mode)
        self.btn_logros.clicked.connect(self.open_gamification)
        self.btn_logout.clicked.connect(self.logout)
        self.sessions_list.itemClicked.connect(self.view_session_history)

        # Estado inicial
        self.btn_sessions.setChecked(True)
        self._load_username()

    def _select_nav(self, active_btn):
        for btn in self._nav_btns:
            btn.setChecked(btn is active_btn)

    def _load_username(self):
        try:
            import sqlite3
            from config import get_database_path
            conn = sqlite3.connect(get_database_path())
            cur = conn.cursor()
            cur.execute("SELECT username, first_name FROM users WHERE id=?", (self.user_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                name = row[1] if row[1] else row[0]
                self._username_label.setText(name.capitalize())
        except Exception:
            pass

    def populate_sessions(self):
        self.sessions_list.clear()
        sessions = get_user_sessions(self.user_id)
        if not sessions:
            item = QListWidgetItem("  No hay sesiones anteriores.")
            item.setForeground(Qt.gray)
            self.sessions_list.addItem(item)
        else:
            for session in sessions:
                session_id, timestamp = session
                if timestamp and timestamp != "None":
                    text = f"  📅  Sesión del {timestamp}"
                else:
                    text = "  📅  Sesión sin fecha registrada"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, session_id)
                self.sessions_list.addItem(item)

    def start_new_session(self):
        self._select_nav(self.btn_new)
        self.controller.start_new_interpreter_session(self.user_id)
        self.close()

    def view_session_history(self, item):
        session_id = item.data(Qt.UserRole)
        if session_id:
            self.controller.show_history_window(session_id)
            self.close()

    def open_gamification(self):
        self._select_nav(self.btn_logros)
        self.controller.show_gamification(self.user_id)

    def open_learning_mode(self):
        self._select_nav(self.btn_learning)
        try:
            from learning_mode_window import LearningModeWindow
            self.learning_window = LearningModeWindow()
            self.learning_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el modo de aprendizaje:\n{str(e)}")

    def logout(self):
        self.controller.logout()
        self.close()

    def _blank_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)


if __name__ == '__main__':
    class MockController:
        def start_new_interpreter_session(self, user_id): print("Nueva sesión", user_id)
        def show_history_window(self, session_id): print("Historial", session_id)
        def show_gamification(self, user_id): print("Gamificación", user_id)
        def logout(self): print("Logout")

    app = QApplication(sys.argv)
    w = SessionsWindow(user_id=2, controller=MockController())
    w.show()
    sys.exit(app.exec_())
