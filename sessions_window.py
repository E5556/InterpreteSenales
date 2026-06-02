import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QFrame,
    QScrollArea, QProgressBar, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    _MATPLOTLIB_OK = True
except Exception:
    _MATPLOTLIB_OK = False
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

        self.btn_perfil    = SidebarBtn("👤", "Mi Perfil")
        self.btn_sessions  = SidebarBtn("📋", "Mis Sesiones")
        self.btn_new       = SidebarBtn("🎬", "Nueva Sesión")
        self.btn_learning  = SidebarBtn("🎓", "Modo Aprendizaje")
        self.btn_logros    = SidebarBtn("🏆", "Mis Logros")
        self.btn_retos     = SidebarBtn("🎯", "Retos del día")
        self.btn_historial = SidebarBtn("📜", "Historial de puntos")
        self.btn_gestos    = SidebarBtn("📊", "Mis Gestos")
        self.btn_ranking   = SidebarBtn("🏅", "Ranking")
        self.btn_eval      = SidebarBtn("📝", "Modo Evaluación")

        self._nav_btns = [
            self.btn_perfil, self.btn_sessions, self.btn_new, self.btn_learning,
            self.btn_logros, self.btn_retos, self.btn_historial,
            self.btn_gestos, self.btn_ranking, self.btn_eval,
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

        self._page_perfil    = self._build_scroll_page(self._build_perfil_content)
        self._page_sessions  = self._build_page_sessions()
        self._page_logros    = self._build_scroll_page(self._build_logros_content)
        self._page_retos     = self._build_scroll_page(self._build_retos_content)
        self._page_historial = self._build_scroll_page(self._build_historial_content)
        self._page_gestos    = self._build_scroll_page(self._build_gestos_content)
        self._page_ranking   = self._build_scroll_page(self._build_ranking_content)

        self.stack.addWidget(self._page_perfil)     # 0
        self.stack.addWidget(self._page_sessions)   # 1
        self.stack.addWidget(self._page_logros)     # 2
        self.stack.addWidget(self._page_retos)      # 3
        self.stack.addWidget(self._page_historial)  # 4
        self.stack.addWidget(self._page_gestos)     # 5
        self.stack.addWidget(self._page_ranking)    # 6

        # Conexiones sidebar
        self.btn_perfil.clicked.connect(lambda: self._go(0, self.btn_perfil))
        self.btn_sessions.clicked.connect(lambda: self._go(1, self.btn_sessions))
        self.btn_new.clicked.connect(self.start_new_session)
        self.btn_learning.clicked.connect(self.open_learning_mode)
        self.btn_logros.clicked.connect(lambda: self._go(2, self.btn_logros))
        self.btn_retos.clicked.connect(lambda: self._go(3, self.btn_retos))
        self.btn_historial.clicked.connect(lambda: self._go(4, self.btn_historial))
        self.btn_gestos.clicked.connect(lambda: self._go(5, self.btn_gestos))
        self.btn_ranking.clicked.connect(lambda: self._go(6, self.btn_ranking))
        self.btn_eval.clicked.connect(self.open_evaluation_mode)
        self.btn_logout.clicked.connect(self.logout)

        self._go(0, self.btn_perfil)  # Inicia en Mi Perfil
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
    # ── PÁGINA: PERFIL ────────────────────────────────────────
    def _build_perfil_content(self, lay):
        from gamification_db import get_user_gamification_profile, LEVELS, seed_default_achievements
        seed_default_achievements()
        p = get_user_gamification_profile(self.user_id)

        lay.addWidget(_lbl("Mi Perfil", 20, bold=True))

        # Tarjeta hero
        hero = QFrame()
        hero.setStyleSheet(f"QFrame{{background:{C_CARD_BG};border-radius:14px;border:1px solid {C_BORDER};}}")
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(24, 20, 24, 20)
        hl.setSpacing(12)

        row = QHBoxLayout()
        emoji = LEVEL_EMOJIS[min(p["level_num"], len(LEVEL_EMOJIS)-1)]
        avatar = QLabel(emoji)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(80, 80)
        avatar.setFont(QFont("Segoe UI", 34))
        avatar.setStyleSheet(f"background:{C_ACCENT};border-radius:40px;color:white;")
        row.addWidget(avatar)

        info = QVBoxLayout()
        info.setSpacing(4)
        info.addWidget(_lbl(p["username"], 22, bold=True))
        info.addWidget(_lbl(f"Nivel {p['level_num']} — {p['level_name']}", 13, color=C_ACCENT))
        info.addWidget(_lbl(f"🔥 Racha: {p['daily_streak']} día(s) consecutivo(s)", 12, color=C_TEXT_MUTED))
        row.addLayout(info)
        row.addStretch()

        pts_col = QVBoxLayout()
        pts_col.setAlignment(Qt.AlignCenter)
        pts_col.addWidget(_lbl(str(p["total_points"]), 34, bold=True, color=C_ACCENT))
        pts_col.addWidget(_lbl("puntos totales", 11, color=C_TEXT_MUTED))
        row.addLayout(pts_col)
        hl.addLayout(row)

        hl.addWidget(_lbl(f"Progreso al nivel {p['level_num']+1}", 11, color=C_TEXT_MUTED))
        bar = QProgressBar()
        bar.setValue(p["progress_pct"])
        bar.setFixedHeight(10)
        bar.setTextVisible(False)
        bar.setStyleSheet(
            f"QProgressBar{{background:{C_BORDER};border-radius:5px;}}"
            f"QProgressBar::chunk{{background:{C_ACCENT};border-radius:5px;}}"
        )
        hl.addWidget(bar)
        hl.addWidget(_lbl(f"{p['total_points']} / {p['next_level_points']} pts", 11, color=C_TEXT_MUTED))
        lay.addWidget(hero)

        # Tabla de niveles
        lvl_card = QFrame()
        lvl_card.setStyleSheet(f"QFrame{{background:{C_CARD_BG};border-radius:14px;border:1px solid {C_BORDER};}}")
        lc = QVBoxLayout(lvl_card)
        lc.setContentsMargins(24, 18, 24, 18)
        lc.setSpacing(10)
        lc.addWidget(_lbl("Sistema de Niveles", 15, bold=True))
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (num, name, req) in enumerate(LEVELS):
            em = LEVEL_EMOJIS[min(num, len(LEVEL_EMOJIS)-1)]
            active = num == p["level_num"]
            lbl = QLabel(f"{em} Nivel {num}: {name}  •  {req} pts")
            lbl.setFont(QFont("Segoe UI", 12))
            lbl.setStyleSheet(
                f"background:{C_ACCENT if active else C_BORDER};"
                f"color:{'white' if active else C_TEXT_DARK};"
                f"border-radius:8px;padding:6px 12px;"
            )
            grid.addWidget(lbl, i // 2, i % 2)
        lc.addLayout(grid)
        lay.addWidget(lvl_card)

        # Gráfica de progreso histórico
        if _MATPLOTLIB_OK:
            try:
                import sqlite3
                from config import get_database_path
                from datetime import datetime
                conn = sqlite3.connect(get_database_path())
                cur = conn.cursor()
                cur.execute("""
                    SELECT DATE(i.timestamp) as dia, COUNT(*) as total
                    FROM interpretations i
                    JOIN sessions s ON i.session_id = s.id
                    WHERE s.user_id = ?
                    GROUP BY dia ORDER BY dia ASC
                    LIMIT 30
                """, (self.user_id,))
                data = cur.fetchall()
                conn.close()

                if data and len(data) >= 1:
                    dias = [datetime.strptime(r[0], "%Y-%m-%d") for r in data]
                    totales = [r[1] for r in data]

                    fig, ax = plt.subplots(figsize=(6.5, 2.5))
                    fig.patch.set_facecolor("#ffffff")
                    ax.set_facecolor("#f8fafc")
                    ax.plot(dias, totales, color="#7c3aed", linewidth=2.2, marker="o",
                            markersize=5, markerfacecolor="#a78bfa")
                    ax.fill_between(dias, totales, alpha=0.12, color="#7c3aed")
                    ax.set_ylabel("Gestos", fontsize=9, color="#64748b")
                    ax.tick_params(labelsize=8, colors="#64748b")
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
                    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    fig.autofmt_xdate(rotation=30)
                    for spine in ax.spines.values():
                        spine.set_edgecolor("#e2e8f0")
                    ax.grid(axis="y", linestyle="--", alpha=0.4, color="#e2e8f0")
                    fig.tight_layout(pad=1.2)

                    chart_card = QFrame()
                    chart_card.setStyleSheet(f"QFrame{{background:{C_CARD_BG};border-radius:14px;border:1px solid {C_BORDER};}}")
                    cc = QVBoxLayout(chart_card)
                    cc.setContentsMargins(18, 14, 18, 14)
                    cc.addWidget(_lbl("📈 Progreso histórico (últimos 30 días)", 14, bold=True))
                    canvas = FigureCanvas(fig)
                    canvas.setFixedHeight(220)
                    cc.addWidget(canvas)
                    lay.addWidget(chart_card)
                    plt.close(fig)
            except Exception:
                pass

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
        from gamification_db import get_daily_challenges, get_weekly_challenge
        from datetime import date
        challenges = get_daily_challenges(self.user_id)
        weekly = get_weekly_challenge(self.user_id)

        lay.addWidget(_lbl("Retos del Día", 20, bold=True))
        lay.addWidget(_lbl(date.today().strftime("%A %d de %B, %Y"), 12, color=C_TEXT_MUTED))

        def _challenge_card(ch, icon="🎯", accent_color=C_ACCENT):
            card = QFrame()
            card.setStyleSheet(f"QFrame{{background:{C_CARD_BG};border-radius:12px;border:1px solid {C_BORDER};}}")
            card.setMinimumHeight(90)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(20, 14, 20, 14)
            row = QHBoxLayout()
            row.addWidget(_lbl(icon, 28))
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
            bar.setMaximum(max(ch["target"], 1))
            bar.setValue(min(ch["current"], ch["target"]))
            bar.setFixedWidth(140); bar.setFixedHeight(10); bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar{{background:{C_BORDER};border-radius:5px;}}"
                f"QProgressBar::chunk{{background:{'#22c55e' if done else accent_color};border-radius:5px;}}"
            )
            row.addWidget(bar)
            cl.addLayout(row)
            return card

        for ch in challenges:
            lay.addWidget(_challenge_card(ch))

        # Reto semanal
        lay.addSpacing(10)
        lay.addWidget(_lbl("🗓️  Reto de la Semana", 16, bold=True))
        lay.addWidget(_lbl("Se renueva cada lunes", 11, color=C_TEXT_MUTED))
        lay.addWidget(_challenge_card(weekly, icon="🗓️", accent_color="#f59e0b"))

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

    # ── PÁGINA: MIS GESTOS ───────────────────────────────────
    def _build_gestos_content(self, lay):
        import sqlite3
        from config import get_database_path

        lay.addWidget(_lbl("Mis Gestos", 20, bold=True))
        lay.addWidget(_lbl("Precisión promedio y frecuencia de cada seña reconocida", 12, color=C_TEXT_MUTED))

        try:
            conn = sqlite3.connect(get_database_path())
            cur = conn.cursor()
            cur.execute("""
                SELECT word_detected,
                       COUNT(*) as total,
                       AVG(confidence_score)*100 as precision_prom,
                       MAX(confidence_score)*100 as mejor,
                       MIN(confidence_score)*100 as peor
                FROM interpretations i
                JOIN sessions s ON i.session_id = s.id
                WHERE s.user_id = ? AND confidence_score IS NOT NULL
                GROUP BY word_detected
                ORDER BY precision_prom DESC
            """, (self.user_id,))
            rows = cur.fetchall()
            conn.close()
        except Exception:
            rows = []

        if not rows:
            lay.addWidget(_lbl("Aún no tienes interpretaciones registradas.\nInicia una sesión para ver tu progreso aquí.", 13, color=C_TEXT_MUTED, wrap=True))
            return

        GESTURE_COLORS = {"HOLA": "#7c3aed", "ADIOS": "#3b82f6", "ADULTO": "#f59e0b",
                          "ANCIANO": "#22c55e", "GATO": "#ef4444"}

        for word, total, prom, mejor, peor in rows:
            prom = prom or 0.0
            mejor = mejor or 0.0
            peor = peor or 0.0
            color = GESTURE_COLORS.get(word, C_ACCENT)

            card = QFrame()
            card.setStyleSheet(f"QFrame{{background:{C_CARD_BG};border-radius:14px;border:1px solid {C_BORDER};}}")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(22, 16, 22, 16)
            cl.setSpacing(8)

            header = QHBoxLayout()
            header.addWidget(_lbl(word, 16, bold=True, color=color))
            header.addStretch()
            header.addWidget(_lbl(f"{int(total)} veces", 12, color=C_TEXT_MUTED))
            cl.addLayout(header)

            bar_row = QHBoxLayout()
            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setValue(int(prom))
            bar.setFixedHeight(14)
            bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar{{background:{C_BORDER};border-radius:7px;}}"
                f"QProgressBar::chunk{{background:{color};border-radius:7px;}}"
            )
            bar_row.addWidget(bar)
            bar_row.addWidget(_lbl(f"  {prom:.1f}%", 13, bold=True, color=color))
            cl.addLayout(bar_row)

            stats_row = QHBoxLayout()
            stats_row.addWidget(_lbl(f"Mejor: {mejor:.1f}%", 11, color=C_SUCCESS))
            stats_row.addWidget(_lbl(f"  Peor: {peor:.1f}%", 11, color=C_DANGER))
            stats_row.addStretch()
            cl.addLayout(stats_row)

            lay.addWidget(card)

    # ── PÁGINA: RANKING ──────────────────────────────────────
    def _build_ranking_content(self, lay):
        import sqlite3
        from config import get_database_path

        lay.addWidget(_lbl("🏅 Ranking de Usuarios", 20, bold=True))
        lay.addWidget(_lbl("Clasificación general por puntos acumulados", 12, color=C_TEXT_MUTED))

        try:
            conn = sqlite3.connect(get_database_path())
            cur = conn.cursor()
            cur.execute("""
                SELECT u.username, up.total_points, up.current_level, up.daily_streak,
                       COUNT(i.id) as total_gestos
                FROM users u
                JOIN user_points up ON u.id = up.user_id
                LEFT JOIN sessions s ON u.id = s.user_id
                LEFT JOIN interpretations i ON s.id = i.session_id
                WHERE u.is_active = 1 AND u.role = 'user'
                GROUP BY u.id
                ORDER BY up.total_points DESC
            """)
            rows = cur.fetchall()
            # También incluir el usuario actual aunque sea admin
            cur.execute("""
                SELECT username FROM users WHERE id=?
            """, (self.user_id,))
            me_row = cur.fetchone()
            me_username = me_row[0] if me_row else ""
            conn.close()
        except Exception:
            rows = []
            me_username = ""

        if not rows:
            lay.addWidget(_lbl("Aún no hay datos de ranking disponibles.", 13, color=C_TEXT_MUTED))
            return

        MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
        LEVEL_NAMES = {1: "Principiante", 2: "Aprendiz", 3: "Comunicador",
                       4: "Intérprete", 5: "Experto", 6: "Maestro"}

        for pos, (username, pts, level, streak, gestos) in enumerate(rows, start=1):
            medal = MEDALS.get(pos, f"#{pos}")
            is_me = (username == me_username)

            card = QFrame()
            border = f"2px solid {C_ACCENT}" if is_me else f"1px solid {C_BORDER}"
            bg = "#f5f3ff" if is_me else C_CARD_BG
            card.setStyleSheet(f"QFrame{{background:{bg};border-radius:12px;border:{border};}}")
            cl = QHBoxLayout(card)
            cl.setContentsMargins(18, 12, 18, 12)
            cl.setSpacing(16)

            cl.addWidget(_lbl(medal, 22))
            info = QVBoxLayout()
            name_text = f"{username}  {'(Tú)' if is_me else ''}"
            info.addWidget(_lbl(name_text, 14, bold=True, color=C_ACCENT if is_me else C_TEXT_DARK))
            info.addWidget(_lbl(f"Nivel {level} — {LEVEL_NAMES.get(level, '')}  •  🔥 {streak} días", 11, color=C_TEXT_MUTED))
            cl.addLayout(info)
            cl.addStretch()

            stats = QVBoxLayout()
            stats.setAlignment(Qt.AlignRight)
            stats.addWidget(_lbl(f"{pts} pts", 16, bold=True, color=C_ACCENT))
            stats.addWidget(_lbl(f"{gestos} gestos", 11, color=C_TEXT_MUTED))
            cl.addLayout(stats)

            lay.addWidget(card)

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

    def open_evaluation_mode(self):
        self.btn_eval.setChecked(True)
        try:
            from evaluation_mode_window import EvaluationModeWindow
            self._eval_window = EvaluationModeWindow(self.user_id, self.controller)
            self._eval_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el modo evaluación:\n{str(e)}")
        self.btn_eval.setChecked(False)

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
        # Sincronizar logros con datos históricos reales (en background)
        try:
            import threading
            from gamification_db import sync_user_gamification
            threading.Thread(
                target=sync_user_gamification, args=(self.user_id,), daemon=True
            ).start()
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
