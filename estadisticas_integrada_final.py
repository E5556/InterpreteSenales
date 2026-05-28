#!/usr/bin/env python3
# =====================================================
# ESTADÍSTICAS INTEGRADA FINAL - InterpreteSenales
# Versión para integración sin advertencias CSS
# =====================================================

import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QWidget, QLabel, QPushButton, QScrollArea,
                             QFrame, QMessageBox, QFileDialog, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from estadisticas_tiempo_real import EstadisticasTiempoReal

class DataWorker(QThread):
    """Worker thread para cargar datos en segundo plano"""
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self):
        super().__init__()
        self.stats_module = EstadisticasTiempoReal()
    
    def run(self):
        """Carga los datos de estadísticas"""
        try:
            self.progress_updated.emit(10, "Iniciando carga de datos...")
            
            # Obtener estadísticas del sistema
            self.progress_updated.emit(30, "Obteniendo estadísticas del sistema...")
            system_stats = self.stats_module.get_estadisticas_sistema_completas()
            
            self.progress_updated.emit(50, "Obteniendo usuarios activos...")
            usuarios_activos = self.stats_module.get_usuarios_mas_activos()
            
            self.progress_updated.emit(70, "Obteniendo patrones temporales...")
            patrones_temporales = self.stats_module.get_sesiones_por_dia()
            
            self.progress_updated.emit(80, "Obteniendo análisis de palabras...")
            analisis_palabras = self.stats_module.get_analisis_palabras()
            
            self.progress_updated.emit(90, "Preparando datos finales...")
            
            # Preparar datos finales
            data = {
                'system': system_stats,
                'usuarios_activos': usuarios_activos,
                'patrones_temporales': patrones_temporales,
                'analisis_palabras': analisis_palabras
            }
            
            self.progress_updated.emit(100, "Datos cargados exitosamente")
            self.data_loaded.emit(data)
            
        except Exception as e:
            print(f"❌ Error en DataWorker: {e}")
            self.error_occurred.emit(str(e))

