#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas de rendimiento y estrés para el sistema de gestos simplificado
Prueba la eficiencia y escalabilidad del sistema
"""

import time
import os
import tempfile
import shutil
import sys
from unittest.mock import patch
import statistics

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from training_utils import get_gestures_with_samples, create_keypoints_for_all_gestures
from constants import get_display_text
from database import init_db, add_user, create_session, add_interpretation


class PerformanceTestSuite:
    """Suite de pruebas de rendimiento"""
    
    def __init__(self):
        self.results = {}
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Configurar entorno temporal para pruebas"""
        self.test_dir = tempfile.mkdtemp()
        self.frame_actions_path = os.path.join(self.test_dir, "frame_actions")
        self.keypoints_path = os.path.join(self.test_dir, "keypoints")
        os.makedirs(self.frame_actions_path)
        os.makedirs(self.keypoints_path)
        
        # Base de datos temporal
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Aplicar patches
        self.patches = [
            patch('training_utils.FRAME_ACTIONS_PATH', self.frame_actions_path),
            patch('training_utils.KEYPOINTS_PATH', self.keypoints_path),
            patch('database.DATABASE_NAME', self.test_db_path)
        ]
        
        for p in self.patches:
            p.start()
        
        # Inicializar base de datos
        init_db()
    
    def cleanup(self):
        """Limpiar entorno de prueba"""
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.test_dir)
        os.unlink(self.test_db_path)
    
    def create_test_gestures(self, num_gestures, samples_per_gesture=5, frames_per_sample=15):
        """Crear gestos de prueba"""
        for i in range(num_gestures):
            gesture_name = f"gesto_{i:03d}"
            gesture_path = os.path.join(self.frame_actions_path, gesture_name)
            os.makedirs(gesture_path)
            
            for j in range(samples_per_gesture):
                sample_path = os.path.join(gesture_path, f"sample_{j:03d}")
                os.makedirs(sample_path)
                
                for k in range(frames_per_sample):
                    frame_file = os.path.join(sample_path, f"frame_{k:02d}.jpg")
                    with open(frame_file, 'w') as f:
                        f.write(f"fake_data_{i}_{j}_{k}")
    
    def time_function(self, func, *args, **kwargs):
        """Medir tiempo de ejecución de una función"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    def test_gesture_detection_scalability(self):
        """Probar escalabilidad de detección de gestos"""
        print("🔍 Probando escalabilidad de detección de gestos...")
        
        gesture_counts = [1, 5, 10, 20, 50, 100]
        detection_times = []
        
        for count in gesture_counts:
            # Limpiar y crear gestos
            if os.path.exists(self.frame_actions_path):
                shutil.rmtree(self.frame_actions_path)
            os.makedirs(self.frame_actions_path)
            
            self.create_test_gestures(count)
            
            # Medir tiempo de detección
            _, detection_time = self.time_function(get_gestures_with_samples)
            detection_times.append(detection_time)
            
            print(f"  {count:3d} gestos: {detection_time:.4f}s")
        
        # Analizar resultados
        avg_time_per_gesture = statistics.mean([t/c for t, c in zip(detection_times, gesture_counts)])
        
        self.results['gesture_detection'] = {
            'gesture_counts': gesture_counts,
            'detection_times': detection_times,
            'avg_time_per_gesture': avg_time_per_gesture,
            'max_time': max(detection_times),
            'scalability': detection_times[-1] / detection_times[0]  # Factor de escalamiento
        }
        
        print(f"  Tiempo promedio por gesto: {avg_time_per_gesture:.6f}s")
        print(f"  Factor de escalamiento (100 vs 1): {self.results['gesture_detection']['scalability']:.2f}x")
    
    def test_display_text_performance(self):
        """Probar rendimiento de conversión de texto"""
        print("\n📝 Probando rendimiento de conversión de texto...")
        
        # Crear diferentes tipos de nombres de gestos
        test_cases = [
            "simple",
            "con_guiones_bajos",
            "muy_largo_nombre_de_gesto_con_muchas_palabras",
            "MAYUSCULAS_Y_minusculas_MeZcLaDaS",
            "_inicio_y_final_",
            "numeros_123_en_medio"
        ]
        
        iterations = 10000
        times = []
        
        for test_case in test_cases:
            start_time = time.time()
            for _ in range(iterations):
                get_display_text(test_case)
            end_time = time.time()
            
            total_time = end_time - start_time
            avg_time = total_time / iterations
            times.append(avg_time)
            
            print(f"  '{test_case}': {avg_time:.8f}s por conversión")
        
        self.results['display_text'] = {
            'avg_times': times,
            'max_time': max(times),
            'min_time': min(times),
            'iterations': iterations
        }
        
        print(f"  Tiempo promedio: {statistics.mean(times):.8f}s")
        print(f"  {iterations} conversiones en {sum(times) * iterations:.4f}s")
    
    def test_database_performance(self):
        """Probar rendimiento de operaciones de base de datos"""
        print("\n💾 Probando rendimiento de base de datos...")
        
        # Probar inserción de usuarios
        num_users = 100
        start_time = time.time()
        user_ids = []
        
        for i in range(num_users):
            user_id = add_user(
                username=f"user_{i:03d}",
                password=f"password_{i}",
                first_name=f"User",
                last_name=f"{i}",
                email=f"user{i}@test.com"
            )
            user_ids.append(user_id)
        
        user_creation_time = time.time() - start_time
        
        # Probar creación de sesiones
        start_time = time.time()
        session_ids = []
        
        for user_id in user_ids[:50]:  # Solo primeros 50 usuarios
            session_id = create_session(user_id)
            session_ids.append(session_id)
        
        session_creation_time = time.time() - start_time
        
        # Probar inserción de interpretaciones
        start_time = time.time()
        interpretations_per_session = 20
        
        for session_id in session_ids[:25]:  # Solo primeras 25 sesiones
            for j in range(interpretations_per_session):
                gesture_name = f"GESTO_{j}"
                add_interpretation(session_id, gesture_name)
        
        interpretation_time = time.time() - start_time
        
        self.results['database'] = {
            'user_creation_time': user_creation_time,
            'session_creation_time': session_creation_time,
            'interpretation_time': interpretation_time,
            'users_per_second': num_users / user_creation_time,
            'sessions_per_second': 50 / session_creation_time,
            'interpretations_per_second': (25 * interpretations_per_session) / interpretation_time
        }
        
        print(f"  {num_users} usuarios creados en {user_creation_time:.4f}s ({self.results['database']['users_per_second']:.1f} usuarios/s)")
        print(f"  50 sesiones creadas en {session_creation_time:.4f}s ({self.results['database']['sessions_per_second']:.1f} sesiones/s)")
        print(f"  {25 * interpretations_per_session} interpretaciones en {interpretation_time:.4f}s ({self.results['database']['interpretations_per_second']:.1f} interp/s)")
    
    def test_memory_usage(self):
        """Probar uso de memoria del sistema"""
        print("\n🧠 Probando uso de memoria...")
        
        try:
            import psutil
            import gc
            
            # Medir memoria inicial
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Crear muchos gestos y procesar
            self.create_test_gestures(50, samples_per_gesture=10)
            
            # Medir memoria después de crear gestos
            after_creation_memory = process.memory_info().rss / 1024 / 1024
            
            # Ejecutar detección múltiples veces
            for _ in range(100):
                get_gestures_with_samples()
            
            # Medir memoria después de detección
            after_detection_memory = process.memory_info().rss / 1024 / 1024
            
            # Limpiar y medir
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024
            
            self.results['memory'] = {
                'initial_mb': initial_memory,
                'after_creation_mb': after_creation_memory,
                'after_detection_mb': after_detection_memory,
                'final_mb': final_memory,
                'max_increase_mb': max(after_creation_memory, after_detection_memory) - initial_memory
            }
            
            print(f"  Memoria inicial: {initial_memory:.1f} MB")
            print(f"  Después de crear gestos: {after_creation_memory:.1f} MB (+{after_creation_memory - initial_memory:.1f} MB)")
            print(f"  Después de detección: {after_detection_memory:.1f} MB")
            print(f"  Memoria final: {final_memory:.1f} MB")
            print(f"  Aumento máximo: {self.results['memory']['max_increase_mb']:.1f} MB")
            
        except ImportError:
            print("  ⚠️ psutil no disponible - saltando prueba de memoria")
            self.results['memory'] = None
    
    def test_concurrent_operations(self):
        """Probar operaciones concurrentes simuladas"""
        print("\n🔄 Probando operaciones concurrentes...")
        
        # Simular múltiples operaciones rápidas
        num_operations = 1000
        
        # Test 1: Detección de gestos rápida
        self.create_test_gestures(10)
        
        start_time = time.time()
        for _ in range(num_operations):
            get_gestures_with_samples()
        detection_time = time.time() - start_time
        
        # Test 2: Conversión de texto rápida
        test_gestures = ["hola", "adios", "por_favor", "buenos_dias", "buenas_noches"]
        
        start_time = time.time()
        for _ in range(num_operations):
            for gesture in test_gestures:
                get_display_text(gesture)
        conversion_time = time.time() - start_time
        
        self.results['concurrent'] = {
            'detection_ops_per_second': num_operations / detection_time,
            'conversion_ops_per_second': (num_operations * len(test_gestures)) / conversion_time,
            'total_detection_time': detection_time,
            'total_conversion_time': conversion_time
        }
        
        print(f"  {num_operations} detecciones en {detection_time:.4f}s ({self.results['concurrent']['detection_ops_per_second']:.1f} ops/s)")
        print(f"  {num_operations * len(test_gestures)} conversiones en {conversion_time:.4f}s ({self.results['concurrent']['conversion_ops_per_second']:.1f} ops/s)")
    
    def generate_report(self):
        """Generar reporte de rendimiento"""
        print("\n" + "="*60)
        print("📊 REPORTE DE RENDIMIENTO")
        print("="*60)
        
        # Análisis de resultados
        issues = []
        recommendations = []
        
        # Analizar detección de gestos
        if 'gesture_detection' in self.results:
            gd = self.results['gesture_detection']
            if gd['avg_time_per_gesture'] > 0.001:  # >1ms por gesto
                issues.append(f"Detección lenta: {gd['avg_time_per_gesture']:.6f}s por gesto")
            if gd['scalability'] > 10:  # Factor de escalamiento alto
                issues.append(f"Escalabilidad pobre: {gd['scalability']:.1f}x más lento con 100 gestos")
        
        # Analizar base de datos
        if 'database' in self.results:
            db = self.results['database']
            if db['users_per_second'] < 50:
                issues.append(f"Creación de usuarios lenta: {db['users_per_second']:.1f} usuarios/s")
            if db['interpretations_per_second'] < 100:
                issues.append(f"Inserción de interpretaciones lenta: {db['interpretations_per_second']:.1f} interp/s")
        
        # Analizar memoria
        if self.results.get('memory'):
            mem = self.results['memory']
            if mem['max_increase_mb'] > 100:
                issues.append(f"Alto uso de memoria: +{mem['max_increase_mb']:.1f} MB")
        
        # Generar recomendaciones
        if len(issues) == 0:
            recommendations.append("✅ Rendimiento excelente en todas las áreas")
        else:
            if any("Detección lenta" in issue for issue in issues):
                recommendations.append("Considerar cache para detección de gestos")
            if any("base de datos" in issue.lower() for issue in issues):
                recommendations.append("Optimizar consultas de base de datos con índices")
            if any("memoria" in issue.lower() for issue in issues):
                recommendations.append("Implementar garbage collection más frecuente")
        
        # Mostrar reporte
        print("🎯 MÉTRICAS CLAVE:")
        if 'gesture_detection' in self.results:
            print(f"  • Detección de gestos: {self.results['gesture_detection']['avg_time_per_gesture']*1000:.2f}ms por gesto")
        
        if 'database' in self.results:
            print(f"  • Throughput DB: {self.results['database']['interpretations_per_second']:.0f} interpretaciones/s")
        
        if 'concurrent' in self.results:
            print(f"  • Operaciones concurrentes: {self.results['concurrent']['detection_ops_per_second']:.0f} detecciones/s")
        
        if self.results.get('memory'):
            print(f"  • Uso de memoria: +{self.results['memory']['max_increase_mb']:.1f} MB máximo")
        
        if issues:
            print("\n⚠️ ISSUES DETECTADOS:")
            for issue in issues:
                print(f"  • {issue}")
        
        print("\n💡 RECOMENDACIONES:")
        for rec in recommendations:
            print(f"  • {rec}")
        
        # Puntuación general
        score = 100
        score -= len(issues) * 15  # -15 puntos por issue
        score = max(0, score)
        
        print(f"\n🏆 PUNTUACIÓN GENERAL: {score}/100")
        
        if score >= 90:
            print("   🟢 Excelente rendimiento")
        elif score >= 70:
            print("   🟡 Buen rendimiento, algunas mejoras posibles")
        else:
            print("   🔴 Rendimiento necesita optimización")
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas de rendimiento"""
        try:
            print("🚀 Iniciando pruebas de rendimiento del sistema simplificado...")
            print("="*60)
            
            self.test_gesture_detection_scalability()
            self.test_display_text_performance()
            self.test_database_performance()
            self.test_memory_usage()
            self.test_concurrent_operations()
            
            self.generate_report()
            
        finally:
            self.cleanup()


if __name__ == '__main__':
    suite = PerformanceTestSuite()
    suite.run_all_tests()