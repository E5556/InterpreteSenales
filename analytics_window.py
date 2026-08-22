import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
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


def _lbl(text, size=13, bold=False, color=C_DARK, align=Qt.AlignLeft, wrap=False):
    l = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet(f"color:{color}; background:transparent;")
    l.setAlignment(align)
    l.setWordWrap(wrap)
    return l


def _card(parent_lay, title, value, subtitle="", accent=C_ACCENT):
    card = QFrame()
    card.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:12px;border:1px solid {C_BORDER};}}")
    cl = QVBoxLayout(card)
    cl.setContentsMargins(18, 14, 18, 14)
    cl.setSpacing(2)
    cl.addWidget(_lbl(title, 11, color=C_MUTED))
    cl.addWidget(_lbl(str(value), 28, bold=True, color=accent))
    if subtitle:
        cl.addWidget(_lbl(subtitle, 10, color=C_MUTED))
    parent_lay.addWidget(card)
    return card


class AnalyticsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle("Analíticas Globales — Admin")
        self.setGeometry(200, 80, 900, 680)
        self.setMinimumSize(780, 560)
        self.setStyleSheet(f"background:{C_BG};")
        self.setWindowIcon(self._blank_icon())
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background:{C_BG};")
        scroll.setGeometry(0, 0, self.width(), self.height())

        inner = QWidget()
        inner.setStyleSheet(f"background:{C_BG};")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(36, 28, 36, 28)
        lay.setSpacing(20)

        lay.addWidget(_lbl("🔍 Analíticas Globales", 22, bold=True))
        lay.addWidget(_lbl("Vista consolidada del sistema para el administrador", 12, color=C_MUTED))

        data = self._fetch_data()

        # ── Tarjetas de métricas rápidas ──────────────────────────
        grid = QGridLayout()
        grid.setSpacing(14)

        metrics = [
            ("👥 Usuarios activos",    data["usuarios_activos"],   "de " + str(data["usuarios_total"]) + " totales"),
            ("📅 Sesiones totales",    data["sesiones_total"],     "en todo el sistema"),
            ("✋ Gestos interpretados", data["gestos_total"],       "interpretaciones reales"),
            ("🎯 Precisión promedio",  f"{data['precision_prom']:.1f}%", "sobre sesiones con datos"),
            ("🏆 Evaluaciones hechas", data["evaluaciones_total"], "en modo evaluación"),
            ("⭐ Mejor evaluación",    f"{data['mejor_eval']}%",   "puntaje más alto"),
        ]
        for i, (title, val, sub) in enumerate(metrics):
            card = QFrame()
            card.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:12px;border:1px solid {C_BORDER};}}")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 12, 16, 12)
            cl.setSpacing(2)
            cl.addWidget(_lbl(title, 11, color=C_MUTED))
            cl.addWidget(_lbl(str(val), 26, bold=True, color=C_ACCENT))
            cl.addWidget(_lbl(sub, 10, color=C_MUTED))
            grid.addWidget(card, i // 3, i % 3)

        grid_w = QWidget()
        grid_w.setStyleSheet("background:transparent;")
        grid_w.setLayout(grid)
        lay.addWidget(grid_w)

        # ── Usuarios más activos ──────────────────────────────────
        lay.addWidget(_lbl("👑 Usuarios más activos", 15, bold=True))
        for rank, (username, gestos, sesiones, pts) in enumerate(data["top_users"], 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
            row = QFrame()
            row.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:10px;border:1px solid {C_BORDER};}}")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(16, 10, 16, 10)
            rl.addWidget(_lbl(medal, 18))
            rl.addWidget(_lbl(username, 13, bold=True))
            rl.addStretch()
            rl.addWidget(_lbl(f"✋ {gestos} gestos", 11, color=C_MUTED))
            rl.addWidget(_lbl(f"  📅 {sesiones} sesiones", 11, color=C_MUTED))
            rl.addWidget(_lbl(f"  ⭐ {pts} pts", 11, bold=True, color=C_ACCENT))
            lay.addWidget(row)

        # ── Gestos más reconocidos ────────────────────────────────
        lay.addWidget(_lbl("✋ Gestos más reconocidos (sistema)", 15, bold=True))
        COLORS = ["#7c3aed", "#3b82f6", "#22c55e", "#f59e0b", "#ef4444"]
        for i, (word, total, avg_conf) in enumerate(data["top_gestos"]):
            pct = int((avg_conf or 0) * 100)
            color = COLORS[i % len(COLORS)]
            card = QFrame()
            card.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:10px;border:1px solid {C_BORDER};}}")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 10, 16, 10)
            cl.setSpacing(6)
            hrow = QHBoxLayout()
            hrow.addWidget(_lbl(word, 14, bold=True, color=color))
            hrow.addStretch()
            hrow.addWidget(_lbl(f"{total} veces  •  {pct}% precisión", 11, color=C_MUTED))
            cl.addLayout(hrow)
            from PyQt5.QtWidgets import QProgressBar
            bar = QProgressBar()
            bar.setMaximum(max(1, data["top_gestos"][0][1]))
            bar.setValue(total)
            bar.setFixedHeight(8)
            bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar{{background:{C_BORDER};border-radius:4px;}}"
                f"QProgressBar::chunk{{background:{color};border-radius:4px;}}"
            )
            cl.addWidget(bar)
            lay.addWidget(card)

        # ── Gráfica de actividad diaria ───────────────────────────
        if _MPL and data["actividad_diaria"]:
            try:
                from datetime import datetime as dt
                dias   = [dt.strptime(r[0], "%Y-%m-%d") for r in data["actividad_diaria"]]
                totals = [r[1] for r in data["actividad_diaria"]]

                fig, ax = plt.subplots(figsize=(7, 2.8))
                fig.patch.set_facecolor("#ffffff")
                ax.set_facecolor("#f8fafc")
                ax.bar(dias, totals, color="#7c3aed", alpha=0.8, width=0.6)
                ax.set_ylabel("Gestos", fontsize=9, color="#64748b")
                ax.tick_params(labelsize=8, colors="#64748b")
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                for spine in ax.spines.values():
                    spine.set_edgecolor("#e2e8f0")
                ax.grid(axis="y", linestyle="--", alpha=0.4, color="#e2e8f0")
                fig.autofmt_xdate(rotation=30)
                fig.tight_layout(pad=1.2)

                chart_card = QFrame()
                chart_card.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:14px;border:1px solid {C_BORDER};}}")
                cc = QVBoxLayout(chart_card)
                cc.setContentsMargins(18, 14, 18, 14)
                cc.addWidget(_lbl("📈 Actividad diaria del sistema (últimos 30 días)", 14, bold=True))
                canvas = FigureCanvas(fig)
                canvas.setFixedHeight(200)
                cc.addWidget(canvas)
                lay.addWidget(chart_card)
                plt.close(fig)
            except Exception:
                pass

        # ── Evaluaciones globales ────────────────────────────────
        if data["eval_por_usuario"]:
            lay.addWidget(_lbl("📝 Evaluaciones por usuario", 15, bold=True))
            for username, total_evals, avg_score in data["eval_por_usuario"]:
                row = QFrame()
                row.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:10px;border:1px solid {C_BORDER};}}")
                rl = QHBoxLayout(row)
                rl.setContentsMargins(16, 10, 16, 10)
                rl.addWidget(_lbl(username, 13, bold=True))
                rl.addStretch()
                rl.addWidget(_lbl(f"{total_evals} evaluaciones  •  promedio {int(avg_score)}%", 11, color=C_MUTED))
                lay.addWidget(row)

        lay.addStretch()
        scroll.setWidget(inner)

        # Hacer el scroll redimensionable con la ventana
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _fetch_data(self):
        from config import get_database_path
        conn = sqlite3.connect(get_database_path())
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users WHERE is_active=1 AND role='user'")
        usuarios_activos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE role='user'")
        usuarios_total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sessions")
        sesiones_total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM interpretations")
        gestos_total = cur.fetchone()[0]

        cur.execute("SELECT AVG(confidence_score) FROM interpretations WHERE confidence_score IS NOT NULL")
        r = cur.fetchone()[0]
        precision_prom = (r or 0) * 100

        # Evaluaciones
        try:
            cur.execute("SELECT COUNT(*), MAX(score_pct) FROM evaluation_results")
            er = cur.fetchone()
            evaluaciones_total = er[0] or 0
            mejor_eval = er[1] or 0
        except Exception:
            evaluaciones_total, mejor_eval = 0, 0

        # Top usuarios
        cur.execute("""
            SELECT u.username, COUNT(i.id) as gestos, COUNT(DISTINCT s.id) as sesiones,
                   COALESCE(up.total_points, 0) as pts
            FROM users u
            LEFT JOIN sessions s ON u.id = s.user_id
            LEFT JOIN interpretations i ON s.id = i.session_id
            LEFT JOIN user_points up ON u.id = up.user_id
            WHERE u.role='user' AND u.is_active=1
            GROUP BY u.id ORDER BY gestos DESC LIMIT 5
        """)
        top_users = cur.fetchall()

        # Gestos más reconocidos
        cur.execute("""
            SELECT word_detected, COUNT(*) as total, AVG(confidence_score)
            FROM interpretations
            WHERE word_detected IS NOT NULL
            GROUP BY word_detected ORDER BY total DESC LIMIT 5
        """)
        top_gestos = cur.fetchall()

        # Actividad diaria últimos 30 días
        cur.execute("""
            SELECT DATE(timestamp) as dia, COUNT(*) as total
            FROM interpretations
            GROUP BY dia ORDER BY dia DESC LIMIT 30
        """)
        actividad_diaria = list(reversed(cur.fetchall()))

        # Evaluaciones por usuario
        try:
            cur.execute("""
                SELECT u.username, COUNT(er.id), AVG(er.score_pct)
                FROM evaluation_results er
                JOIN users u ON er.user_id = u.id
                GROUP BY er.user_id ORDER BY COUNT(er.id) DESC
            """)
            eval_por_usuario = cur.fetchall()
        except Exception:
            eval_por_usuario = []

        conn.close()
        return {
            "usuarios_activos": usuarios_activos,
            "usuarios_total":   usuarios_total,
            "sesiones_total":   sesiones_total,
            "gestos_total":     gestos_total,
            "precision_prom":   precision_prom,
            "evaluaciones_total": evaluaciones_total,
            "mejor_eval":       mejor_eval,
            "top_users":        top_users,
            "top_gestos":       top_gestos,
            "actividad_diaria": actividad_diaria,
            "eval_por_usuario": eval_por_usuario,
        }

    def _blank_icon(self):
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        return QIcon(px)
