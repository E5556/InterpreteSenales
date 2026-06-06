import sys
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor

from database import get_session_interpretations, get_database_name

C_BG      = "#f8fafc"
C_CARD    = "#ffffff"
C_ACCENT  = "#7c3aed"
C_BORDER  = "#e2e8f0"
C_DARK    = "#1e293b"
C_MUTED   = "#64748b"
C_SUCCESS = "#22c55e"
C_DANGER  = "#ef4444"


def _lbl(text, size=13, bold=False, color=C_DARK, align=Qt.AlignLeft):
    l = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    l.setFont(f)
    l.setStyleSheet(f"color:{color}; background:transparent;")
    l.setAlignment(align)
    return l


class HistoryWindow(QWidget):
    def __init__(self, session_id, controller):
        super().__init__()
        self.session_id = session_id
        self.controller = controller
        self._interpretations = []

        conn = sqlite3.connect(get_database_name())
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, start_time FROM sessions WHERE id = ?", (session_id,))
        result = cursor.fetchone()
        self.user_id   = result[0] if result else None
        self.start_time = result[1] if result else None
        # Obtener username
        self.username = "Usuario"
        if self.user_id:
            cursor.execute("SELECT username FROM users WHERE id=?", (self.user_id,))
            r = cursor.fetchone()
            if r:
                self.username = r[0]
        conn.close()

        self.setWindowTitle(f"Historial de Sesión #{session_id}")
        self.setGeometry(300, 150, 700, 560)
        self.setMinimumSize(600, 480)
        self.setStyleSheet(f"background:{C_BG};")
        self.setWindowIcon(self._blank_icon())

        self._build_ui()
        self.populate_interpretations()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(16)

        # Encabezado
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(_lbl(f"Historial de Sesión #{self.session_id}", 20, bold=True))
        fecha = str(self.start_time)[:16] if self.start_time else "Sin fecha"
        title_col.addWidget(_lbl(f"Usuario: {self.username}  •  {fecha}", 11, color=C_MUTED))
        header.addLayout(title_col)
        header.addStretch()
        root.addLayout(header)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C_BORDER};")
        root.addWidget(sep)

        # Tabla de interpretaciones
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["#", "Seña", "Confianza", "Hora"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 90)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet(f"""
            QTableWidget {{border:1px solid {C_BORDER};border-radius:10px;background:{C_CARD};font-size:13px;color:{C_DARK};}}
            QHeaderView::section {{background:#f1f5f9;font-weight:bold;padding:8px;border:none;color:{C_DARK};}}
            QTableWidget::item:alternate {{background:#f8f9ff;}}
        """)
        root.addWidget(self.table)

        # Resumen
        self.summary_lbl = _lbl("", 11, color=C_MUTED)
        root.addWidget(self.summary_lbl)

        # Botones
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_pdf = QPushButton("📄  Exportar PDF")
        self.btn_pdf.setFixedHeight(40)
        self.btn_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_pdf.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.btn_pdf.setStyleSheet(f"""
            QPushButton {{background:{C_ACCENT};color:white;border-radius:8px;border:none;}}
            QPushButton:hover {{background:#6d28d9;}}
            QPushButton:disabled {{background:#e2e8f0;color:{C_MUTED};}}
        """)
        self.btn_pdf.clicked.connect(self.export_pdf)
        btn_row.addWidget(self.btn_pdf)

        btn_row.addStretch()

        self.back_button = QPushButton("🔙  Volver a Sesiones")
        self.back_button.setFixedHeight(40)
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.setFont(QFont("Segoe UI", 12))
        self.back_button.setStyleSheet(f"""
            QPushButton {{background:{C_CARD};color:{C_DARK};border:1px solid {C_BORDER};border-radius:8px;}}
            QPushButton:hover {{background:#f1f5f9;}}
        """)
        self.back_button.clicked.connect(self.go_back)
        btn_row.addWidget(self.back_button)

        self.logout_button = QPushButton("🚪  Cerrar Sesión")
        self.logout_button.setFixedHeight(40)
        self.logout_button.setCursor(Qt.PointingHandCursor)
        self.logout_button.setFont(QFont("Segoe UI", 12))
        self.logout_button.setStyleSheet(f"""
            QPushButton {{background:{C_CARD};color:{C_DANGER};border:1px solid {C_DANGER};border-radius:8px;}}
            QPushButton:hover {{background:rgba(239,68,68,0.08);}}
        """)
        self.logout_button.clicked.connect(self.logout)
        btn_row.addWidget(self.logout_button)

        root.addLayout(btn_row)

    def populate_interpretations(self):
        self.table.setRowCount(0)
        self._interpretations = []

        try:
            conn = sqlite3.connect(get_database_name())
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(interpretations)")
            cols = [c[1] for c in cursor.fetchall()]
            if 'confidence_score' in cols:
                cursor.execute(
                    "SELECT word_detected, confidence_score, timestamp FROM interpretations WHERE session_id=? ORDER BY timestamp ASC",
                    (self.session_id,)
                )
                rows = cursor.fetchall()
                self._interpretations = [(w, c, t) for w, c, t in rows]
            else:
                cursor.execute(
                    "SELECT word FROM interpretations WHERE session_id=? ORDER BY id ASC",
                    (self.session_id,)
                )
                rows = cursor.fetchall()
                self._interpretations = [(w, None, None) for (w,) in rows]
            conn.close()
        except Exception:
            interpretations = get_session_interpretations(self.session_id)
            self._interpretations = [(w, None, t) for w, t in interpretations]

        if not self._interpretations:
            self.table.setRowCount(1)
            item = QTableWidgetItem("No hay interpretaciones en esta sesión.")
            item.setForeground(QColor(C_MUTED))
            self.table.setItem(0, 1, item)
            self.btn_pdf.setEnabled(False)
            self.summary_lbl.setText("Sin interpretaciones registradas.")
            return

        for i, (word, conf, ts) in enumerate(self._interpretations):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.item(i, 0).setTextAlignment(Qt.AlignCenter)

            word_item = QTableWidgetItem(word or "—")
            word_item.setFont(QFont("Segoe UI", 12, QFont.Bold))
            self.table.setItem(i, 1, word_item)

            if conf is not None:
                pct = int(float(conf) * 100)
                conf_item = QTableWidgetItem(f"{pct}%")
                conf_item.setTextAlignment(Qt.AlignCenter)
                conf_item.setForeground(QColor(C_SUCCESS if pct >= 80 else (C_MUTED if pct >= 60 else C_DANGER)))
                self.table.setItem(i, 2, conf_item)
            else:
                self.table.setItem(i, 2, QTableWidgetItem("—"))

            ts_str = str(ts)[11:19] if ts else "—"
            ts_item = QTableWidgetItem(ts_str)
            ts_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, ts_item)

        # Resumen
        total = len(self._interpretations)
        confs = [float(c) for _, c, _ in self._interpretations if c is not None]
        avg_conf = sum(confs) / len(confs) * 100 if confs else 0
        gestos_unicos = len({w for w, _, _ in self._interpretations})
        self.summary_lbl.setText(
            f"{total} interpretaciones  •  {gestos_unicos} gestos distintos"
            + (f"  •  Precisión promedio: {avg_conf:.1f}%" if confs else "")
        )

    def export_pdf(self):
        if not self._interpretations:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF", f"sesion_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            "PDF Files (*.pdf)"
        )
        if not path:
            return
        try:
            self._generate_pdf(path)
            QMessageBox.information(self, "PDF exportado", f"PDF guardado en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el PDF:\n{str(e)}")

    def _generate_pdf(self, path):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

        doc = SimpleDocTemplate(path, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        accent = colors.HexColor("#7c3aed")
        muted  = colors.HexColor("#64748b")
        green  = colors.HexColor("#22c55e")
        red    = colors.HexColor("#ef4444")

        title_style = ParagraphStyle("title", fontSize=20, textColor=accent, fontName="Helvetica-Bold", spaceAfter=4)
        sub_style   = ParagraphStyle("sub",   fontSize=11, textColor=muted,  fontName="Helvetica", spaceAfter=2)
        normal      = styles["Normal"]

        story = []
        story.append(Paragraph("Intérprete LSC — Reporte de Sesión", title_style))
        story.append(Paragraph(f"Sesión #{self.session_id}  •  Usuario: {self.username}  •  Fecha: {str(self.start_time)[:16] if self.start_time else 'Sin fecha'}", sub_style))
        story.append(HRFlowable(width="100%", thickness=1, color=accent, spaceAfter=12))

        # Resumen
        total  = len(self._interpretations)
        confs  = [float(c) for _, c, _ in self._interpretations if c is not None]
        avg_c  = sum(confs) / len(confs) * 100 if confs else 0
        unicos = len({w for w, _, _ in self._interpretations})
        story.append(Paragraph(f"<b>Total interpretaciones:</b> {total}  &nbsp;&nbsp; <b>Gestos distintos:</b> {unicos}" +
                                (f"  &nbsp;&nbsp; <b>Precisión promedio:</b> {avg_c:.1f}%" if confs else ""), normal))
        story.append(Spacer(1, 0.4*cm))

        # Tabla
        data = [["#", "Seña", "Confianza", "Hora"]]
        for i, (word, conf, ts) in enumerate(self._interpretations):
            pct_str = f"{int(float(conf)*100)}%" if conf is not None else "—"
            ts_str  = str(ts)[11:19] if ts else "—"
            data.append([str(i+1), word or "—", pct_str, ts_str])

        col_widths = [1*cm, 7*cm, 3*cm, 3.5*cm]
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), accent),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,0), 11),
            ("ALIGN",       (0,0), (-1,-1), "CENTER"),
            ("ALIGN",       (1,1), (1,-1), "LEFT"),
            ("FONTSIZE",    (0,1), (-1,-1), 10),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9ff")]),
            ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING",  (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.6*cm))
        story.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} — Sistema Intérprete LSC", sub_style))
        doc.build(story)

    def go_back(self):
        if self.user_id:
            self.controller.go_back_to_sessions(self.user_id)
            self.close()

    def logout(self):
        self.controller.logout()
        self.close()

    def _blank_icon(self):
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        return QIcon(px)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    class MockController:
        def go_back_to_sessions(self, u): print("Volver", u)
        def logout(self): print("Logout")
    w = HistoryWindow(session_id=1, controller=MockController())
    w.show()
    sys.exit(app.exec_())
