import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QProgressBar, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    _MPL = True
except Exception:
    _MPL = False

C_BG     = "#f8fafc"
C_CARD   = "#ffffff"
C_ACCENT = "#7c3aed"
C_BORDER = "#e2e8f0"
C_DARK   = "#1e293b"
C_MUTED  = "#64748b"
C_SUCCESS= "#22c55e"
C_DANGER = "#ef4444"

GESTURE_COLORS = ["#7c3aed", "#3b82f6", "#22c55e", "#f59e0b", "#ef4444"]
LEVEL_NAMES = {1:"Principiante", 2:"Aprendiz", 3:"Comunicador",
               4:"Intérprete", 5:"Experto", 6:"Maestro"}


def _lbl(text, size=13, bold=False, color=C_DARK, wrap=False, align=Qt.AlignLeft):
    l = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet(f"color:{color}; background:transparent;")
    l.setWordWrap(wrap)
    l.setAlignment(align)
    return l


class UserProfileAdminWindow(QWidget):
    def __init__(self, user_id, username, parent=None):
        super().__init__(parent)
        self.user_id  = user_id
        self.username = username
        self.setWindowTitle(f"Perfil de {username}")
        self.setGeometry(250, 100, 780, 620)
        self.setMinimumSize(680, 500)
        self.setStyleSheet(f"background:{C_BG};")
        self.setWindowIcon(self._blank_icon())
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background:{C_BG};")

        inner = QWidget()
        inner.setStyleSheet(f"background:{C_BG};")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(18)

        data = self._fetch_data()

        # ── Encabezado ────────────────────────────────────────────
        hero = QFrame()
        hero.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:14px;border:1px solid {C_BORDER};}}")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(24, 20, 24, 20)
        hl.setSpacing(20)

        avatar = QLabel(data["avatar"] or "👤")
        avatar.setFont(QFont("Segoe UI", 36))
        avatar.setFixedSize(72, 72)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"background:{C_ACCENT};border-radius:36px;")
        hl.addWidget(avatar)

        info = QVBoxLayout()
        info.setSpacing(2)
        info.addWidget(_lbl(data["full_name"] or self.username, 20, bold=True))
        info.addWidget(_lbl(f"@{self.username}  •  {data['email'] or '—'}", 11, color=C_MUTED))
        info.addWidget(_lbl(
            f"Nivel {data['level']} — {LEVEL_NAMES.get(data['level'], '—')}  •  "
            f"{data['total_points']} pts  •  🔥 {data['streak']} días",
            12, color=C_ACCENT
        ))
        hl.addLayout(info)
        hl.addStretch()

        status_lbl = QLabel("✅ Activo" if data["is_active"] else "⛔ Inactivo")
        status_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        status_lbl.setStyleSheet(
            f"color:{C_SUCCESS if data['is_active'] else C_DANGER};"
            f"background:{'#dcfce7' if data['is_active'] else '#fee2e2'};"
            f"border-radius:8px;padding:4px 12px;"
        )
        hl.addWidget(status_lbl)
        lay.addWidget(hero)

        # ── Métricas rápidas ──────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(12)
        metrics = [
            ("📅 Sesiones",        str(data["sesiones"])),
            ("✋ Gestos totales",   str(data["gestos"])),
            ("🎯 Precisión prom.", f"{data['precision']:.1f}%"),
            ("📝 Evaluaciones",    str(data["evaluaciones"])),
            ("⭐ Mejor eval.",     f"{data['mejor_eval']}%"),
            ("🗓️ Último acceso",   str(data["last_login"])[:10] if data["last_login"] else "—"),
        ]
        for i, (title, val) in enumerate(metrics):
            card = QFrame()
            card.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:10px;border:1px solid {C_BORDER};}}")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 10, 14, 10)
            cl.addWidget(_lbl(title, 10, color=C_MUTED))
            cl.addWidget(_lbl(val, 20, bold=True, color=C_ACCENT))
            grid.addWidget(card, i // 3, i % 3)
        grid_w = QWidget()
        grid_w.setStyleSheet("background:transparent;")
        grid_w.setLayout(grid)
        lay.addWidget(grid_w)

        # ── Gestos más practicados ────────────────────────────────
        if data["top_gestos"]:
            lay.addWidget(_lbl("✋ Gestos practicados", 14, bold=True))
            for i, (word, total, avg_conf) in enumerate(data["top_gestos"]):
                pct = int((avg_conf or 0) * 100)
                color = GESTURE_COLORS[i % len(GESTURE_COLORS)]
                row_w = QFrame()
                row_w.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:10px;border:1px solid {C_BORDER};}}")
                rl = QVBoxLayout(row_w)
                rl.setContentsMargins(16, 10, 16, 10)
                rl.setSpacing(4)
                hr = QHBoxLayout()
                hr.addWidget(_lbl(word, 13, bold=True, color=color))
                hr.addStretch()
                hr.addWidget(_lbl(f"{total} veces  •  {pct}% precisión", 11, color=C_MUTED))
                rl.addLayout(hr)
                bar = QProgressBar()
                bar.setMaximum(max(1, data["top_gestos"][0][1]))
                bar.setValue(total)
                bar.setFixedHeight(8)
                bar.setTextVisible(False)
                bar.setStyleSheet(
                    f"QProgressBar{{background:{C_BORDER};border-radius:4px;}}"
                    f"QProgressBar::chunk{{background:{color};border-radius:4px;}}"
                )
                rl.addWidget(bar)
                lay.addWidget(row_w)

        # ── Logros desbloqueados ──────────────────────────────────
        if data["logros"]:
            lay.addWidget(_lbl(f"🏆 Logros ({len(data['logros'])} desbloqueados)", 14, bold=True))
            logros_row = QHBoxLayout()
            logros_row.setSpacing(8)
            for name, rarity in data["logros"][:6]:
                chip = QLabel(f"🏅 {name}")
                chip.setFont(QFont("Segoe UI", 10))
                rarity_colors = {"common":"#64748b","uncommon":"#0891b2","rare":"#3b82f6","epic":"#8b5cf6","legendary":"#f59e0b"}
                rc = rarity_colors.get(rarity, C_MUTED)
                chip.setStyleSheet(f"background:#f8f9ff;color:{rc};border:1px solid {rc};border-radius:6px;padding:3px 8px;")
                logros_row.addWidget(chip)
            logros_row.addStretch()
            lay.addLayout(logros_row)

        # ── Gráfica actividad ─────────────────────────────────────
        if _MPL and len(data["actividad"]) >= 2:
            try:
                from datetime import datetime as dt
                dias   = [dt.strptime(r[0], "%Y-%m-%d") for r in data["actividad"]]
                totals = [r[1] for r in data["actividad"]]
                import matplotlib.dates as mdates

                fig, ax = plt.subplots(figsize=(6.5, 2.2))
                fig.patch.set_facecolor("#ffffff")
                ax.set_facecolor("#f8fafc")
                ax.bar(dias, totals, color="#7c3aed", alpha=0.8, width=0.6)
                ax.set_ylabel("Gestos", fontsize=8, color="#64748b")
                ax.tick_params(labelsize=7, colors="#64748b")
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                for spine in ax.spines.values():
                    spine.set_edgecolor("#e2e8f0")
                ax.grid(axis="y", linestyle="--", alpha=0.3)
                fig.autofmt_xdate(rotation=25)
                fig.tight_layout(pad=1.0)

                chart_card = QFrame()
                chart_card.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:12px;border:1px solid {C_BORDER};}}")
                cc = QVBoxLayout(chart_card)
                cc.setContentsMargins(16, 12, 16, 10)
                cc.addWidget(_lbl("📈 Actividad reciente", 13, bold=True))
                canvas = FigureCanvas(fig)
                canvas.setFixedHeight(180)
                cc.addWidget(canvas)
                lay.addWidget(chart_card)
                plt.close(fig)
            except Exception:
                pass

        lay.addStretch()
        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _fetch_data(self):
        try:
            from config import get_database_path
            conn = sqlite3.connect(get_database_path())
            cur = conn.cursor()

            cur.execute("""SELECT first_name, last_name, email, profile_picture_url,
                                  is_active, last_login FROM users WHERE id=?""", (self.user_id,))
            u = cur.fetchone() or (None,)*6
            full_name = " ".join(filter(None, [u[0], u[1]])) or None

            cur.execute("SELECT total_points, current_level, daily_streak FROM user_points WHERE user_id=?", (self.user_id,))
            pts_row = cur.fetchone() or (0, 1, 0)

            cur.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (self.user_id,))
            sesiones = cur.fetchone()[0] or 0

            cur.execute("""SELECT COUNT(*) FROM interpretations i
                           JOIN sessions s ON i.session_id=s.id WHERE s.user_id=?""", (self.user_id,))
            gestos = cur.fetchone()[0] or 0

            cur.execute("""SELECT AVG(confidence_score) FROM interpretations i
                           JOIN sessions s ON i.session_id=s.id
                           WHERE s.user_id=? AND confidence_score IS NOT NULL""", (self.user_id,))
            r = cur.fetchone()[0]
            precision = (r or 0) * 100

            cur.execute("""SELECT word_detected, COUNT(*) as t, AVG(confidence_score)
                           FROM interpretations i JOIN sessions s ON i.session_id=s.id
                           WHERE s.user_id=? AND word_detected IS NOT NULL
                           GROUP BY word_detected ORDER BY t DESC LIMIT 5""", (self.user_id,))
            top_gestos = cur.fetchall()

            cur.execute("""SELECT a.achievement_name, a.rarity FROM user_achievements ua
                           JOIN achievements a ON ua.achievement_id=a.id
                           WHERE ua.user_id=? ORDER BY ua.earned_date DESC""", (self.user_id,))
            logros = cur.fetchall()

            try:
                cur.execute("SELECT COUNT(*), MAX(score_pct) FROM evaluation_results WHERE user_id=?", (self.user_id,))
                er = cur.fetchone()
                evaluaciones = er[0] or 0
                mejor_eval   = er[1] or 0
            except Exception:
                evaluaciones, mejor_eval = 0, 0

            cur.execute("""SELECT DATE(i.timestamp) as dia, COUNT(*) FROM interpretations i
                           JOIN sessions s ON i.session_id=s.id WHERE s.user_id=?
                           GROUP BY dia ORDER BY dia DESC LIMIT 20""", (self.user_id,))
            actividad = list(reversed(cur.fetchall()))
            conn.close()

            return {
                "full_name": full_name, "email": u[2], "avatar": u[3],
                "is_active": bool(u[4]), "last_login": u[5],
                "total_points": pts_row[0] or 0, "level": pts_row[1] or 1,
                "streak": pts_row[2] or 0,
                "sesiones": sesiones, "gestos": gestos, "precision": precision,
                "top_gestos": top_gestos, "logros": logros,
                "evaluaciones": evaluaciones, "mejor_eval": mejor_eval,
                "actividad": actividad,
            }
        except Exception:
            return {
                "full_name": None, "email": None, "avatar": None,
                "is_active": True, "last_login": None,
                "total_points": 0, "level": 1, "streak": 0,
                "sesiones": 0, "gestos": 0, "precision": 0,
                "top_gestos": [], "logros": [], "evaluaciones": 0,
                "mejor_eval": 0, "actividad": [],
            }

    def _blank_icon(self):
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        return QIcon(px)
