import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QFrame,
    QScrollArea, QProgressBar, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor
from database import get_user_sessions

C_SIDEBAR_BG   = "#1e1e2e"
C_ACCENT       = "#7c3aed"
C_ACCENT_LIGHT = "#a78bfa"
C_BG           = "#f8fafc"
C_CARD_BG      = "#ffffff"
C_TEXT_DARK    = "#1e293b"
C_TEXT_MUTED   = "#64748b"
C_BORDER       = "#e2e8f0"
C_DANGER       = "#ef4444"
C_SUCCESS      = "#22c55e"

RARITY_COLORS = {"common": "#64748b", "rare": "#3b82f6", "epic": "#8b5cf6"}
LEVEL_EMOJIS  = ["", "🌱", "📚", "💬", "🎯", "⭐", "🏆"]


class SidebarBtn(QPushButton):
    def __init__(self, icon, text):
        super().__init__(f"  {icon}  {text}")
        self.setCheckable(True)
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 13))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #94a3b8;
                border: none; border-radius: 10px;
                text-align: left; padding-left: 12px;
            }}
            QPushButton:hover {{ background: rgba(124,58,237,0.18); color: {C_ACCENT_LIGHT}; }}
            QPushButton:checked {{ background: {C_ACCENT}; color: white; font-weight: bold; }}
        """)


def _lbl(text, size=13, bold=False, color=C_TEXT_DARK, wrap=False):
    l = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet(f"color:{color}; background:transparent;")
    if wrap:
        l.setWordWrap(True)
    return l


class SessionsWindow(QWidget):
    def __init__(self, user_id, controller, is_admin_mode=False):
        super().__init__()
        self.user_id = int(user_id)
        self.controller = controller
        self.is_admin_mode = is_admin_mode

        self.setWindowTitle("Intérprete LSC")
        self.setGeometry(200, 100, 1000, 640)
        self.setMinimumSize(820, 520)
        self.setWindowIcon(self._blank_icon())

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background:{C_SIDEBAR_BG};")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(12, 28, 12, 24)
        sb.setSpacing(6)

        self._username_label = QLabel("...")
        self._username_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self._username_label.setStyleSheet("color:white; padding-bottom:4px;")
        sb.addWidget(self._username_label)

        role_lbl = QLabel("Usuario" if not is_admin_mode else "Vista Admin")
        role_lbl.setFont(QFont("Segoe UI", 10))
        role_lbl.setStyleSheet(f"color:{C_ACCENT_LIGHT}; padding-bottom:14px;")
        sb.addWidget(role_lbl)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background:#2d2d44;")
        sb.addWidget(sep)
        sb.addSpacing(10)

        self.btn_sessions  = SidebarBtn("📋", "Mis Sesiones")
        self.btn_new       = SidebarBtn("🎬", "Nueva Sesión")
        self.btn_learning  = SidebarBtn("🎓", "Modo Aprendizaje")
        self.btn_logros    = SidebarBtn("🏆", "Mis Logros")
        self.btn_retos     = SidebarBtn("🎯", "Retos del día")
        self.btn_historial = SidebarBtn("📜", "Historial de puntos")

        self._nav_btns = [
            self.btn_sessions, self.btn_new, self.btn_learning,
            self.btn_logros, self.btn_retos, self.btn_historial
        ]
        for btn in self._nav_btns:
            sb.addWidget(btn)

        if is_admin_mode:
            self.btn_new.hide()

        sb.addStretch()
        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setStyleSheet("background:#2d2d44;")
        sb.addWidget(sep2)
        sb.addSpacing(8)

        self.btn_logout = QPushButton("  🚪  Cerrar Sesión")
        self.btn_logout.setFixedHeight(44)
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.setFont(QFont("Segoe UI", 12))
        self.btn_logout.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{C_DANGER};
                border:1px solid {C_DANGER}; border-radius:8px;
                text-align:left; padding-left:12px; }}
            QPushButton:hover {{ background:rgba(239,68,68,0.12); }}
        """)
        if is_admin_mode:
            self.btn_logout.hide()
        sb.addWidget(self.btn_logout)

        root.addWidget(sidebar)

        # ── STACK DE PÁGINAS ─────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background:{C_BG};")
        root.addWidget(self.stack)

        self._page_sessions  = self._build_page_sessions()
        self._page_logros    = self._build_scroll_page(self._build_logros_content)
        self._page_retos     = self._build_scroll_page(self._build_retos_content)
        self._page_historial = self._build_scroll_page(self._build_historial_content)

        self.stack.addWidget(self._page_sessions)   # 0
        self.stack.addWidget(self._page_logros)     # 1
        self.stack.addWidget(self._page_retos)      # 2
        self.stack.addWidget(self._page_historial)  # 3

        # Conexiones sidebar
        self.btn_sessions.clicked.connect(lambda: self._go(0, self.btn_sessions))
        self.btn_new.clicked.connect(self.start_new_session)
        self.btn_learning.clicked.connect(self.open_learning_mode)
        self.btn_logros.clicked.connect(lambda: self._go(1, self.btn_logros))
        self.btn_retos.clicked.connect(lambda: self._go(2, self.btn_retos))
        self.btn_historial.clicked.connect(lambda: self._go(3, self.btn_historial))
        self.btn_logout.clicked.connect(self.logout)

        self._go(0, self.btn_sessions)
        self._load_username()

    # ── NAVEGACIÓN ────────────────────────────────────────────
    def _go(self, index, active_btn):
        for btn in self._nav_btns:
            btn.setChecked(btn is active_btn)
        self.stack.setCurrentIndex(index)

    # ── PÁGINA: SESIONES ──────────────────────────────────────
    def _build_page_sessions(self):
        page = QWidget()
        page.setStyleSheet(f"background:{C_BG};")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(14)

        lay.addWidget(_lbl("Mis Sesiones de Interpretación", 20, bold=True))
        lay.addWidget(_lbl("Haz clic en una sesión para ver su historial", 11, color=C_TEXT_MUTED))

        self.sessions_list = QListWidget()
        self.sessions_list.setStyleSheet(f"""
            QListWidget {{ background:{C_CARD_BG}; border:1px solid {C_BORDER};
                border-radius:12px; padding:8px; font-size:13px; color:{C_TEXT_DARK}; }}
            QListWidget::item {{ padding:10px 14px; border-radius:8px; }}
            QListWidget::item:hover {{ background:#f1f5f9; }}
            QListWidget::item:selected {{ background:{C_ACCENT}; color:white; }}
        """)
        self.sessions_list.itemClicked.connect(self.view_session_history)
        lay.addWidget(self.sessions_list)
        self.populate_sessions()
        return page

    # ── SCROLL WRAPPER ────────────────────────────────────────
    def _build_scroll_page(self, build_fn):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background:{C_BG};")
        inner = QWidget()
        inner.setStyleSheet(f"background:{C_BG};")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(20)
        build_fn(lay)
        lay.addStretch()
        scroll.setWidget(inner)
        return scroll

    # ── PÁGINA: LOGROS ────────────────────────────────────────
    def _build_logros_content(self, lay):
        from gamification_db import get_all_achievements, get_user_achievements, seed_default_achievements
        seed_default_achievements()
        all_ach = get_all_achievements()
        earned_rows = get_user_achievements(self.user_id)
        earned_names = {r[0] for r in earned_rows}

        lay.addWidget(_lbl("Mis Logros", 20, bold=True))
        lay.addWidget(_lbl(f"{len(earned_names)} / {len(all_ach)} desbloqueados", 12, color=C_TEXT_MUTED))

        grid = QGridLayout()
        grid.setSpacing(14)
        for i, (ach_id, name, desc, pts, rarity) in enumerate(all_ach):
            unlocked = name in earned_names
            card = QFrame()
            card.setFixedSize(210, 130)
            rc = RARITY_COLORS.get(rarity, C_TEXT_MUTED)
            card.setStyleSheet(
                f"QFrame{{background:{C_CARD_BG};border-radius:10px;border:{'2px solid '+rc if unlocked else '1px solid '+C_BORDER};}}"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 10, 12, 10)
            cl.setSpacing(4)
            icon = "🔒" if not unlocked else ("🏅" if rarity=="common" else ("💎" if rarity=="epic" else "⭐"))
            cl.addWidget(_lbl(icon, 20))
            cl.addWidget(_lbl(name, 11, bold=True, color=C_TEXT_DARK if unlocked else C_TEXT_MUTED))
            cl.addWidget(_lbl(desc, 9, color=C_TEXT_MUTED, wrap=True))
            cl.addWidget(_lbl(f"+{pts} pts", 10, bold=True, color=rc if unlocked else C_BORDER))
            grid.addWidget(card, i // 4, i % 4)
        container = QWidget()
        container.setLayout(grid)
        lay.addWidget(container)

    # ── PÁGINA: RETOS DEL DÍA ────────────────────────────────
    def _build_retos_content(self, lay):
        from gamification_db import get_daily_challenges
        from datetime import date
        challenges = get_daily_challenges(self.user_id)

        lay.addWidget(_lbl("Retos del Día", 20, bold=True))
        lay.addWidget(_lbl(date.today().strftime("%A %d de %B, %Y"), 12, color=C_TEXT_MUTED))

        for ch in challenges:
            card = QFrame()
            card.setStyleSheet(f"QFrame{{background:{C_CARD_BG};border-radius:12px;border:1px solid {C_BORDER};}}")
            card.setMinimumHeight(90)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(20, 14, 20, 14)
            row = QHBoxLayout()
            row.addWidget(_lbl("🎯", 28))
            info = QVBoxLayout()
            info.addWidget(_lbl(ch["title"], 14, bold=True))
            done = ch["current"] >= ch["target"]
            info.addWidget(_lbl(
                ("✅ ¡Completado!  " if done else "") + f"{ch['current']} / {ch['target']}",
                12, color=C_SUCCESS if done else C_TEXT_MUTED
            ))
            row.addLayout(info)
            row.addStretch()
            bar = QProgressBar()
            bar.setMaximum(ch["target"])
            bar.setValue(min(ch["current"], ch["target"]))
            bar.setFixedWidth(140); bar.setFixedHeight(10); bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar{{background:{C_BORDER};border-radius:5px;}}"
                f"QProgressBar::chunk{{background:{'#22c55e' if done else C_ACCENT};border-radius:5px;}}"
            )
            row.addWidget(bar)
            cl.addLayout(row)
            lay.addWidget(card)

    # ── PÁGINA: HISTORIAL ────────────────────────────────────
    def _build_historial_content(self, lay):
        from gamification_db import get_points_history, get_user_gamification_profile
        p = get_user_gamification_profile(self.user_id)
        rows = get_points_history(self.user_id)

        lay.addWidget(_lbl("Historial de Puntos", 20, bold=True))
        lay.addWidget(_lbl(f"Total acumulado: {p['total_points']} pts  •  Nivel {p['level_num']} — {p['level_name']}", 12, color=C_ACCENT))

        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels(["Fecha", "Tipo", "Puntos", "Descripción"])
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet("""
            QTableWidget{border:none;background:white;border-radius:10px;}
            QHeaderView::section{background:#f1f5f9;font-weight:bold;padding:8px;border:none;}
        """)
        type_labels = {"session": "Sesión", "achievement": "Logro", "lesson_complete": "Lección"}
        for i, (ts, ptype, pts, desc) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(str(ts)[:16]))
            table.setItem(i, 1, QTableWidgetItem(type_labels.get(ptype, ptype)))
            pts_item = QTableWidgetItem(f"+{pts}")
            pts_item.setForeground(QColor(C_SUCCESS))
            table.setItem(i, 2, pts_item)
            table.setItem(i, 3, QTableWidgetItem(desc or ""))
        lay.addWidget(table)

    # ── ACCIONES ─────────────────────────────────────────────
    def populate_sessions(self):
        self.sessions_list.clear()
        sessions = get_user_sessions(self.user_id)
        if not sessions:
            item = QListWidgetItem("  No hay sesiones anteriores.")
            item.setForeground(Qt.gray)
            self.sessions_list.addItem(item)
        else:
            for session_id, timestamp in sessions:
                text = f"  📅  Sesión del {timestamp}" if timestamp and timestamp != "None" else "  📅  Sesión sin fecha"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, session_id)
                self.sessions_list.addItem(item)

    def start_new_session(self):
        self.controller.start_new_interpreter_session(self.user_id)
        self.close()

    def view_session_history(self, item):
        session_id = item.data(Qt.UserRole)
        if session_id:
            self.controller.show_history_window(session_id)
            self.close()

    def open_learning_mode(self):
        self.btn_learning.setChecked(True)
        try:
            from learning_mode_window import LearningModeWindow
            self.learning_window = LearningModeWindow()
            self.learning_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el modo de aprendizaje:\n{str(e)}")
        self.btn_learning.setChecked(False)

    def logout(self):
        self.controller.logout()
        self.close()

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
                self._username_label.setText((row[1] or row[0]).capitalize())
        except Exception:
            pass

    def _blank_icon(self):
        px = QPixmap(32, 32); px.fill(Qt.transparent)
        return QIcon(px)


if __name__ == '__main__':
    class MockController:
        def start_new_interpreter_session(self, u): print("Nueva sesión", u)
        def show_history_window(self, s): print("Historial", s)
        def show_gamification(self, u): print("Gamif", u)
        def logout(self): print("Logout")

    app = QApplication(sys.argv)
    w = SessionsWindow(user_id=2, controller=MockController())
    w.show()
    sys.exit(app.exec_())
