import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QMessageBox, QHeaderView, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QColor, QFont

from database import get_all_users, delete_user
from config import get_database_version
from database_v2 import DatabaseManager
from user_form_window import UserFormWindow
from estadisticas_integrada_final import show_integrated_statistics

# ── Paleta de colores ──────────────────────────────────────────────────────────
C_SIDEBAR_BG    = "#1e1e2e"
C_SIDEBAR_HOVER = "#2d2d44"
C_ACCENT        = "#7c3aed"
C_ACCENT_LIGHT  = "#ede9fe"
C_BG            = "#f8fafc"
C_TABLE_HEADER  = "#f1f5f9"
C_ROW_ALT       = "#f8f9ff"
C_ROW_HOVER     = "#ede9fe"
C_BORDER        = "#e2e8f0"
C_TEXT_MAIN     = "#1e293b"
C_TEXT_MUTED    = "#94a3b8"
C_WHITE         = "#ffffff"

BADGE_ADMIN     = ("#7c3aed", C_WHITE)
BADGE_USER      = ("#64748b", C_WHITE)
BADGE_YES       = ("#16a34a", C_WHITE)
BADGE_NO        = ("#dc2626", C_WHITE)


def badge_item(text: str, bg: str, fg: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignCenter)
    item.setBackground(QColor(bg))
    item.setForeground(QColor(fg))
    font = QFont()
    font.setBold(True)
    font.setPointSize(8)
    item.setFont(font)
    return item


class SidebarButton(QPushButton):
    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(f"  {icon_text}  {label}", parent)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #c4b5fd;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                text-align: left;
                padding-left: 12px;
            }}
            QPushButton:hover {{
                background: {C_SIDEBAR_HOVER};
                color: {C_WHITE};
            }}
            QPushButton:pressed {{
                background: {C_ACCENT};
                color: {C_WHITE};
            }}
        """)


class ActionButton(QPushButton):
    """Botón de acción pequeño para la barra superior de la tabla."""
    def __init__(self, icon_text: str, label: str, color: str = C_ACCENT, parent=None):
        super().__init__(f"{icon_text}  {label}", parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(34)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: {C_WHITE};
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                opacity: 0.85;
                background: {color}cc;
            }}
            QPushButton:pressed {{
                background: {color}99;
            }}
        """)


