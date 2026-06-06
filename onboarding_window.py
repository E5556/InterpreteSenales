import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QStackedWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon

C_BG     = "#0f0f1a"
C_CARD   = "#1e1e2e"
C_ACCENT = "#7c3aed"
C_TEXT   = "#f8fafc"
C_MUTED  = "#94a3b8"

STEPS = [
    {
        "emoji": "👋",
        "title": "¡Bienvenido al Intérprete LSC!",
        "body": (
            "Este sistema reconoce <b>lengua de señas colombiana</b> en tiempo real "
            "usando tu cámara y un modelo de inteligencia artificial.<br><br>"
            "En los siguientes pasos te explicamos cómo sacarle el máximo provecho."
        ),
    },
    {
        "emoji": "✋",
        "title": "Gestos disponibles",
        "body": (
            "El modelo actualmente reconoce <b>5 gestos</b>:<br><br>"
            "<b>HOLA &nbsp;·&nbsp; ADIOS &nbsp;·&nbsp; ADULTO &nbsp;·&nbsp; ANCIANO &nbsp;·&nbsp; GATO</b><br><br>"
            "Cada gesto debe hacerse frente a la cámara con buena iluminación.<br>"
            "El sistema acumula frames y predice cuando detecta que bajaste la mano."
        ),
    },
    {
        "emoji": "🎓",
        "title": "Aprende antes de practicar",
        "body": (
            "Usa el <b>Modo Aprendizaje</b> para ver la animación 3D de cada gesto "
            "antes de intentarlo.<br><br>"
            "Luego practica en el <b>Intérprete</b> (Nueva Sesión) y finalmente "
            "evalúa tu nivel en el <b>Modo Evaluación</b>."
        ),
    },
    {
        "emoji": "🏆",
        "title": "Gana puntos y sube de nivel",
        "body": (
            "Cada gesto reconocido te da <b>2 puntos</b>. "
            "La precisión y las rachas diarias otorgan bonos adicionales.<br><br>"
            "Completa <b>retos diarios y semanales</b>, desbloquea <b>logros</b> "
            "y compite en el <b>ranking</b> con otros usuarios.<br><br>"
            "Al subir de nivel recibirás un <b>certificado PDF</b> descargable."
        ),
    },
    {
        "emoji": "🚀",
        "title": "¡Listo para empezar!",
        "body": (
            "Ya conoces lo esencial. Pulsa <b>Comenzar</b> para ir al menú principal.<br><br>"
            "Puedes revisar tus estadísticas, gestos y evaluaciones en cualquier momento "
            "desde el menú lateral."
        ),
    },
]


def _should_show_onboarding(user_id, db_path):
    """Retorna True si el usuario nunca ha visto el onboarding."""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_meta
            (user_id INTEGER PRIMARY KEY, daily_goal INTEGER DEFAULT 10,
             onboarding_done INTEGER DEFAULT 0)
        """)
        # Agregar columna si no existe (migración segura)
        try:
            cur.execute("ALTER TABLE user_meta ADD COLUMN onboarding_done INTEGER DEFAULT 0")
        except Exception:
            pass
        cur.execute("SELECT onboarding_done FROM user_meta WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        conn.commit()
        conn.close()
        return (row is None) or (row[0] == 0)
    except Exception:
        return False


def _mark_onboarding_done(user_id, db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_meta (user_id, daily_goal, onboarding_done)
            VALUES (?, 10, 1)
            ON CONFLICT(user_id) DO UPDATE SET onboarding_done=1
        """, (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass


class OnboardingWindow(QDialog):
    def __init__(self, user_id, db_path, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.db_path = db_path
        self.setWindowTitle("Bienvenida — Intérprete LSC")
        self.setFixedSize(560, 480)
        self.setStyleSheet(f"background:{C_BG};")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.stack = QStackedWidget()
        for step in STEPS:
            self.stack.addWidget(self._build_step(step))
        root.addWidget(self.stack)

        # Barra de navegación
        nav = QWidget()
        nav.setStyleSheet(f"background:{C_CARD};")
        nl = QHBoxLayout(nav)
        nl.setContentsMargins(24, 14, 24, 14)

        self.dots_layout = QHBoxLayout()
        self.dots_layout.setSpacing(8)
        self._dots = []
        for i in range(len(STEPS)):
            d = QLabel("●")
            d.setFont(QFont("Segoe UI", 10))
            d.setStyleSheet(f"color:{C_ACCENT if i==0 else '#2d2d44'}; background:transparent;")
            self._dots.append(d)
            self.dots_layout.addWidget(d)
        nl.addLayout(self.dots_layout)
        nl.addStretch()

        self.btn_prev = QPushButton("← Anterior")
        self.btn_prev.setFixedHeight(38)
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setFont(QFont("Segoe UI", 11))
        self.btn_prev.setStyleSheet(
            f"QPushButton{{background:transparent;color:{C_MUTED};border:1px solid #2d2d44;border-radius:8px;padding:0 16px;}}"
            f"QPushButton:hover{{color:{C_TEXT};border-color:{C_MUTED};}}"
        )
        self.btn_prev.clicked.connect(self._prev)
        self.btn_prev.setVisible(False)
        nl.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Siguiente →")
        self.btn_next.setFixedHeight(38)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_next.setStyleSheet(
            f"QPushButton{{background:{C_ACCENT};color:white;border:none;border-radius:8px;padding:0 20px;}}"
            f"QPushButton:hover{{background:#6d28d9;}}"
        )
        self.btn_next.clicked.connect(self._next)
        nl.addWidget(self.btn_next)

        root.addWidget(nav)

    def _build_step(self, step):
        w = QWidget()
        w.setStyleSheet(f"background:{C_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(48, 40, 48, 20)
        lay.setSpacing(16)
        lay.addStretch()

        em = QLabel(step["emoji"])
        em.setAlignment(Qt.AlignCenter)
        em.setFont(QFont("Segoe UI", 56))
        em.setStyleSheet("background:transparent;")
        lay.addWidget(em)

        title = QLabel(step["title"])
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color:{C_TEXT}; background:transparent;")
        title.setWordWrap(True)
        lay.addWidget(title)

        body = QLabel()
        body.setText(step["body"])
        body.setAlignment(Qt.AlignCenter)
        body.setFont(QFont("Segoe UI", 12))
        body.setStyleSheet(f"color:{C_MUTED}; background:transparent;")
        body.setWordWrap(True)
        lay.addWidget(body)

        lay.addStretch()
        return w

    def _prev(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._update_nav(idx - 1)

    def _next(self):
        idx = self.stack.currentIndex()
        if idx < len(STEPS) - 1:
            self.stack.setCurrentIndex(idx + 1)
            self._update_nav(idx + 1)
        else:
            _mark_onboarding_done(self.user_id, self.db_path)
            self.accept()

    def _update_nav(self, idx):
        for i, d in enumerate(self._dots):
            d.setStyleSheet(f"color:{C_ACCENT if i==idx else '#2d2d44'}; background:transparent;")
        self.btn_prev.setVisible(idx > 0)
        is_last = (idx == len(STEPS) - 1)
        self.btn_next.setText("🚀  Comenzar" if is_last else "Siguiente →")