class EstadisticasIntegradaFinalWindow(QDialog):
    """Ventana de estadísticas integrada completamente estable"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stats_data = None
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Configura la interfaz de usuario sin propiedades CSS problemáticas"""
        self.setWindowTitle("Estadísticas del Sistema - InterpreteSenales")
        self.setFixedSize(1000, 700)
        
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QFrame {
                background-color: #0078D4;
                border: none;
            }
        """)
        
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        title = QLabel("Estadísticas del Sistema")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
        """)
        
        subtitle = QLabel("Análisis completo con tiempo real de uso")
        subtitle.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-family: 'Segoe UI';
            }
        """)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header.setLayout(header_layout)
        main_layout.addWidget(header)
        
        # Contenido principal con scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #f5f5f5;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #e0e0e0;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #0078D4;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #106EBE;
            }
        """)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
        """)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # Panel de controles
        controls_panel = self.create_controls_panel()
        content_layout.addWidget(controls_panel)
        
        # Widget de pestañas
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background-color: #e8f4fd;
            }
        """)
        
        # Crear pestañas
        self.create_tabs()
        content_layout.addWidget(self.tab_widget)
        
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Footer
        footer = QFrame()
        footer.setFixedHeight(40)
        footer.setStyleSheet("""
            QFrame {
                background-color: #0078D4;
                border: none;
            }
        """)
        
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(20, 0, 20, 0)
        
        version_label = QLabel("Versión v2.1.0 - Integrada Estable")
        version_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
        """)
        
        copyright_label = QLabel("© 2024 InterpreteSenales - Sin Errores")
        copyright_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
        """)
        
        footer_layout.addWidget(version_label)
        footer_layout.addStretch()
        footer_layout.addWidget(copyright_label)
        footer.setLayout(footer_layout)
        main_layout.addWidget(footer)
        
        self.setLayout(main_layout)
    
    def create_controls_panel(self):
        """Crea el panel de controles"""
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                padding: 16px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Botón actualizar
        update_btn = QPushButton("🔄 Actualizar")
        update_btn.setFixedHeight(40)
        update_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
        """)
        update_btn.clicked.connect(self.load_data)
        
        # Botón exportar PDF
        export_btn = QPushButton("📄 Exportar PDF")
        export_btn.setFixedHeight(40)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        export_btn.clicked.connect(self.export_to_pdf)
        
        layout.addWidget(update_btn)
        layout.addWidget(export_btn)
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
    
    def create_tabs(self):
        """Crea las pestañas de estadísticas"""
        # Pestaña Resumen Ejecutivo
        summary_tab = self.create_summary_tab()
        self.tab_widget.addTab(summary_tab, "Resumen Ejecutivo")
        
        # Pestaña Usuarios Activos
        users_tab = self.create_users_tab()
        self.tab_widget.addTab(users_tab, "Usuarios Activos")
        
        # Pestaña Patrones Temporales
        temporal_tab = self.create_temporal_tab()
        self.tab_widget.addTab(temporal_tab, "Patrones Temporales")
        
        # Pestaña Análisis de Palabras
        words_tab = self.create_words_analysis_tab()
        self.tab_widget.addTab(words_tab, "Análisis de Palabras")
    
    def create_summary_tab(self):
        """Crea la pestaña de resumen ejecutivo"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Título
        title = QLabel("Métricas Principales")
        title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
        """)
        layout.addWidget(title)
        
        # Grid de métricas
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(16)
        
        # Crear métricas
        self.metrics_widgets = []
        metrics_info = [
            ("👥", "Usuarios Totales", "Cargando...", "Usuarios registrados"),
            ("📝", "Sesiones Activas", "Cargando...", "Sesiones con interpretaciones"),
            ("⏱️", "Tiempo Real", "Cargando...", "Tiempo real de uso"),
            ("🎯", "Precisión", "Cargando...", "Precisión promedio"),
            ("🤲", "Gestos", "Cargando...", "Gestos disponibles"),
            ("📊", "Interpretaciones", "Cargando...", "Interpretaciones realizadas")
        ]
        
        for i, (icon, title_text, value, description) in enumerate(metrics_info):
            metric_widget = self.create_metric_widget(icon, title_text, value, description)
            self.metrics_widgets.append(metric_widget)
            row = i // 3
            col = i % 3
            metrics_grid.addWidget(metric_widget, row, col)
        
        layout.addLayout(metrics_grid)
        
        # Información detallada de tiempo
        tiempo_title = QLabel("Información Detallada de Tiempo")
        tiempo_title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI';
                margin-top: 20px;
            }
        """)
        layout.addWidget(tiempo_title)
        
        self.tiempo_info_widget = QFrame()
        self.tiempo_info_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                padding: 20px;
            }
        """)
        
        tiempo_layout = QVBoxLayout()
        tiempo_layout.setContentsMargins(20, 20, 20, 20)
        
        self.tiempo_label = QLabel("Cargando información de tiempo...")
        self.tiempo_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
                font-family: 'Segoe UI';
                line-height: 1.6;
            }
        """)
        self.tiempo_label.setWordWrap(True)
        
        tiempo_layout.addWidget(self.tiempo_label)
        self.tiempo_info_widget.setLayout(tiempo_layout)
        layout.addWidget(self.tiempo_info_widget)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_users_tab(self):
        """Crea la pestaña de usuarios activos"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        title = QLabel("Usuarios Más Activos")
        title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
        """)
        layout.addWidget(title)
        
        # Tabla de usuarios
        self.users_table = QFrame()
        self.users_table.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                padding: 20px;
            }
        """)
        
        users_layout = QVBoxLayout()
        users_layout.setContentsMargins(20, 20, 20, 20)
        
        self.users_label = QLabel("Cargando usuarios...")
        self.users_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
                font-family: 'Segoe UI';
                line-height: 1.6;
            }
        """)
        self.users_label.setWordWrap(True)
        
        users_layout.addWidget(self.users_label)
        self.users_table.setLayout(users_layout)
        layout.addWidget(self.users_table)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_temporal_tab(self):
        """Crea la pestaña de patrones temporales"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        title = QLabel("Patrones Temporales")
        title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
        """)
        layout.addWidget(title)
        
        # Información temporal
        self.temporal_info_widget = QFrame()
        self.temporal_info_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                padding: 20px;
            }
        """)
        
        temporal_layout = QVBoxLayout()
        temporal_layout.setContentsMargins(20, 20, 20, 20)
        
        self.temporal_label = QLabel("Cargando patrones temporales...")
        self.temporal_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
                font-family: 'Segoe UI';
                line-height: 1.6;
            }
        """)
        self.temporal_label.setWordWrap(True)
        
        temporal_layout.addWidget(self.temporal_label)
        self.temporal_info_widget.setLayout(temporal_layout)
        layout.addWidget(self.temporal_info_widget)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_words_analysis_tab(self):
        """Crea la pestaña de análisis de palabras"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        title = QLabel("Análisis de Palabras")
        title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
        """)
        layout.addWidget(title)
        
        # Estadísticas generales de palabras
        general_stats_title = QLabel("Estadísticas Generales")
        general_stats_title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI';
                margin-top: 10px;
            }
        """)
        layout.addWidget(general_stats_title)
        
        # Widget para estadísticas generales
        self.general_stats_widget = QFrame()
        self.general_stats_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                padding: 20px;
            }
        """)
        
        general_layout = QVBoxLayout()
        general_layout.setContentsMargins(20, 20, 20, 20)
        
        self.general_stats_label = QLabel("Cargando estadísticas generales...")
        self.general_stats_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
                font-family: 'Segoe UI';
                line-height: 1.6;
            }
        """)
        self.general_stats_label.setWordWrap(True)
        
        general_layout.addWidget(self.general_stats_label)
        self.general_stats_widget.setLayout(general_layout)
        layout.addWidget(self.general_stats_widget)
        
        # Top palabras
        top_words_title = QLabel("Palabras Más Interpretadas")
        top_words_title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI';
                margin-top: 20px;
            }
        """)
        layout.addWidget(top_words_title)
        
        # Widget para top palabras
        self.top_words_widget = QFrame()
        self.top_words_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                padding: 20px;
            }
        """)
        
        top_words_layout = QVBoxLayout()
        top_words_layout.setContentsMargins(20, 20, 20, 20)
        
        self.top_words_label = QLabel("Cargando análisis de palabras...")
        self.top_words_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
                font-family: 'Segoe UI';
                line-height: 1.6;
            }
        """)
        self.top_words_label.setWordWrap(True)
        
        top_words_layout.addWidget(self.top_words_label)
        self.top_words_widget.setLayout(top_words_layout)
        layout.addWidget(self.top_words_widget)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_metric_widget(self, icon, title, value, description):
        """Crea un widget de métrica"""
        widget = QFrame()
        widget.setFixedSize(280, 150)
        widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        # Icono y título
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                background-color: transparent;
            }
        """)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
        """)
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Valor
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 28px;
                font-weight: bold;
                font-family: 'Segoe UI';
                margin: 5px 0;
            }
        """)
        
        # Descripción
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
                font-family: 'Segoe UI';
                line-height: 1.4;
            }
        """)
        desc_label.setWordWrap(True)
        
        layout.addLayout(header_layout)
        layout.addWidget(value_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def load_data(self):
        """Carga los datos usando el worker thread"""
        try:
            # Crear y configurar worker
            self.worker = DataWorker()
            self.worker.data_loaded.connect(self.on_data_loaded)
            self.worker.error_occurred.connect(self.on_data_error)
            self.worker.progress_updated.connect(self.on_progress_updated)
            self.worker.start()
            
        except Exception as e:
            print(f"❌ Error al iniciar carga de datos: {e}")
            QMessageBox.critical(self, "Error", f"Error al cargar datos:\n{e}")
    
    def on_data_loaded(self, data):
        """Maneja la carga exitosa de datos"""
        try:
            print(f"✅ Datos cargados exitosamente: {list(data.keys())}")
            self.stats_data = data
            
            # Actualizar métricas principales
            if 'system' in data and isinstance(data['system'], dict):
                self.update_metrics_display(data['system'])
            
            # Actualizar usuarios activos
            if 'usuarios_activos' in data:
                self.update_users_display(data['usuarios_activos'])
            
            # Actualizar patrones temporales
            if 'patrones_temporales' in data:
                self.update_temporal_display(data['patrones_temporales'])
            
            # Actualizar análisis de palabras
            if 'analisis_palabras' in data:
                self.update_words_analysis_display(data['analisis_palabras'])
                
        except Exception as e:
            print(f"❌ Error al procesar datos cargados: {e}")
            QMessageBox.critical(self, "Error", f"Error al procesar datos:\n{e}")
    
    def on_data_error(self, error_message):
        """Maneja errores en la carga de datos"""
        print(f"❌ Error en carga de datos: {error_message}")
        QMessageBox.critical(self, "Error", f"Error al cargar estadísticas:\n{error_message}")
    
    def on_progress_updated(self, value, text):
        """Maneja actualizaciones de progreso"""
        print(f"📊 Progreso: {value}% - {text}")
    
    def update_metrics_display(self, system_stats):
        """Actualiza la visualización de métricas"""
        try:
            # Validar que system_stats sea un diccionario
            if not isinstance(system_stats, dict):
                print(f"❌ Error: system_stats no es un diccionario, es: {type(system_stats)}")
                return
            
            # Verificar claves necesarias
            required_keys = ['usuarios_totales', 'sesiones_activas', 'tiempo_total_horas',
                           'precision_promedio', 'gestos_disponibles', 'interpretaciones_totales']
            
            for key in required_keys:
                if key not in system_stats:
                    print(f"❌ Error: Clave '{key}' no encontrada en system_stats")
                    return
            
            # Preparar datos de métricas
            con_datos = system_stats.get('precision_con_datos', 0)
            sin_datos = system_stats.get('precision_sin_datos', 0)
            metrics_data = [
                str(system_stats['usuarios_totales']),
                str(system_stats['sesiones_activas']),
                f"{system_stats['tiempo_total_horas']}h",
                f"{system_stats['precision_promedio']}%",
                str(system_stats['gestos_disponibles']),
                str(system_stats['interpretaciones_totales'])
            ]
            # Subtítulos actualizados (índice 3 = subtítulo de cada tarjeta)
            metrics_subtitles = [
                "Usuarios registrados",
                "Sesiones con interpretaciones",
                "Tiempo real de uso",
                f"Sobre {con_datos} de {con_datos + sin_datos} interpretaciones",
                "Gestos con modelo entrenado",
                "Interpretaciones realizadas"
            ]

            # Actualizar cada widget de métrica
            for i, metric_widget in enumerate(self.metrics_widgets):
                labels = metric_widget.findChildren(QLabel)
                if len(labels) >= 3:
                    labels[2].setText(metrics_data[i])
                if len(labels) >= 4:
                    labels[3].setText(metrics_subtitles[i])
            
            # Actualizar información detallada de tiempo
            tiempo_info_text = f"""
            <b>📊 Resumen de Tiempo Real:</b><br/>
            • <b>Tiempo total calculado:</b> {system_stats['tiempo_total_horas']} horas<br/>
            • <b>Sesiones con tiempo calculado:</b> {system_stats.get('sesiones_calculadas', 0)}<br/>
            • <b>Sesiones activas:</b> {system_stats['sesiones_activas']}<br/>
            • <b>Sesiones este mes:</b> {system_stats.get('sesiones_mes', 0)}<br/>
            <br/>
            <b>👥 Tiempo por Usuario:</b><br/>
            """
            
            # Agregar tiempo por usuario si está disponible
            if 'tiempo_por_usuario' in system_stats:
                for username, tiempo_segundos in system_stats['tiempo_por_usuario'].items():
                    tiempo_horas = tiempo_segundos / 3600
                    tiempo_minutos = tiempo_segundos / 60
                    tiempo_info_text += f"• <b>{username}:</b> {tiempo_horas:.2f}h ({tiempo_minutos:.0f} min)<br/>"
            
            con_datos = system_stats.get('precision_con_datos', '?')
            sin_datos = system_stats.get('precision_sin_datos', '?')
            tiempo_info_text += f"""
            <br/>
            <b>🎯 Precisión — Detalle:</b><br/>
            • Promedio calculado sobre <b>{con_datos}</b> interpretaciones con confidence registrado<br/>
            • <b>{sin_datos}</b> interpretaciones no tienen confidence (no se incluyen en el promedio)<br/>
            • Si las {sin_datos} sin datos tuvieran baja confianza, el promedio real sería menor<br/>
            <br/>
            <b>📈 Método de Cálculo del Tiempo:</b><br/>
            • Tiempo calculado entre primera y última interpretación de cada sesión<br/>
            • Sesiones con una sola interpretación: 1 minuto mínimo<br/>
            • Sesiones sin interpretaciones: 0 minutos
            """
            
            self.tiempo_label.setText(tiempo_info_text)
            
            print(f"✅ Métricas actualizadas: {system_stats['usuarios_totales']} usuarios, {system_stats['sesiones_activas']} sesiones")
            
        except Exception as e:
            print(f"❌ Error al actualizar métricas: {e}")
    
    def update_users_display(self, usuarios_activos):
        """Actualiza la visualización de usuarios activos"""
        try:
            if not usuarios_activos:
                self.users_label.setText("No hay usuarios activos disponibles.")
                return
            
            users_text = "<b>👥 Usuarios Más Activos:</b><br/><br/>"
            
            for i, usuario in enumerate(usuarios_activos, 1):
                username = usuario.get('username', 'Usuario desconocido')
                sesiones = usuario.get('sesiones', 0)
                tiempo_horas = usuario.get('tiempo_horas', 0)
                interpretaciones = usuario.get('interpretaciones', 0)
                
                users_text += f"""
                <b>{i}. {username}</b><br/>
                • Sesiones: {sesiones}<br/>
                • Tiempo: {tiempo_horas:.2f} horas<br/>
                • Interpretaciones: {interpretaciones}<br/>
                <br/>
                """
            
            self.users_label.setText(users_text)
            print(f"✅ Usuarios actualizados: {len(usuarios_activos)} usuarios")
            
        except Exception as e:
            print(f"❌ Error al actualizar usuarios: {e}")
    
    def update_temporal_display(self, patrones_temporales):
        """Actualiza la visualización de patrones temporales"""
        try:
            if not patrones_temporales:
                self.temporal_label.setText("No hay patrones temporales disponibles.")
                return
            
            temporal_text = "<b>📅 Patrones Temporales por Día:</b><br/><br/>"
            
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            
            # Verificar si patrones_temporales es un diccionario
            if isinstance(patrones_temporales, dict) and len(patrones_temporales) > 0:
                # Ordenar los días de la semana
                orden_dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
                
                for dia in orden_dias:
                    if dia in patrones_temporales:
                        datos = patrones_temporales[dia]
                        sesiones = datos.get('sessions', 0)
                        usuarios_unicos = datos.get('users', 0)
                        interpretaciones = datos.get('interpretations', 0)
                        
                        temporal_text += f"""
                        <b>{dia.capitalize()}</b><br/>
                        • Sesiones: {sesiones}<br/>
                        • Usuarios únicos: {usuarios_unicos}<br/>
                        • Interpretaciones: {interpretaciones}<br/>
                        <br/>
                        """
            else:
                temporal_text += f"No hay datos temporales válidos. Tipo: {type(patrones_temporales)}"
            
            self.temporal_label.setText(temporal_text)
            print(f"✅ Patrones temporales actualizados: {len(patrones_temporales)} días")
            
        except Exception as e:
            print(f"❌ Error al actualizar patrones temporales: {e}")
            self.temporal_label.setText(f"Error al cargar patrones temporales: {e}")
    
    def update_words_analysis_display(self, analisis_palabras):
        """Actualiza la visualización del análisis de palabras"""
        try:
            if not analisis_palabras:
                self.general_stats_label.setText("No hay datos de análisis de palabras disponibles.")
                self.top_words_label.setText("No hay datos de análisis de palabras disponibles.")
                return
            
            # Actualizar estadísticas generales
            stats_generales = analisis_palabras.get('estadisticas_generales', {})
            general_text = f"""
            <b>📊 Resumen General de Palabras:</b><br/>
            • <b>Palabras únicas interpretadas:</b> {stats_generales.get('palabras_unicas', 0)}<br/>
            • <b>Total de interpretaciones:</b> {stats_generales.get('total_interpretaciones', 0)}<br/>
            • <b>Precisión general:</b> {stats_generales.get('precision_general', 0)}%<br/>
            • <b>Usuarios activos:</b> {stats_generales.get('usuarios_activos', 0)}<br/>
            <br/>
            <b>📈 Insights:</b><br/>
            • Promedio de interpretaciones por palabra: {stats_generales.get('total_interpretaciones', 0) / max(stats_generales.get('palabras_unicas', 1), 1):.1f}<br/>
            • Diversidad de vocabulario: {stats_generales.get('palabras_unicas', 0)} palabras diferentes<br/>
            """
            
            self.general_stats_label.setText(general_text)
            
            # Actualizar top palabras
            palabras_top = analisis_palabras.get('palabras_top', [])
            if palabras_top:
                top_words_text = "<b>🏆 Top 20 Palabras Más Interpretadas:</b><br/><br/>"
                
                for i, palabra_data in enumerate(palabras_top, 1):
                    palabra = palabra_data.get('palabra', 'N/A')
                    total = palabra_data.get('total_interpretaciones', 0)
                    precision = palabra_data.get('precision_promedio', 0)
                    usuarios = palabra_data.get('usuarios_unicos', 0)
                    dias = palabra_data.get('dias_activos', 0)
                    correctas = palabra_data.get('interpretaciones_correctas', 0)
                    porcentaje_exito = palabra_data.get('porcentaje_exito', 0)
                    tiempo_proc = palabra_data.get('tiempo_procesamiento_promedio', 0)
                    
                    # Emoji basado en la posición
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    
                    top_words_text += f"""
                    <b>{emoji} {palabra}</b><br/>
                    • Interpretaciones: {total}<br/>
                    • Precisión: {precision}%<br/>
                    • Usuarios únicos: {usuarios}<br/>
                    • Días activos: {dias}<br/>
                    • Correctas: {correctas} ({porcentaje_exito}%)<br/>
                    • Tiempo promedio: {tiempo_proc}ms<br/>
                    <br/>
                    """
                
                self.top_words_label.setText(top_words_text)
                print(f"✅ Análisis de palabras actualizado: {len(palabras_top)} palabras")
            else:
                self.top_words_label.setText("No hay datos de palabras disponibles.")
            
        except Exception as e:
            print(f"❌ Error al actualizar análisis de palabras: {e}")
            self.general_stats_label.setText(f"Error al cargar estadísticas generales: {e}")
            self.top_words_label.setText(f"Error al cargar análisis de palabras: {e}")
    
    def export_to_pdf(self):
        """Exporta las estadísticas a PDF"""
        try:
            if not self.stats_data:
                QMessageBox.warning(self, "Advertencia", "No hay datos para exportar. Cargue las estadísticas primero.")
                return
            
            # Seleccionar carpeta
            folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para guardar PDF")
            if not folder:
                return
            
            # Generar PDF
            stats_module = EstadisticasTiempoReal()
            filename = f"estadisticas_integrada_{stats_module.get_estadisticas_sistema_completas()['timestamp'].replace(':', '-').replace(' ', '_')}.pdf"
            filepath = stats_module.exportar_a_pdf(folder, filename, True)
            
            if filepath:
                QMessageBox.information(self, "Éxito", f"PDF generado exitosamente:\n{filepath}")
            else:
                QMessageBox.warning(self, "Error", "No se pudo generar el PDF")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al exportar PDF:\n{e}")

def show_integrated_statistics():
    """Muestra la ventana de estadísticas integrada"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    window = EstadisticasIntegradaFinalWindow()
    window.exec_()

if __name__ == "__main__":
    show_integrated_statistics()

