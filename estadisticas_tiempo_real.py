#!/usr/bin/env python3
# =====================================================
# ESTADÍSTICAS TIEMPO REAL - InterpreteSenales
# Módulo que calcula el tiempo real de uso del sistema
# =====================================================

import sqlite3
import json
import os
import subprocess
import platform
from datetime import datetime, timedelta
from config import get_database_path
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io

class EstadisticasTiempoReal:
    """Módulo de estadísticas que calcula el tiempo real de uso"""
    
    def __init__(self):
        self.db_path = get_database_path()
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def get_connection(self):
        """Obtiene conexión a la base de datos"""
        return sqlite3.connect(self.db_path)
    
    def safe_divide(self, numerator, denominator, default=0):
        """División segura que maneja None y cero"""
        if denominator is None or denominator == 0:
            return default
        if numerator is None:
            return default
        return numerator / denominator
    
    def safe_round(self, value, decimals=1, default=0):
        """Redondeo seguro que maneja None"""
        if value is None:
            return default
        try:
            return round(float(value), decimals)
        except (ValueError, TypeError):
            return default
    
    def calcular_tiempo_real_uso(self):
        """Calcula el tiempo real de uso basado en interpretaciones"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Obtener sesiones con interpretaciones y sus timestamps
            cursor.execute("""
                SELECT 
                    s.id as session_id,
                    s.user_id,
                    u.username,
                    COUNT(i.id) as total_interpretaciones,
                    MIN(i.timestamp) as primera_interpretacion,
                    MAX(i.timestamp) as ultima_interpretacion
                FROM sessions s
                LEFT JOIN interpretations i ON s.id = i.session_id
                LEFT JOIN users u ON s.user_id = u.id
                WHERE i.timestamp IS NOT NULL
                GROUP BY s.id, s.user_id, u.username
                HAVING COUNT(i.id) > 0
                ORDER BY s.id
            """)
            
            sesiones_con_tiempo = cursor.fetchall()
            
            tiempo_total_segundos = 0
            sesiones_calculadas = 0
            tiempo_por_usuario = {}
            
            for sesion in sesiones_con_tiempo:
                session_id, user_id, username, total_interp, primera_interp, ultima_interp = sesion
                
                tiempo_sesion = 0
                
                if primera_interp and ultima_interp:
                    try:
                        primera = datetime.strptime(primera_interp, '%Y-%m-%d %H:%M:%S')
                        ultima = datetime.strptime(ultima_interp, '%Y-%m-%d %H:%M:%S')
                        tiempo_sesion = (ultima - primera).total_seconds()
                        
                        # Si el tiempo es muy pequeño (menos de 10 segundos), asumir tiempo mínimo
                        if tiempo_sesion < 10:
                            tiempo_sesion = max(60, total_interp * 10)  # Mínimo 1 minuto o 10 segundos por interpretación
                        
                    except Exception as e:
                        # Si hay error en el parsing, usar tiempo estimado
                        tiempo_sesion = max(60, total_interp * 10)
                
                # Si solo hay una interpretación, asumir 1 minuto
                elif total_interp == 1:
                    tiempo_sesion = 60
                
                if tiempo_sesion > 0:
                    tiempo_total_segundos += tiempo_sesion
                    sesiones_calculadas += 1
                    
                    # Acumular tiempo por usuario
                    if username not in tiempo_por_usuario:
                        tiempo_por_usuario[username] = 0
                    tiempo_por_usuario[username] += tiempo_sesion
            
            conn.close()
            
            tiempo_total_horas = self.safe_round(tiempo_total_segundos / 3600, 2)
            
            return {
                'tiempo_total_segundos': tiempo_total_segundos,
                'tiempo_total_horas': tiempo_total_horas,
                'sesiones_calculadas': sesiones_calculadas,
                'tiempo_por_usuario': tiempo_por_usuario
            }
            
        except Exception as e:
            print(f"Error al calcular tiempo real: {e}")
            return {
                'tiempo_total_segundos': 0,
                'tiempo_total_horas': 0,
                'sesiones_calculadas': 0,
                'tiempo_por_usuario': {}
            }
    
    def get_estadisticas_sistema_completas(self):
        """Obtiene estadísticas completas del sistema con tiempo real"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Usuarios totales
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            total_users = cursor.fetchone()[0] or 0
            
            # Sesiones totales
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0] or 0
            
            # Calcular tiempo real de uso
            tiempo_real = self.calcular_tiempo_real_uso()
            
            # Precisión promedio (de interpretations)
            cursor.execute("""
                SELECT AVG(confidence_score) 
                FROM interpretations 
                WHERE confidence_score IS NOT NULL
            """)
            avg_confidence = cursor.fetchone()[0]
            precision_percentage = self.safe_round((avg_confidence or 0) * 100, 1)
            
            # Gestos disponibles — solo los que tienen keypoints entrenados (.h5)
            import os as _os
            try:
                from constants import KEYPOINTS_PATH
                total_gestures = len([f for f in _os.listdir(KEYPOINTS_PATH) if f.endswith('.h5')])
            except Exception:
                cursor.execute("SELECT COUNT(*) FROM gestures WHERE is_active = 1")
                total_gestures = cursor.fetchone()[0] or 0
            
            # Interpretaciones totales
            cursor.execute("SELECT COUNT(*) FROM interpretations")
            total_interpretations = cursor.fetchone()[0] or 0
            
            # Sesiones este mes
            cursor.execute("""
                SELECT COUNT(*) FROM sessions 
                WHERE created_at >= date('now', 'start of month')
            """)
            sessions_this_month = cursor.fetchone()[0] or 0
            
            # Usuarios activos este mes
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) FROM sessions 
                WHERE created_at >= date('now', 'start of month')
            """)
            active_users_this_month = cursor.fetchone()[0] or 0
            
            # Última sesión
            cursor.execute("""
                SELECT MAX(start_time) FROM sessions 
                WHERE start_time IS NOT NULL
            """)
            last_session = cursor.fetchone()[0]
            
            # Sesiones con interpretaciones (sesiones activas)
            cursor.execute("""
                SELECT COUNT(DISTINCT s.id) FROM sessions s
                INNER JOIN interpretations i ON s.id = i.session_id
            """)
            active_sessions = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'usuarios_totales': total_users,
                'usuarios_activos_mes': active_users_this_month,
                'sesiones_totales': total_sessions,
                'sesiones_activas': active_sessions,
                'sesiones_mes': sessions_this_month,
                'tiempo_total_horas': tiempo_real['tiempo_total_horas'],
                'tiempo_total_segundos': tiempo_real['tiempo_total_segundos'],
                'sesiones_calculadas': tiempo_real['sesiones_calculadas'],
                'tiempo_por_usuario': tiempo_real['tiempo_por_usuario'],
                'precision_promedio': precision_percentage,
                'gestos_disponibles': total_gestures,
                'interpretaciones_totales': total_interpretations,
                'ultima_sesion': last_session,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            print(f"Error al obtener estadísticas completas: {e}")
            return {
                'usuarios_totales': 0,
                'usuarios_activos_mes': 0,
                'sesiones_totales': 0,
                'sesiones_activas': 0,
                'sesiones_mes': 0,
                'tiempo_total_horas': 0,
                'tiempo_total_segundos': 0,
                'sesiones_calculadas': 0,
                'tiempo_por_usuario': {},
                'precision_promedio': 0,
                'gestos_disponibles': 0,
                'interpretaciones_totales': 0,
                'ultima_sesion': None,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def get_usuarios_mas_activos(self):
        """Obtiene los usuarios más activos con tiempo real"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Obtener estadísticas de tiempo real
            tiempo_real = self.calcular_tiempo_real_uso()
            
            cursor.execute("""
                SELECT 
                    u.username,
                    u.first_name,
                    u.last_name,
                    COUNT(s.id) as total_sesiones,
                    COUNT(i.id) as total_interpretaciones,
                    AVG(i.confidence_score) as precision_promedio,
                    MAX(s.start_time) as ultima_sesion
                FROM users u
                LEFT JOIN sessions s ON u.id = s.user_id
                LEFT JOIN interpretations i ON s.id = i.session_id
                WHERE u.is_active = 1
                GROUP BY u.id, u.username, u.first_name, u.last_name
                ORDER BY total_interpretaciones DESC, total_sesiones DESC
                LIMIT 10
            """)
            
            usuarios = []
            for row in cursor.fetchall():
                username, first_name, last_name, sesiones, interpretaciones, precision, ultima_sesion = row
                
                # Formatear nombre
                nombre_completo = f"{first_name or ''} {last_name or ''}".strip()
                if not nombre_completo:
                    nombre_completo = username
                
                # Obtener tiempo real del usuario
                tiempo_usuario_horas = self.safe_round(tiempo_real['tiempo_por_usuario'].get(username, 0) / 3600, 2)
                
                # Formatear precisión
                precision_pct = self.safe_round((precision or 0) * 100, 1)
                
                usuarios.append({
                    'username': username,
                    'nombre_completo': nombre_completo,
                    'sesiones': sesiones or 0,
                    'interpretaciones': interpretaciones or 0,
                    'tiempo_horas': tiempo_usuario_horas,
                    'precision': precision_pct,
                    'ultima_sesion': ultima_sesion
                })
            
            conn.close()
            return usuarios
            
        except Exception as e:
            print(f"Error al obtener usuarios activos: {e}")
            return []
    
    def get_sesiones_por_dia(self):
        """Obtiene las sesiones agrupadas por día de la semana"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Obtener sesiones por día de la semana
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN strftime('%w', s.start_time) = '0' THEN 'domingo'
                        WHEN strftime('%w', s.start_time) = '1' THEN 'lunes'
                        WHEN strftime('%w', s.start_time) = '2' THEN 'martes'
                        WHEN strftime('%w', s.start_time) = '3' THEN 'miércoles'
                        WHEN strftime('%w', s.start_time) = '4' THEN 'jueves'
                        WHEN strftime('%w', s.start_time) = '5' THEN 'viernes'
                        WHEN strftime('%w', s.start_time) = '6' THEN 'sábado'
                        ELSE 'desconocido'
                    END as dia_semana,
                    COUNT(s.id) as total_sesiones,
                    COUNT(DISTINCT s.user_id) as usuarios_unicos,
                    COUNT(i.id) as total_interpretaciones
                FROM sessions s
                LEFT JOIN interpretations i ON s.id = i.session_id
                WHERE s.start_time IS NOT NULL
                GROUP BY strftime('%w', s.start_time)
                ORDER BY strftime('%w', s.start_time)
            """)
            
            sesiones_por_dia = {}
            for row in cursor.fetchall():
                dia, sesiones, usuarios, interpretaciones = row
                sesiones_por_dia[dia] = {
                    'sessions': sesiones or 0,
                    'users': usuarios or 0,
                    'interpretations': interpretaciones or 0,
                    'time': '0.0h',  # Placeholder
                    'accuracy': '94.8%'  # Placeholder
                }
            
            conn.close()
            return sesiones_por_dia
            
        except Exception as e:
            print(f"Error al obtener sesiones por día: {e}")
            return {}
    
    def get_analisis_palabras(self):
        """Obtiene análisis detallado de las palabras más interpretadas"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Palabras más interpretadas con estadísticas detalladas
            cursor.execute("""
                SELECT 
                    word_detected,
                    COUNT(*) as total_interpretaciones,
                    AVG(confidence_score) as precision_promedio,
                    COUNT(DISTINCT s.user_id) as usuarios_unicos,
                    COUNT(DISTINCT DATE(s.start_time)) as dias_activos,
                    SUM(CASE WHEN i.is_correct = 1 THEN 1 ELSE 0 END) as interpretaciones_correctas,
                    AVG(processing_time_ms) as tiempo_procesamiento_promedio,
                    MIN(i.timestamp) as primera_interpretacion,
                    MAX(i.timestamp) as ultima_interpretacion
                FROM interpretations i
                LEFT JOIN sessions s ON i.session_id = s.id
                WHERE word_detected IS NOT NULL AND word_detected != ''
                GROUP BY word_detected
                ORDER BY total_interpretaciones DESC
                LIMIT 20
            """)
            
            palabras_analisis = []
            for row in cursor.fetchall():
                palabra, total, precision, usuarios, dias, correctas, tiempo_proc, primera, ultima = row
                
                # Calcular porcentaje de éxito
                porcentaje_exito = self.safe_round((correctas or 0) / (total or 1) * 100, 1)
                
                palabras_analisis.append({
                    'palabra': palabra,
                    'total_interpretaciones': total or 0,
                    'precision_promedio': self.safe_round((precision or 0) * 100, 1),
                    'usuarios_unicos': usuarios or 0,
                    'dias_activos': dias or 0,
                    'interpretaciones_correctas': correctas or 0,
                    'porcentaje_exito': porcentaje_exito,
                    'tiempo_procesamiento_promedio': self.safe_round(tiempo_proc or 0, 1),
                    'primera_interpretacion': primera,
                    'ultima_interpretacion': ultima
                })
            
            # Estadísticas generales de palabras
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT word_detected) as palabras_unicas,
                    COUNT(*) as total_interpretaciones,
                    AVG(confidence_score) as precision_general,
                    COUNT(DISTINCT s.user_id) as usuarios_activos_palabras
                FROM interpretations i
                LEFT JOIN sessions s ON i.session_id = s.id
                WHERE word_detected IS NOT NULL AND word_detected != ''
            """)
            
            stats_generales = cursor.fetchone()
            if stats_generales:
                palabras_unicas, total_interp, precision_gen, usuarios_activos = stats_generales
                estadisticas_generales = {
                    'palabras_unicas': palabras_unicas or 0,
                    'total_interpretaciones': total_interp or 0,
                    'precision_general': self.safe_round((precision_gen or 0) * 100, 1),
                    'usuarios_activos': usuarios_activos or 0
                }
            else:
                estadisticas_generales = {
                    'palabras_unicas': 0,
                    'total_interpretaciones': 0,
                    'precision_general': 0,
                    'usuarios_activos': 0
                }
            
            conn.close()
            
            return {
                'palabras_top': palabras_analisis,
                'estadisticas_generales': estadisticas_generales,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            print(f"Error al obtener análisis de palabras: {e}")
            return {
                'palabras_top': [],
                'estadisticas_generales': {},
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def exportar_a_pdf(self, output_dir=None, filename=None, abrir_automaticamente=True):
        """Exporta las estadísticas con tiempo real a PDF"""
        try:
            # Obtener datos reales con tiempo calculado
            stats = self.get_estadisticas_sistema_completas()
            usuarios_activos = self.get_usuarios_mas_activos()
            
            # Configurar archivo de salida
            if not output_dir:
                output_dir = os.path.expanduser("~/Desktop")
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"estadisticas_tiempo_real_{timestamp}.pdf"
            
            filepath = os.path.join(output_dir, filename)
            
            # Crear documento PDF
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#0078D4')
            )
            story.append(Paragraph("Estadísticas con Tiempo Real de Uso", title_style))
            story.append(Paragraph("InterpreteSenales - Análisis Completo del Sistema", styles['Heading2']))
            story.append(Spacer(1, 20))
            
            # Resumen ejecutivo con tiempo real
            story.append(Paragraph("Resumen Ejecutivo", styles['Heading2']))
            resumen_text = f"""
            <b>Fecha de generación:</b> {stats['timestamp']}<br/>
            <b>Usuarios totales:</b> {stats['usuarios_totales']}<br/>
            <b>Usuarios activos este mes:</b> {stats['usuarios_activos_mes']}<br/>
            <b>Sesiones totales:</b> {stats['sesiones_totales']}<br/>
            <b>Sesiones activas (con interpretaciones):</b> {stats['sesiones_activas']}<br/>
            <b>Sesiones este mes:</b> {stats['sesiones_mes']}<br/>
            <b>Tiempo real de uso:</b> {stats['tiempo_total_horas']} horas ({stats['tiempo_total_segundos']:.0f} segundos)<br/>
            <b>Sesiones con tiempo calculado:</b> {stats['sesiones_calculadas']}<br/>
            <b>Precisión promedio:</b> {stats['precision_promedio']}%<br/>
            <b>Interpretaciones totales:</b> {stats['interpretaciones_totales']}<br/>
            <b>Última sesión:</b> {stats['ultima_sesion'] or 'N/A'}<br/>
            """
            story.append(Paragraph(resumen_text, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Tiempo por usuario
            if stats['tiempo_por_usuario']:
                story.append(Paragraph("Tiempo de Uso por Usuario", styles['Heading2']))
                
                tiempo_data = [['Usuario', 'Tiempo (horas)', 'Tiempo (minutos)', 'Porcentaje']]
                tiempo_total_horas = stats['tiempo_total_horas']
                
                for username, tiempo_segundos in stats['tiempo_por_usuario'].items():
                    tiempo_horas = tiempo_segundos / 3600
                    tiempo_minutos = tiempo_segundos / 60
                    porcentaje = (tiempo_segundos / stats['tiempo_total_segundos'] * 100) if stats['tiempo_total_segundos'] > 0 else 0
                    
                    tiempo_data.append([
                        username,
                        f"{tiempo_horas:.2f}",
                        f"{tiempo_minutos:.0f}",
                        f"{porcentaje:.1f}%"
                    ])
                
                tiempo_table = Table(tiempo_data)
                tiempo_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0078D4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(tiempo_table)
                story.append(Spacer(1, 20))
            
            # Usuarios más activos
            if usuarios_activos:
                story.append(Paragraph("Usuarios Más Activos", styles['Heading2']))
                
                user_data = [['Usuario', 'Sesiones', 'Interpretaciones', 'Tiempo (h)', 'Precisión (%)', 'Última Sesión']]
                for usuario in usuarios_activos[:10]:
                    user_data.append([
                        usuario['nombre_completo'],
                        str(usuario['sesiones']),
                        str(usuario['interpretaciones']),
                        str(usuario['tiempo_horas']),
                        str(usuario['precision']),
                        usuario['ultima_sesion'] or 'N/A'
                    ])
                
                user_table = Table(user_data)
                user_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28A745')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(user_table)
                story.append(Spacer(1, 20))
            
            # Pie de página
            story.append(Paragraph(f"Reporte generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}", styles['Normal']))
            story.append(Paragraph("InterpreteSenales - Sistema de Interpretación de Lengua de Señas", styles['Normal']))
            
            # Construir PDF
            doc.build(story)
            
            print(f"✅ PDF generado exitosamente: {filepath}")
            
            # Abrir automáticamente si se solicita
            if abrir_automaticamente:
                self.abrir_archivo(filepath)
            
            return filepath
            
        except Exception as e:
            print(f"❌ Error al generar PDF: {e}")
            return None
    
    def abrir_archivo(self, filepath):
        """Abre el archivo PDF generado"""
        try:
            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", filepath])
            else:  # Linux
                subprocess.run(["xdg-open", filepath])
        except Exception as e:
            print(f"Error al abrir archivo: {e}")

def main():
    """Función principal para probar el módulo"""
    stats = EstadisticasTiempoReal()
    
    print("📊 ESTADÍSTICAS CON TIEMPO REAL")
    print("=" * 50)
    
    # Obtener estadísticas
    datos = stats.get_estadisticas_sistema_completas()
    
    print(f"👥 Usuarios totales: {datos['usuarios_totales']}")
    print(f"👥 Usuarios activos este mes: {datos['usuarios_activos_mes']}")
    print(f"📝 Sesiones totales: {datos['sesiones_totales']}")
    print(f"📝 Sesiones activas: {datos['sesiones_activas']}")
    print(f"📝 Sesiones este mes: {datos['sesiones_mes']}")
    print(f"⏱️ Tiempo real de uso: {datos['tiempo_total_horas']} horas ({datos['tiempo_total_segundos']:.0f} segundos)")
    print(f"📊 Sesiones calculadas: {datos['sesiones_calculadas']}")
    print(f"🎯 Precisión promedio: {datos['precision_promedio']}%")
    print(f"🤲 Gestos disponibles: {datos['gestos_disponibles']}")
    print(f"📊 Interpretaciones totales: {datos['interpretaciones_totales']}")
    print(f"🕒 Última sesión: {datos['ultima_sesion'] or 'N/A'}")
    
    print("\n👥 TIEMPO POR USUARIO:")
    for username, tiempo_segundos in datos['tiempo_por_usuario'].items():
        tiempo_horas = tiempo_segundos / 3600
        print(f"   {username}: {tiempo_horas:.2f} horas ({tiempo_segundos:.0f} segundos)")
    
    print("\n👥 USUARIOS MÁS ACTIVOS:")
    usuarios = stats.get_usuarios_mas_activos()
    for i, usuario in enumerate(usuarios[:5], 1):
        print(f"{i}. {usuario['nombre_completo']} - {usuario['sesiones']} sesiones, {usuario['interpretaciones']} interpretaciones, {usuario['tiempo_horas']}h")
    
    # Generar PDF
    print("\n📄 Generando PDF...")
    pdf_path = stats.exportar_a_pdf()
    if pdf_path:
        print(f"✅ PDF generado: {pdf_path}")

if __name__ == "__main__":
    main()
