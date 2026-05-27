from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor

# Paleta (misma que admin_panel.py)
C_SIDEBAR_BG  = "#1e1e2e"
C_ACCENT      = "#7c3aed"
C_ACCENT_LIGHT= "#a78bfa"
C_BG          = "#f8fafc"
C_CARD_BG     = "#ffffff"
C_TEXT_DARK   = "#1e293b"
C_TEXT_MUTED  = "#64748b"
C_SUCCESS     = "#22c55e"
C_WARNING     = "#f59e0b"
C_DANGER      = "#ef4444"
C_BORDER      = "#e2e8f0"

RARITY_COLORS = {
    "common": "#64748b",
    "rare":   "#3b82f6",
    "epic":   "#8b5cf6",
    "legendary": "#f59e0b",
}

LEVEL_EMOJIS = ["", "🌱", "📚", "💬", "🎯", "⭐", "🏆"]


def _label(text, size=13, bold=False, color=C_TEXT_DARK, wrap=False):
    lbl = QLabel(text)
    font = QFont("Segoe UI", size)
    font.setBold(bold)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def _card(parent_layout, min_height=0):
    card = QFrame()
    card.setObjectName("card")
    card.setStyleSheet(
        f"QFrame#card {{ background: {C_CARD_BG}; border-radius: 12px; border: 1px solid {C_BORDER}; }}"
    )
    if min_height:
        card.setMinimumHeight(min_height)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(10)
    parent_layout.addWidget(card)
    return layout


