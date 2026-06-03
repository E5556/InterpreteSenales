"""
Ventana de Modo de Aprendizaje - Lenguaje de Señas Peruano
"""

import sys
import os
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QSlider, QTextEdit,
                             QListWidget, QListWidgetItem,
                             QProgressBar, QMessageBox, QCheckBox,
                             QFrame)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon
import open3d as o3d
from hand_3d_model import Hand3DModel
from hand_3d_widget import Hand3DWidget
from realistic_3d_visualizer import Realistic3DVisualizer
from frame_viewer import FrameViewer

# ── Paleta del sistema ────────────────────────────────────────────────────────
C_SIDEBAR   = "#1e1e2e"
C_ACCENT    = "#7c3aed"
C_ACCENT_L  = "#a78bfa"
C_BG        = "#f8fafc"
C_CARD      = "#ffffff"
C_BORDER    = "#e2e8f0"
C_TEXT      = "#1e293b"
C_MUTED     = "#64748b"
C_SUCCESS   = "#22c55e"
C_DANGER    = "#ef4444"
C_WARNING   = "#f59e0b"


def _styled_btn(text, color=C_ACCENT, icon="", min_w=None):
    btn = QPushButton(f"{icon}  {text}" if icon else text)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedHeight(36)
    if min_w:
        btn.setMinimumWidth(min_w)
    btn.setFont(QFont("Segoe UI", 11))
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {color}; color: white;
            border: none; border-radius: 8px; padding: 0 14px;
        }}
        QPushButton:hover {{ background: {color}dd; }}
        QPushButton:pressed {{ background: {color}aa; }}
        QPushButton:disabled {{ background: #e2e8f0; color: #94a3b8; }}
    """)
    return btn


def _section_label(text):
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
    lbl.setStyleSheet(f"color:{C_MUTED}; letter-spacing:1px; background:transparent;")
    return lbl


def _card_frame():
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background: {C_CARD};
            border: 1px solid {C_BORDER};
            border-radius: 12px;
        }}
    """)
    return f


class AnimationThread(QThread):
    frame_updated    = pyqtSignal(int, int)
    animation_finished = pyqtSignal()

    def __init__(self, hand_model):
        super().__init__()
        self.hand_model = hand_model
        self.is_running = False

    def run(self):
        self.is_running = True
        while self.is_running and self.hand_model.is_playing:
            if self.hand_model.current_frame < self.hand_model.total_frames - 1:
                self.hand_model.next_frame()
                self.frame_updated.emit(self.hand_model.current_frame, self.hand_model.total_frames)
                self.msleep(int(100 / self.hand_model.animation_speed))
            else:
                self.hand_model.is_playing = False
                self.animation_finished.emit()
                break

    def stop(self):
        self.is_running = False


class LearningModeWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.hand_model = Hand3DModel()
        self.animation_thread = None
        self.vis = None
        self.current_gesture = None
        self.phrase_gestures = []
        self.hand_3d_widget = None
        self.realistic_visualizer = None
        self.frame_viewer = None
        self.current_phrase_index = 0
        self.is_playing_phrase = False

        self.init_ui()
        self.load_available_gestures()

    # ── UI ────────────────────────────────────────────────────────────────────
    def init_ui(self):
        self.setWindowTitle("Modo Aprendizaje — Intérprete LSP")
        self.setGeometry(80, 60, 1380, 860)
        self.setMinimumSize(1100, 680)

        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        self.setWindowIcon(QIcon(px))

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── SIDEBAR izquierdo ─────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet(f"background:{C_SIDEBAR};")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(16, 24, 16, 20)
        sb_lay.setSpacing(0)

        # Logo / título
        title_lbl = QLabel("🎓 Modo Aprendizaje")
        title_lbl.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title_lbl.setStyleSheet("color:white; padding-bottom:4px; background:transparent;")
        sb_lay.addWidget(title_lbl)

        sub_lbl = QLabel("Lengua de Señas Peruana")
        sub_lbl.setFont(QFont("Segoe UI", 10))
        sub_lbl.setStyleSheet(f"color:{C_ACCENT_L}; padding-bottom:18px; background:transparent;")
        sb_lay.addWidget(sub_lbl)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#2d2d44;")
        sb_lay.addWidget(sep)
        sb_lay.addSpacing(16)

        # ── Sección: Gestos ───────────────────────────────────────
        sb_lay.addWidget(_section_label("GESTOS DISPONIBLES"))
        sb_lay.addSpacing(6)

        self.gesture_list = QListWidget()
        self.gesture_list.setMaximumHeight(180)
        self.gesture_list.setStyleSheet(f"""
            QListWidget {{
                background: #2d2d44; border: none; border-radius: 10px;
                color: #c4b5fd; font-size: 13px; padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px 12px; border-radius: 7px;
            }}
            QListWidget::item:hover {{
                background: rgba(124,58,237,0.25); color: white;
            }}
            QListWidget::item:selected {{
                background: {C_ACCENT}; color: white; font-weight: bold;
            }}
        """)
        self.gesture_list.itemClicked.connect(self.on_gesture_selected)
        sb_lay.addWidget(self.gesture_list)
        sb_lay.addSpacing(12)

        # Info gesto seleccionado
        sb_lay.addWidget(_section_label("INFORMACIÓN"))
        sb_lay.addSpacing(6)
        self.gesture_info = QTextEdit()
        self.gesture_info.setMaximumHeight(90)
        self.gesture_info.setReadOnly(True)
        self.gesture_info.setStyleSheet(f"""
            QTextEdit {{
                background: #2d2d44; border: none; border-radius: 10px;
                color: #94a3b8; font-size: 12px; padding: 8px;
            }}
        """)
        sb_lay.addWidget(self.gesture_info)
        sb_lay.addSpacing(16)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background:#2d2d44;")
        sb_lay.addWidget(sep2)
        sb_lay.addSpacing(16)

        # ── Sección: Frase ────────────────────────────────────────
        sb_lay.addWidget(_section_label("CONSTRUIR FRASE"))
        sb_lay.addSpacing(6)

        self.phrase_list = QListWidget()
        self.phrase_list.setMaximumHeight(130)
        self.phrase_list.setStyleSheet(f"""
            QListWidget {{
                background: #2d2d44; border: none; border-radius: 10px;
                color: #c4b5fd; font-size: 12px; padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px 12px; border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background: {C_ACCENT}; color: white;
            }}
        """)
        sb_lay.addWidget(self.phrase_list)
        sb_lay.addSpacing(8)

        phrase_btns = QHBoxLayout()
        phrase_btns.setSpacing(6)
        self.add_to_phrase_btn = _styled_btn("+ Agregar", C_ACCENT)
        self.clear_phrase_btn  = _styled_btn("Limpiar", "#475569")
        self.play_phrase_btn   = _styled_btn("▶ Frase", C_SUCCESS)
        self.add_to_phrase_btn.clicked.connect(self.add_to_phrase)
        self.clear_phrase_btn.clicked.connect(self.clear_phrase)
        self.play_phrase_btn.clicked.connect(self.play_phrase)
        phrase_btns.addWidget(self.add_to_phrase_btn)
        phrase_btns.addWidget(self.clear_phrase_btn)
        phrase_btns.addWidget(self.play_phrase_btn)
        sb_lay.addLayout(phrase_btns)
        sb_lay.addSpacing(16)

        sep3 = QFrame()
        sep3.setFixedHeight(1)
        sep3.setStyleSheet("background:#2d2d44;")
        sb_lay.addWidget(sep3)
        sb_lay.addSpacing(16)

        # ── Sección: Configuración ────────────────────────────────
        sb_lay.addWidget(_section_label("CONFIGURACIÓN"))
        sb_lay.addSpacing(8)

        def _chk(text):
            cb = QCheckBox(text)
            cb.setFont(QFont("Segoe UI", 11))
            cb.setStyleSheet(f"""
                QCheckBox {{ color: #94a3b8; background: transparent; }}
                QCheckBox:hover {{ color: white; }}
                QCheckBox::indicator {{ width:16px; height:16px; border-radius:4px;
                    border:1px solid #4d4d66; background:#2d2d44; }}
                QCheckBox::indicator:checked {{ background:{C_ACCENT}; border-color:{C_ACCENT}; }}
            """)
            return cb

        self.loop_checkbox            = _chk("Repetir en bucle")
        self.show_both_hands_checkbox = _chk("Mostrar ambas manos")
        self.show_both_hands_checkbox.setChecked(True)
        self.highlight_keypoints_checkbox = _chk("Resaltar puntos clave")
        sb_lay.addWidget(self.loop_checkbox)
        sb_lay.addSpacing(4)
        sb_lay.addWidget(self.show_both_hands_checkbox)
        sb_lay.addSpacing(4)
        sb_lay.addWidget(self.highlight_keypoints_checkbox)

        sb_lay.addStretch()

        # Botón ayuda al fondo
        help_btn = QPushButton("❓  Ayuda")
        help_btn.setFixedHeight(38)
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.setFont(QFont("Segoe UI", 11))
        help_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C_ACCENT_L};
                border: 1px solid #3d3d5c; border-radius: 8px;
            }}
            QPushButton:hover {{ background: rgba(124,58,237,0.2); color: white; }}
        """)
        help_btn.clicked.connect(self.show_help)
        sb_lay.addWidget(help_btn)

        root_layout.addWidget(sidebar)

        # ── PANEL DERECHO: visualización ──────────────────────────
        right = QWidget()
        right.setStyleSheet(f"background:{C_BG};")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(28, 24, 28, 20)
        right_lay.setSpacing(16)

        # Encabezado
        hdr = QHBoxLayout()
        self.current_gesture_lbl = QLabel("Selecciona un gesto")
        self.current_gesture_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.current_gesture_lbl.setStyleSheet(f"color:{C_TEXT}; background:transparent;")
        hdr.addWidget(self.current_gesture_lbl)
        hdr.addStretch()

        self.phrase_progress_lbl = QLabel("")
        self.phrase_progress_lbl.setFont(QFont("Segoe UI", 11))
        self.phrase_progress_lbl.setStyleSheet(f"color:{C_MUTED}; background:transparent;")
        hdr.addWidget(self.phrase_progress_lbl)
        right_lay.addLayout(hdr)

        # Visor de frames — tarjeta
        viewer_card = _card_frame()
        vc_lay = QVBoxLayout(viewer_card)
        vc_lay.setContentsMargins(0, 0, 0, 0)
        self.frame_viewer = FrameViewer()
        self.frame_viewer.frame_updated.connect(self.on_frame_updated)
        self.frame_viewer.setStyleSheet("background:transparent; border:none;")
        vc_lay.addWidget(self.frame_viewer)
        right_lay.addWidget(viewer_card, 1)

        # Barra de progreso del frame
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ background:{C_BORDER}; border-radius:3px; border:none; }}
            QProgressBar::chunk {{ background:{C_ACCENT}; border-radius:3px; }}
        """)
        right_lay.addWidget(self.progress_bar)

        # Controles de animación
        ctrl_card = _card_frame()
        ctrl_lay = QVBoxLayout(ctrl_card)
        ctrl_lay.setContentsMargins(18, 14, 18, 14)
        ctrl_lay.setSpacing(12)

        # Fila 1: botones de reproducción
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.back_btn  = _styled_btn("⏮", "#475569", min_w=44)
        self.play_btn  = _styled_btn("▶  Reproducir", C_ACCENT, min_w=130)
        self.pause_btn = _styled_btn("⏸  Pausar", "#0891b2", min_w=110)
        self.stop_btn  = _styled_btn("⏹  Detener", C_DANGER, min_w=110)
        self.step_btn  = _styled_btn("⏭", "#475569", min_w=44)

        self.play_btn.clicked.connect(self.play_animation)
        self.pause_btn.clicked.connect(self.pause_animation)
        self.stop_btn.clicked.connect(self.stop_animation)
        self.step_btn.clicked.connect(self.step_forward)
        self.back_btn.clicked.connect(self.step_backward)

        btn_row.addWidget(self.back_btn)
        btn_row.addWidget(self.play_btn)
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.step_btn)
        btn_row.addStretch()

        # Frame info a la derecha
        self.frame_info = QLabel("Frame: — / —")
        self.frame_info.setFont(QFont("Segoe UI", 11))
        self.frame_info.setStyleSheet(f"color:{C_MUTED}; background:transparent;")
        btn_row.addWidget(self.frame_info)

        ctrl_lay.addLayout(btn_row)

        # Fila 2: velocidad
        speed_row = QHBoxLayout()
        speed_row.setSpacing(10)
        spd_lbl = QLabel("🐢  Velocidad")
        spd_lbl.setFont(QFont("Segoe UI", 11))
        spd_lbl.setStyleSheet(f"color:{C_MUTED}; background:transparent;")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(50)
        self.speed_slider.setValue(10)
        self.speed_slider.setFixedWidth(200)
        self.speed_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px; background:{C_BORDER}; border-radius:3px;
            }}
            QSlider::handle:horizontal {{
                width:16px; height:16px; margin:-5px 0;
                background:{C_ACCENT}; border-radius:8px;
            }}
            QSlider::sub-page:horizontal {{
                background:{C_ACCENT}; border-radius:3px;
            }}
        """)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        self.speed_label = QLabel("1.0x  🐇")
        self.speed_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.speed_label.setStyleSheet(f"color:{C_ACCENT}; background:transparent;")
        speed_row.addWidget(spd_lbl)
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_label)
        speed_row.addStretch()
        ctrl_lay.addLayout(speed_row)

        right_lay.addWidget(ctrl_card)

        # Instrucciones compactas
        hint = QLabel(
            "💡  <b>Cómo usar:</b>  Selecciona un gesto en el panel izquierdo → Reproduce → "
            "Practica imitando la secuencia. Agrega gestos a la frase para reproducirlos en cadena."
        )
        hint.setFont(QFont("Segoe UI", 10))
        hint.setStyleSheet(
            f"color:{C_MUTED}; background:#f1f5f9; border-radius:8px; "
            f"padding:8px 14px; border:1px solid {C_BORDER};"
        )
        hint.setWordWrap(True)
        right_lay.addWidget(hint)

        root_layout.addWidget(right)

    # ── Lógica (sin cambios respecto al original) ─────────────────────────────
    def load_available_gestures(self):
        gestures = self.frame_viewer.get_available_gestures()
        self.gesture_list.clear()
        for gesture in gestures:
            item = QListWidgetItem(gesture.replace('_', ' ').title())
            item.setData(Qt.UserRole, gesture)
            self.gesture_list.addItem(item)

    def on_gesture_selected(self, item):
        gesture_name = item.data(Qt.UserRole)
        self.current_gesture = gesture_name
        self.current_gesture_lbl.setText(gesture_name.replace('_', ' ').title())

        if self.frame_viewer.load_gesture(gesture_name):
            info = self.frame_viewer.get_gesture_info(gesture_name)
            self.gesture_info.setHtml(
                f"<span style='color:#a78bfa'><b>{info['name'].replace('_',' ').title()}</b></span><br>"
                f"<span style='color:#64748b'>Muestras: {info.get('samples','N/A')} &nbsp;·&nbsp; "
                f"Frames: {info.get('total_frames','N/A')}</span>"
            )
            self.update_animation_controls()
        else:
            QMessageBox.warning(self, "Error", f"No se pudo cargar el gesto: {gesture_name}")

    def add_to_phrase(self):
        if self.current_gesture:
            self.phrase_gestures.append(self.current_gesture)
            self.update_phrase_display()

    def clear_phrase(self):
        self.phrase_gestures.clear()
        self.update_phrase_display()
        self.phrase_progress_lbl.setText("")

    def update_phrase_display(self):
        self.phrase_list.clear()
        for i, gesture in enumerate(self.phrase_gestures):
            item = QListWidgetItem(f"{i+1}. {gesture.replace('_', ' ').title()}")
            self.phrase_list.addItem(item)

    def play_phrase(self):
        if not self.phrase_gestures:
            QMessageBox.information(self, "Sin gestos",
                "No hay gestos en la frase.\nSelecciona un gesto y pulsa '+ Agregar'.")
            return
        self.current_phrase_index = 0
        self.is_playing_phrase = True
        self.play_next_gesture_in_phrase()

    def play_next_gesture_in_phrase(self):
        if not self.is_playing_phrase or self.current_phrase_index >= len(self.phrase_gestures):
            self.is_playing_phrase = False
            self.current_phrase_index = 0
            self.phrase_progress_lbl.setText("✅ Frase completada")
            return

        current_gesture = self.phrase_gestures[self.current_phrase_index]
        self.phrase_progress_lbl.setText(
            f"Gesto {self.current_phrase_index + 1} / {len(self.phrase_gestures)}"
        )

        if self.frame_viewer.load_gesture(current_gesture):
            self.current_gesture_lbl.setText(current_gesture.replace('_', ' ').title())
            info = self.frame_viewer.get_gesture_info(current_gesture)
            self.gesture_info.setHtml(
                f"<span style='color:#a78bfa'><b>{info['name'].replace('_',' ').title()}</b></span><br>"
                f"<span style='color:#64748b'>Frase: {self.current_phrase_index+1}/{len(self.phrase_gestures)}</span>"
            )
            self.highlight_current_phrase_gesture()
            self.frame_viewer.play_animation()
            self.update_play_buttons(True)
        else:
            self.current_phrase_index += 1
            self.play_next_gesture_in_phrase()

    def highlight_current_phrase_gesture(self):
        for i in range(self.phrase_list.count()):
            item = self.phrase_list.item(i)
            if i == self.current_phrase_index:
                item.setBackground(QColor("#7c3aed"))
                item.setForeground(QColor("#ffffff"))
            else:
                item.setBackground(QColor("#2d2d44"))
                item.setForeground(QColor("#c4b5fd"))

    def play_animation(self):
        if not self.frame_viewer.frame_files:
            QMessageBox.warning(self, "Sin frames", "Selecciona un gesto primero.")
            return
        self.frame_viewer.play_animation()
        self.update_play_buttons(True)

    def pause_animation(self):
        self.frame_viewer.pause_animation()
        self.update_play_buttons(False)
        if self.is_playing_phrase:
            self.is_playing_phrase = False

    def stop_animation(self):
        self.frame_viewer.stop_animation()
        self.update_play_buttons(False)
        self.update_frame_display()
        if self.is_playing_phrase:
            self.is_playing_phrase = False
            self.current_phrase_index = 0
            self.phrase_progress_lbl.setText("")
            for i in range(self.phrase_list.count()):
                self.phrase_list.item(i).setBackground(QColor("#2d2d44"))
                self.phrase_list.item(i).setForeground(QColor("#c4b5fd"))

    def step_forward(self):
        if self.frame_viewer.next_frame():
            self.update_frame_display()

    def step_backward(self):
        if self.frame_viewer.previous_frame():
            self.update_frame_display()

    def on_speed_changed(self, value):
        speed = value / 10.0
        self.frame_viewer.set_animation_speed(speed)
        self.speed_label.setText(f"{speed:.1f}x  {'🐇' if speed >= 2 else ('🐢' if speed <= 0.5 else '▶')}")

    def update_animation_controls(self):
        has_data = len(self.frame_viewer.frame_files) > 0
        for btn in (self.play_btn, self.pause_btn, self.stop_btn,
                    self.step_btn, self.back_btn, self.add_to_phrase_btn):
            btn.setEnabled(has_data)

    def update_play_buttons(self, is_playing):
        self.play_btn.setEnabled(not is_playing)
        self.pause_btn.setEnabled(is_playing)
        self.stop_btn.setEnabled(True)

    def update_frame_display(self):
        current = self.frame_viewer.current_frame
        total   = len(self.frame_viewer.frame_files)
        self.frame_info.setText(f"Frame: {current + 1} / {total}")
        if total > 0:
            self.progress_bar.setValue(int(((current + 1) / total) * 100))
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)

    def on_frame_updated(self, current_frame, total_frames):
        self.update_frame_display()
        if (self.is_playing_phrase and
                current_frame >= total_frames - 1 and
                self.frame_viewer.is_playing):
            self.current_phrase_index += 1
            self.frame_viewer.stop_animation()
            self.update_play_buttons(False)
            QTimer.singleShot(800, self.play_next_gesture_in_phrase)

    def show_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Ayuda — Modo Aprendizaje")
        msg.setIcon(QMessageBox.Information)
        msg.setText("""
<h3 style='color:#7c3aed'>Modo de Aprendizaje</h3>
<p>Observa los frames originales de cada seña y practica imitándolos.</p>

<b>Pasos:</b>
<ol>
<li>Selecciona un gesto del panel izquierdo</li>
<li>Pulsa <b>▶ Reproducir</b> para ver la secuencia</li>
<li>Usa <b>⏮ ⏭</b> para avanzar frame a frame</li>
<li>Ajusta la velocidad con el deslizador</li>
</ol>

<b>Frases:</b>
<p>Agrega varios gestos con <b>+ Agregar</b> y pulsa <b>▶ Frase</b> para reproducirlos en cadena.</p>
        """)
        msg.setStyleSheet("QLabel{min-width:360px; font-size:13px;}")
        msg.exec_()


def main():
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = LearningModeWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