class AdminPanel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.user_form_win = None
        self.sessions_win = None
        self.gesture_manager_win = None
        self._is_expanded = get_database_version() == "expanded"

        self.setWindowTitle("Intérprete LSC — Panel de Administración")
        self.setGeometry(100, 80, 1100, 680)
        self.setMinimumSize(900, 580)
        self.setWindowIcon(self._make_icon())
        self.setStyleSheet(f"background: {C_BG}; font-family: 'Segoe UI', sans-serif;")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_main_area(), 1)

        self.populate_users_table()

    # ── Sidebar ────────────────────────────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background: {C_SIDEBAR_BG};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        # Logo / título
        logo = QLabel("🤲  LSC Admin")
        logo.setStyleSheet(f"color: {C_WHITE}; font-size: 16px; font-weight: bold; padding: 8px 4px 20px 4px;")
        layout.addWidget(logo)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {C_SIDEBAR_HOVER};")
        layout.addWidget(sep)
        layout.addSpacing(8)

        # Sección NAVEGACIÓN
        nav_label = QLabel("NAVEGACIÓN")
        nav_label.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 10px; font-weight: bold; padding: 4px 4px 2px 4px;")
        layout.addWidget(nav_label)

        self.btn_stats     = SidebarButton("📊", "Estadísticas")
        self.btn_analytics = SidebarButton("🔍", "Analíticas globales")
        self.btn_gestures  = SidebarButton("🤲", "Gestionar Gestos")
        self.btn_learning  = SidebarButton("🎓", "Modo Aprendizaje")
        layout.addWidget(self.btn_stats)
        layout.addWidget(self.btn_analytics)
        layout.addWidget(self.btn_gestures)
        layout.addWidget(self.btn_learning)

        layout.addSpacing(12)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color: {C_SIDEBAR_HOVER};")
        layout.addWidget(sep2)
        layout.addSpacing(8)

        # Sección USUARIOS
        usr_label = QLabel("USUARIOS")
        usr_label.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 10px; font-weight: bold; padding: 4px 4px 2px 4px;")
        layout.addWidget(usr_label)

        self.btn_sessions = SidebarButton("📋", "Ver Sesiones")
        layout.addWidget(self.btn_sessions)

        layout.addStretch()

        # Cerrar sesión al fondo
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setStyleSheet(f"color: {C_SIDEBAR_HOVER};")
        layout.addWidget(sep3)
        layout.addSpacing(6)

        self.btn_logout = SidebarButton("🚪", "Cerrar Sesión")
        self.btn_logout.setStyleSheet(self.btn_logout.styleSheet().replace("#c4b5fd", "#fca5a5"))
        layout.addWidget(self.btn_logout)

        # Conexiones sidebar
        self.btn_stats.clicked.connect(self.handle_show_statistics)
        self.btn_analytics.clicked.connect(self.handle_show_analytics)
        self.btn_gestures.clicked.connect(self.handle_manage_gestures)
        self.btn_learning.clicked.connect(self.handle_learning_mode)
        self.btn_sessions.clicked.connect(self.handle_view_sessions)
        self.btn_logout.clicked.connect(self.logout)

        return sidebar

    # ── Área principal ─────────────────────────────────────────────────────────
    def _build_main_area(self) -> QWidget:
        main = QWidget()
        main.setStyleSheet(f"background: {C_BG};")
        layout = QVBoxLayout(main)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        # Encabezado
        header_layout = QHBoxLayout()
        title = QLabel("Gestión de Usuarios")
        title.setStyleSheet(f"color: {C_TEXT_MAIN}; font-size: 22px; font-weight: bold;")
        subtitle = QLabel("Administra los usuarios registrados en el sistema")
        subtitle.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header_layout.addLayout(title_col)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Barra de acciones
        layout.addWidget(self._build_action_bar())

        # Tabla
        layout.addWidget(self._build_table(), 1)

        return main

    def _build_action_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(f"""
            QWidget {{
                background: {C_WHITE};
                border: 1px solid {C_BORDER};
                border-radius: 10px;
            }}
        """)
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(8)

        self.btn_add    = ActionButton("➕", "Agregar",  "#2563eb")
        self.btn_edit   = ActionButton("✏️", "Editar",   "#0891b2")
        self.btn_delete = ActionButton("🗑️", "Eliminar", "#dc2626")

        row.addWidget(self.btn_add)
        row.addWidget(self.btn_edit)
        row.addWidget(self.btn_delete)

        if self._is_expanded:
            self.btn_activate   = ActionButton("✅", "Activar",         "#16a34a")
            self.btn_deactivate = ActionButton("⛔", "Desactivar",      "#ea580c")
            self.btn_verify     = ActionButton("📧", "Verificar Email", "#7c3aed")
            row.addWidget(self.btn_activate)
            row.addWidget(self.btn_deactivate)
            row.addWidget(self.btn_verify)

            self.btn_activate.clicked.connect(self.handle_activate_user)
            self.btn_deactivate.clicked.connect(self.handle_deactivate_user)
            self.btn_verify.clicked.connect(self.handle_verify_email)

        row.addStretch()

        # Contador de usuarios
        self.user_count_label = QLabel("")
        self.user_count_label.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px; background: transparent; border: none;")
        row.addWidget(self.user_count_label)

        # Conexiones
        self.btn_add.clicked.connect(self.handle_add_user)
        self.btn_edit.clicked.connect(self.handle_edit_user)
        self.btn_delete.clicked.connect(self.handle_delete_user)

        return bar

    def _build_table(self) -> QTableWidget:
        cols = ["ID", "Username", "Nombre", "Apellido", "Email", "Rol", "Activo", "Email Verificado"] \
               if self._is_expanded else \
               ["ID", "Username", "Nombre", "Apellido", "Email", "Rol"]

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(len(cols))
        self.users_table.setHorizontalHeaderLabels(cols)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.setShowGrid(False)
        self.users_table.setFocusPolicy(Qt.NoFocus)
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.users_table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.users_table.setStyleSheet(f"""
            QTableWidget {{
                background: {C_WHITE};
                alternate-background-color: {C_ROW_ALT};
                border: 1px solid {C_BORDER};
                border-radius: 10px;
                outline: none;
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                color: {C_TEXT_MAIN};
                font-size: 13px;
                border-bottom: 1px solid {C_BORDER};
            }}
            QTableWidget::item:selected {{
                background: {C_ROW_HOVER};
                color: {C_TEXT_MAIN};
            }}
            QHeaderView::section {{
                background: {C_TABLE_HEADER};
                color: {C_TEXT_MUTED};
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid {C_BORDER};
            }}
            QScrollBar:vertical {{
                background: {C_BG};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {C_BORDER};
                border-radius: 4px;
                min-height: 20px;
            }}
        """)
        return self.users_table

    # ── Poblar tabla ───────────────────────────────────────────────────────────
    def populate_users_table(self):
        self.users_table.setRowCount(0)

        if self._is_expanded:
            db = DatabaseManager()
            users = db.execute_query("""
                SELECT id, username, first_name, last_name, email, role, is_active, email_verified
                FROM users ORDER BY username
            """)
            for r, u in enumerate(users):
                self.users_table.insertRow(r)
                self.users_table.setRowHeight(r, 46)

                for c in range(6):
                    item = QTableWidgetItem(str(u[c] or ""))
                    if c == 0:
                        item.setData(Qt.UserRole, u[0])
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setForeground(QColor(C_TEXT_MUTED))
                    self.users_table.setItem(r, c, item)

                # Badge Rol
                role_txt = str(u[5] or "")
                role_bg, role_fg = BADGE_ADMIN if role_txt == "admin" else BADGE_USER
                self.users_table.setItem(r, 5, badge_item(role_txt, role_bg, role_fg))

                # Badge Activo
                active = bool(u[6])
                self.users_table.setItem(r, 6, badge_item("Sí" if active else "No",
                                                           *BADGE_YES if active else BADGE_NO))

                # Badge Email verificado
                verified = bool(u[7])
                self.users_table.setItem(r, 7, badge_item("Sí" if verified else "No",
                                                           *BADGE_YES if verified else BADGE_NO))
        else:
            users = get_all_users()
            for r, u in enumerate(users):
                self.users_table.insertRow(r)
                self.users_table.setRowHeight(r, 46)
                for c, val in enumerate(u):
                    item = QTableWidgetItem(str(val))
                    if c == 0:
                        item.setData(Qt.UserRole, u[0])
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setForeground(QColor(C_TEXT_MUTED))
                    self.users_table.setItem(r, c, item)

        count = self.users_table.rowCount()
        self.user_count_label.setText(f"{count} usuario{'s' if count != 1 else ''}")

    # ── Handlers ───────────────────────────────────────────────────────────────
    def _selected_user(self):
        rows = self.users_table.selectionModel().selectedRows()
        if not rows:
            return None, None
        row = rows[0].row()
        return (self.users_table.item(row, 0).data(Qt.UserRole),
                self.users_table.item(row, 1).text())

    def handle_add_user(self):
        self.user_form_win = UserFormWindow(admin_panel=self, current_user_role='admin')
        self.user_form_win.show()

    def handle_edit_user(self):
        uid, _ = self._selected_user()
        if uid is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un usuario para editar.")
            return
        self.user_form_win = UserFormWindow(user_id=uid, admin_panel=self, current_user_role='admin')
        self.user_form_win.show()

    def handle_delete_user(self):
        uid, username = self._selected_user()
        if uid is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un usuario para eliminar.")
            return
        if username == 'admin':
            QMessageBox.critical(self, "Error", "No se puede eliminar al usuario administrador.")
            return
        reply = QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Eliminar al usuario '{username}'?\nEsta acción es irreversible.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_user(uid)
            self.populate_users_table()

    def handle_activate_user(self):
        uid, username = self._selected_user()
        if uid is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un usuario para activar.")
            return
        DatabaseManager().execute_query("UPDATE users SET is_active = 1 WHERE id = ?", (uid,))
        self.populate_users_table()

    def handle_deactivate_user(self):
        uid, username = self._selected_user()
        if uid is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un usuario para desactivar.")
            return
        if username == 'admin':
            QMessageBox.critical(self, "Error", "No se puede desactivar al administrador.")
            return
        DatabaseManager().execute_query("UPDATE users SET is_active = 0 WHERE id = ?", (uid,))
        self.populate_users_table()

    def handle_verify_email(self):
        uid, username = self._selected_user()
        if uid is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un usuario para verificar email.")
            return
        DatabaseManager().execute_query("UPDATE users SET email_verified = 1 WHERE id = ?", (uid,))
        self.populate_users_table()

    def handle_view_sessions(self):
        uid, username = self._selected_user()
        if uid is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un usuario para ver sus sesiones.")
            return
        self.controller.show_user_sessions_for_admin(uid, username)

    def handle_manage_gestures(self):
        self.controller.show_gesture_manager()

    def handle_learning_mode(self):
        self.controller.show_learning_mode()

    def handle_show_statistics(self):
        try:
            show_integrated_statistics()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir las estadísticas:\n{e}")

    def handle_show_analytics(self):
        try:
            from analytics_window import AnalyticsWindow
            self._analytics_win = AnalyticsWindow(self)
            self._analytics_win.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir analíticas:\n{e}")

    def logout(self):
        self.controller.logout()
        self.close()

    def _make_icon(self):
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        return QIcon(px)


if __name__ == '__main__':
    class MockController:
        def logout(self): print("logout")
        def show_gesture_manager(self): print("gestures")
        def show_user_sessions_for_admin(self, uid, name): print(f"sessions {uid} {name}")

    app = QApplication(sys.argv)
    w = AdminPanel(MockController())
    w.show()
    sys.exit(app.exec_())
