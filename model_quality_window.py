import sqlite3
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
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


def _lbl(text, size=13, bold=False, color=C_DARK, wrap=False):
    l = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet(f"color:{color}; background:transparent;")
    l.setWordWrap(wrap)
    return l


class ModelQualityWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calidad del Modelo — Admin")
        self.setGeometry(200, 80, 860, 640)
        self.setMinimumSize(720, 520)
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
        lay.setSpacing(20)

        lay.addWidget(_lbl("🧪 Calidad del Modelo", 22, bold=True))
        lay.addWidget(_lbl("Análisis basado en los resultados reales del Modo Evaluación", 12, color=C_MUTED))

        data = self._fetch_data()

        if not data["gestures"]:
            lay.addWidget(_lbl(
                "No hay suficientes evaluaciones para generar el análisis.\n"
                "Los usuarios deben completar el Modo Evaluación para acumular datos.",
                13, color=C_MUTED, wrap=True
            ))
            scroll.setWidget(inner)
            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.addWidget(scroll)
            return

        gestures = data["gestures"]

        # ── Métricas globales ─────────────────────────────────────
        total_pred = data["total_predictions"]
        correct    = data["total_correct"]
        global_acc = int(correct / total_pred * 100) if total_pred > 0 else 0

        mcard = QFrame()
        mcard.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:14px;border:1px solid {C_BORDER};}}")
        ml = QHBoxLayout(mcard)
        ml.setContentsMargins(24, 18, 24, 18)
        ml.setSpacing(32)
        for title, val, color in [
            ("Total predicciones", str(total_pred), C_ACCENT),
            ("Correctas", str(correct), C_SUCCESS),
            ("Incorrectas", str(total_pred - correct), C_DANGER),
            ("Precisión global", f"{global_acc}%", C_ACCENT),
        ]:
            col = QVBoxLayout()
            col.addWidget(_lbl(title, 10, color=C_MUTED))
            col.addWidget(_lbl(val, 26, bold=True, color=color))
            ml.addLayout(col)
        ml.addStretch()
        lay.addWidget(mcard)

        # ── Precisión por gesto ───────────────────────────────────
        lay.addWidget(_lbl("✋ Precisión por gesto", 15, bold=True))
        COLORS = ["#7c3aed","#3b82f6","#22c55e","#f59e0b","#ef4444"]
        for i, g in enumerate(gestures):
            acc_g = int(g["correct"] / g["total"] * 100) if g["total"] > 0 else 0
            color = COLORS[i % len(COLORS)]
            row_w = QFrame()
            row_w.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:10px;border:1px solid {C_BORDER};}}")
            rl = QVBoxLayout(row_w)
            rl.setContentsMargins(16, 10, 16, 10)
            rl.setSpacing(4)
            hr = QHBoxLayout()
            hr.addWidget(_lbl(g["name"], 13, bold=True, color=color))
            hr.addStretch()
            hr.addWidget(_lbl(f"{g['correct']}/{g['total']}  •  {acc_g}%", 11, color=C_MUTED))
            rl.addLayout(hr)
            from PyQt5.QtWidgets import QProgressBar
            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setValue(acc_g)
            bar.setFixedHeight(10)
            bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar{{background:{C_BORDER};border-radius:5px;}}"
                f"QProgressBar::chunk{{background:{color};border-radius:5px;}}"
            )
            rl.addWidget(bar)
            lay.addWidget(row_w)

        # ── Tabla de confusiones ──────────────────────────────────
        if data["confusion"] and _MPL:
            lay.addWidget(_lbl("🔀 Matriz de confusión", 15, bold=True))
            lay.addWidget(_lbl(
                "Filas = gesto esperado, Columnas = gesto detectado. "
                "La diagonal debe ser alta (predicciones correctas).",
                11, color=C_MUTED, wrap=True
            ))
            try:
                labels = gestures_names = [g["name"] for g in gestures]
                n = len(labels)
                matrix = np.zeros((n, n), dtype=int)
                name_to_idx = {g: i for i, g in enumerate(labels)}

                for expected, predicted, count in data["confusion"]:
                    if expected in name_to_idx and predicted in name_to_idx:
                        matrix[name_to_idx[expected]][name_to_idx[predicted]] += count

                fig, ax = plt.subplots(figsize=(6, 5))
                fig.patch.set_facecolor("#ffffff")
                im = ax.imshow(matrix, cmap="Blues")
                ax.set_xticks(range(n))
                ax.set_yticks(range(n))
                ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
                ax.set_yticklabels(labels, fontsize=9)
                ax.set_xlabel("Detectado", fontsize=10)
                ax.set_ylabel("Esperado", fontsize=10)
                ax.set_title("Matriz de Confusión", fontsize=11, pad=10)
                for i in range(n):
                    for j in range(n):
                        val = matrix[i, j]
                        if val > 0:
                            txt_color = "white" if matrix[i, j] > matrix.max() * 0.6 else "black"
                            ax.text(j, i, str(val), ha="center", va="center",
                                    color=txt_color, fontsize=10, fontweight="bold")
                fig.colorbar(im, ax=ax, shrink=0.8)
                fig.tight_layout()

                chart_card = QFrame()
                chart_card.setStyleSheet(f"QFrame{{background:{C_CARD};border-radius:14px;border:1px solid {C_BORDER};}}")
                cc = QVBoxLayout(chart_card)
                cc.setContentsMargins(16, 14, 16, 14)
                canvas = FigureCanvas(fig)
                canvas.setFixedHeight(300)
                cc.addWidget(canvas)
                lay.addWidget(chart_card)
                plt.close(fig)
            except Exception:
                pass

        # ── Errores más frecuentes ────────────────────────────────
        if data["top_errors"]:
            lay.addWidget(_lbl("❌ Confusiones más frecuentes", 15, bold=True))
            err_table = QTableWidget(len(data["top_errors"]), 3)
            err_table.setHorizontalHeaderLabels(["Gesto esperado", "Detectado como", "Veces"])
            err_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            err_table.setEditTriggers(QTableWidget.NoEditTriggers)
            err_table.verticalHeader().setVisible(False)
            err_table.setStyleSheet(
                f"QTableWidget{{border:1px solid {C_BORDER};border-radius:10px;background:{C_CARD};}}"
                f"QHeaderView::section{{background:#f1f5f9;font-weight:bold;padding:8px;border:none;}}"
            )
            for i, (exp, pred, cnt) in enumerate(data["top_errors"]):
                err_table.setItem(i, 0, QTableWidgetItem(exp))
                err_table.setItem(i, 1, QTableWidgetItem(pred))
                cnt_item = QTableWidgetItem(str(cnt))
                cnt_item.setForeground(QColor(C_DANGER))
                cnt_item.setTextAlignment(Qt.AlignCenter)
                err_table.setItem(i, 2, cnt_item)
            err_table.setFixedHeight(min(200, 40 + len(data["top_errors"]) * 36))
            lay.addWidget(err_table)

        lay.addStretch()
        scroll.setWidget(inner)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _fetch_data(self):
        try:
            from config import get_database_path
            from training_utils import get_gestures_with_valid_keypoints
            conn = sqlite3.connect(get_database_path())
            cur = conn.cursor()

            try:
                cur.execute("SELECT details FROM evaluation_results WHERE details IS NOT NULL")
                rows = cur.fetchall()
            except Exception:
                conn.close()
                return {"gestures": [], "total_predictions": 0, "total_correct": 0,
                        "confusion": [], "top_errors": []}

            conn.close()

            word_ids = [g.upper() for g in get_gestures_with_valid_keypoints()]
            stats = {w: {"total": 0, "correct": 0} for w in word_ids}
            confusion_counts = {}
            total_pred = 0
            total_correct = 0

            for (details_json,) in rows:
                try:
                    details = json.loads(details_json)
                    for d in details:
                        exp  = (d.get("word") or "").upper()
                        pred = (d.get("pred") or "").upper()
                        ok   = d.get("ok", False)
                        if not exp:
                            continue
                        total_pred += 1
                        if ok:
                            total_correct += 1
                        if exp in stats:
                            stats[exp]["total"] += 1
                            if ok:
                                stats[exp]["correct"] += 1
                        # Confusión
                        if pred:
                            key = (exp, pred)
                            confusion_counts[key] = confusion_counts.get(key, 0) + 1
                except Exception:
                    continue

            gestures = [
                {"name": w, "total": stats[w]["total"], "correct": stats[w]["correct"]}
                for w in word_ids if stats[w]["total"] > 0
            ]

            confusion = [(exp, pred, cnt) for (exp, pred), cnt in confusion_counts.items()]
            top_errors = sorted(
                [(exp, pred, cnt) for (exp, pred), cnt in confusion_counts.items() if exp != pred],
                key=lambda x: -x[2]
            )[:8]

            return {
                "gestures": gestures,
                "total_predictions": total_pred,
                "total_correct": total_correct,
                "confusion": confusion,
                "top_errors": top_errors,
            }
        except Exception:
            return {"gestures": [], "total_predictions": 0, "total_correct": 0,
                    "confusion": [], "top_errors": []}

    def _blank_icon(self):
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        return QIcon(px)