class SidebarBtn(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 16px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: rgba(124,58,237,0.15);
                color: {C_ACCENT_LIGHT};
            }}
            QPushButton:checked {{
                background: {C_ACCENT};
                color: white;
                font-weight: bold;
            }}
        """)


class GamificationWindow(QWidget):
    def __init__(self, user_id, controller=None):
        super().__init__()
        self.user_id = user_id
        self.controller = controller
        self.setWindowTitle("🏆 Mis Logros y Progreso")
        self.setGeometry(200, 100, 1000, 680)
        self.setMinimumSize(900, 600)

        # Seed logros si no existen
        from gamification_db import seed_default_achievements
        seed_default_achievements()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet(f"background: {C_SIDEBAR_BG};")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 24, 12, 24)
        sb_layout.setSpacing(6)

        sb_title = QLabel("🏆  Gamificación")
        sb_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        sb_title.setStyleSheet(f"color: white; padding-bottom: 12px;")
        sb_layout.addWidget(sb_title)

        self.btn_profile    = SidebarBtn("👤  Mi Perfil")
        self.btn_achievements = SidebarBtn("🎖️  Logros")
        self.btn_challenges = SidebarBtn("🎯  Retos del día")
        self.btn_history    = SidebarBtn("📜  Historial")
        self._sidebar_btns = [self.btn_profile, self.btn_achievements, self.btn_challenges, self.btn_history]
        for btn in self._sidebar_btns:
            sb_layout.addWidget(btn)

        sb_layout.addStretch()
        root.addWidget(sidebar)

        # ── CONTENT AREA ─────────────────────────────────────
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setFrameShape(QFrame.NoFrame)
        self.content_area.setStyleSheet(f"background: {C_BG};")
        root.addWidget(self.content_area)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background: {C_BG};")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(32, 32, 32, 32)
        self.content_layout.setSpacing(20)
        self.content_area.setWidget(self.content_widget)

        # Connections
        self.btn_profile.clicked.connect(lambda: self._show_section("profile"))
        self.btn_achievements.clicked.connect(lambda: self._show_section("achievements"))
        self.btn_challenges.clicked.connect(lambda: self._show_section("challenges"))
        self.btn_history.clicked.connect(lambda: self._show_section("history"))

        self._show_section("profile")

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_section(self, section):
        for btn in self._sidebar_btns:
            btn.setChecked(False)
        btn_map = {
            "profile": self.btn_profile,
            "achievements": self.btn_achievements,
            "challenges": self.btn_challenges,
            "history": self.btn_history,
        }
        btn_map[section].setChecked(True)
        self._clear_content()
        getattr(self, f"_build_{section}")()

    # ── PERFIL ────────────────────────────────────────────────
    def _build_profile(self):
        from gamification_db import get_user_gamification_profile
        p = get_user_gamification_profile(self.user_id)

        self.content_layout.addWidget(_label("Mi Perfil", 20, bold=True))

        # Avatar + nombre
        hero = _card(self.content_layout)
        row = QHBoxLayout()
        emoji = LEVEL_EMOJIS[min(p["level_num"], len(LEVEL_EMOJIS) - 1)]
        avatar = _label(emoji, size=48)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(90, 90)
        avatar.setStyleSheet(
            f"background: {C_ACCENT}; border-radius: 45px; color: white; font-size: 36px;"
        )
        row.addWidget(avatar)

        info = QVBoxLayout()
        info.addWidget(_label(p["username"], 22, bold=True))
        info.addWidget(_label(f"Nivel {p['level_num']} — {p['level_name']}", 13, color=C_ACCENT))
        info.addWidget(_label(f"🔥 Racha: {p['daily_streak']} día(s) consecutivo(s)", 12, color=C_TEXT_MUTED))
        row.addLayout(info)
        row.addStretch()

        pts_box = QVBoxLayout()
        pts_box.setAlignment(Qt.AlignCenter)
        pts_box.addWidget(_label(str(p["total_points"]), 32, bold=True, color=C_ACCENT))
        pts_box.addWidget(_label("puntos totales", 11, color=C_TEXT_MUTED))
        row.addLayout(pts_box)
        hero.addLayout(row)

        # Barra de progreso al siguiente nivel
        hero.addWidget(_label(f"Progreso al nivel {p['level_num'] + 1}", 12, color=C_TEXT_MUTED))
        bar = QProgressBar()
        bar.setValue(p["progress_pct"])
        bar.setFixedHeight(10)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: {C_BORDER}; border-radius: 5px; }}
            QProgressBar::chunk {{ background: {C_ACCENT}; border-radius: 5px; }}
        """)
        hero.addWidget(bar)
        hero.addWidget(_label(f"{p['total_points']} / {p['next_level_points']} pts", 11, color=C_TEXT_MUTED))

        # Tabla de niveles
        lvl_card = _card(self.content_layout)
        lvl_card.addWidget(_label("Sistema de Niveles", 15, bold=True))
        from gamification_db import LEVELS
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (num, name, req) in enumerate(LEVELS):
            em = LEVEL_EMOJIS[min(num, len(LEVEL_EMOJIS) - 1)]
            active = num == p["level_num"]
            bg = C_ACCENT if active else C_BORDER
            col = "white" if active else C_TEXT_DARK
            lbl = QLabel(f"{em} Nivel {num}: {name}  •  {req} pts")
            lbl.setFont(QFont("Segoe UI", 12))
            lbl.setStyleSheet(
                f"background: {bg}; color: {col}; border-radius: 8px; padding: 6px 12px;"
            )
            grid.addWidget(lbl, i // 2, i % 2)
        lvl_card.addLayout(grid)

        self.content_layout.addStretch()

    # ── LOGROS ────────────────────────────────────────────────
    def _build_achievements(self):
        from gamification_db import get_all_achievements, get_user_achievements
        all_ach = get_all_achievements()
        earned_rows = get_user_achievements(self.user_id)
        earned_names = {r[0] for r in earned_rows}

        self.content_layout.addWidget(_label("Logros", 20, bold=True))
        self.content_layout.addWidget(
            _label(f"{len(earned_names)} / {len(all_ach)} desbloqueados", 13, color=C_TEXT_MUTED)
        )

        grid = QGridLayout()
        grid.setSpacing(14)
        for i, (ach_id, name, desc, pts, rarity) in enumerate(all_ach):
            unlocked = name in earned_names
            card = QFrame()
            card.setFixedSize(200, 130)
            rarity_color = RARITY_COLORS.get(rarity, C_TEXT_MUTED)
            if unlocked:
                card.setStyleSheet(
                    f"QFrame {{ background: {C_CARD_BG}; border-radius: 10px; "
                    f"border: 2px solid {rarity_color}; }}"
                )
            else:
                card.setStyleSheet(
                    f"QFrame {{ background: #f1f5f9; border-radius: 10px; "
                    f"border: 1px solid {C_BORDER}; }}"
                )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 10, 12, 10)
            cl.setSpacing(4)

            icon = "🔒" if not unlocked else ("🏅" if rarity == "common" else ("💎" if rarity == "epic" else "⭐"))
            cl.addWidget(_label(icon, 22))
            cl.addWidget(_label(name, 11, bold=True,
                                color=C_TEXT_DARK if unlocked else C_TEXT_MUTED))
            cl.addWidget(_label(desc, 9, color=C_TEXT_MUTED, wrap=True))
            cl.addWidget(_label(f"+{pts} pts", 10, bold=True,
                                color=rarity_color if unlocked else C_BORDER))

            grid.addWidget(card, i // 4, i % 4)

        container = QWidget()
        container.setLayout(grid)
        self.content_layout.addWidget(container)
        self.content_layout.addStretch()

    # ── RETOS DEL DÍA ─────────────────────────────────────────
    def _build_challenges(self):
        from gamification_db import get_daily_challenges
        challenges = get_daily_challenges(self.user_id)

        self.content_layout.addWidget(_label("Retos del Día", 20, bold=True))
        from datetime import date
        self.content_layout.addWidget(
            _label(date.today().strftime("%A %d de %B, %Y"), 13, color=C_TEXT_MUTED)
        )

        for ch in challenges:
            cl = _card(self.content_layout, min_height=90)
            row = QHBoxLayout()

            icon = "🎯" if ch["type"] == "gestures" else ("📋" if ch["type"] == "sessions" else "🎯")
            row.addWidget(_label(icon, 28))

            info = QVBoxLayout()
            info.addWidget(_label(ch["title"], 14, bold=True))
            progress_text = f"{ch['current']} / {ch['target']}"
            done = ch["current"] >= ch["target"]
            status_color = C_SUCCESS if done else C_TEXT_MUTED
            info.addWidget(_label(("✅ ¡Completado! " if done else "") + progress_text,
                                  12, color=status_color))
            row.addLayout(info)
            row.addStretch()

            bar = QProgressBar()
            bar.setMaximum(ch["target"])
            bar.setValue(min(ch["current"], ch["target"]))
            bar.setFixedWidth(140)
            bar.setFixedHeight(10)
            bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar {{ background:{C_BORDER}; border-radius:5px; }}"
                f"QProgressBar::chunk {{ background:{'#22c55e' if done else C_ACCENT}; border-radius:5px; }}"
            )
            row.addWidget(bar)
            cl.addLayout(row)

        self.content_layout.addStretch()

    # ── HISTORIAL ─────────────────────────────────────────────
    def _build_history(self):
        from gamification_db import get_points_history
        rows = get_points_history(self.user_id)

        self.content_layout.addWidget(_label("Historial de Puntos", 20, bold=True))

        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels(["Fecha", "Tipo", "Puntos", "Descripción"])
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet("""
            QTableWidget { border: none; background: white; border-radius: 10px; }
            QHeaderView::section { background: #f1f5f9; font-weight: bold; padding: 8px; border: none; }
        """)

        type_labels = {
            "session": "Sesión",
            "achievement": "Logro",
            "lesson_complete": "Lección",
        }
        for i, (ts, ptype, pts, desc) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(str(ts)[:16]))
            table.setItem(i, 1, QTableWidgetItem(type_labels.get(ptype, ptype)))
            pts_item = QTableWidgetItem(f"+{pts}")
            pts_item.setForeground(QColor(C_SUCCESS))
            table.setItem(i, 2, pts_item)
            table.setItem(i, 3, QTableWidgetItem(desc or ""))

        self.content_layout.addWidget(table)
        self.content_layout.addStretch()
