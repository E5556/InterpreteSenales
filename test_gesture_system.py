#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el sistema de gestión de gestos simplificado
Prueba todo el flujo desde detección hasta procesamiento de keypoints
"""

import unittest
import os
import tempfile
import shutil
import sqlite3
import json
import numpy as np
from unittest.mock import patch, MagicMock, mock_open
import sys

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Función para importar módulos con manejo de errores
def safe_import():
    """Importar módulos con manejo de dependencias faltantes"""
    try:
        from constants import get_display_text, DATABASE_NAME
        from training_utils import get_gestures_with_samples, create_keypoints_for_all_gestures
        from database import (init_db, add_user, check_user, create_session, 
                             add_interpretation, get_user_sessions, get_session_interpretations)
        return True, (get_display_text, DATABASE_NAME, get_gestures_with_samples, 
                     create_keypoints_for_all_gestures, init_db, add_user, check_user, 
                     create_session, add_interpretation, get_user_sessions, get_session_interpretations)
    except ImportError as e:
        print(f"⚠️ Error de importación: {e}")
        print("💡 Instalar dependencias faltantes:")
        print("   pip install opencv-python mediapipe tensorflow numpy pandas scikit-learn")
        return False, None

# Realizar importación segura
IMPORTS_OK, modules = safe_import()
if IMPORTS_OK:
    get_display_text, DATABASE_NAME, get_gestures_with_samples, create_keypoints_for_all_gestures, init_db, add_user, check_user, create_session, add_interpretation, get_user_sessions, get_session_interpretations = modules


class TestGestureDetection(unittest.TestCase):
    """Pruebas para la detección automática de gestos"""
    
    def setUp(self):
        """Configurar entorno de prueba"""
        if not IMPORTS_OK:
            self.skipTest("Dependencias faltantes - instalar opencv-python, mediapipe, tensorflow")
        
        # Crear estructura temporal de directorios para pruebas
        self.test_dir = tempfile.mkdtemp()
        self.frame_actions_path = os.path.join(self.test_dir, "frame_actions")
        os.makedirs(self.frame_actions_path)
        
        # Mock del FRAME_ACTIONS_PATH en constants
        self.patcher = patch('training_utils.FRAME_ACTIONS_PATH', self.frame_actions_path)
        self.patcher.start()
    
    def tearDown(self):
        """Limpiar directorios temporales"""
        self.patcher.stop()
        shutil.rmtree(self.test_dir)
    
    def _create_gesture_with_samples(self, gesture_name, num_samples=2, frames_per_sample=5):
        """Crear gesto con muestras de prueba"""
        gesture_path = os.path.join(self.frame_actions_path, gesture_name)
        os.makedirs(gesture_path)
        
        for i in range(num_samples):
            sample_path = os.path.join(gesture_path, f"sample_{i}")
            os.makedirs(sample_path)
            
            for j in range(frames_per_sample):
                # Crear archivos de imagen falsos
                frame_file = os.path.join(sample_path, f"frame_{j:02d}.jpg")
                with open(frame_file, 'w') as f:
                    f.write("fake_image_data")
    
    def _create_empty_gesture(self, gesture_name):
        """Crear gesto sin muestras"""
        gesture_path = os.path.join(self.frame_actions_path, gesture_name)
        os.makedirs(gesture_path)
    
    def test_get_gestures_with_samples_empty_directory(self):
        """Probar detección cuando no hay gestos"""
        result = get_gestures_with_samples()
        self.assertEqual(result, [])
    
    def test_get_gestures_with_samples_with_valid_gestures(self):
        """Probar detección de gestos válidos con muestras"""
        # Crear gestos con muestras
        self._create_gesture_with_samples("hola")
        self._create_gesture_with_samples("adios")
        self._create_gesture_with_samples("por_favor")
        
        result = get_gestures_with_samples()
        expected = ["adios", "hola", "por_favor"]  # Ordenados alfabéticamente
        self.assertEqual(result, expected)
    
    def test_get_gestures_with_samples_ignore_empty_gestures(self):
        """Probar que ignora gestos sin muestras"""
        # Crear gesto con muestras
        self._create_gesture_with_samples("hola")
        
        # Crear gesto vacío
        self._create_empty_gesture("adios")
        
        result = get_gestures_with_samples()
        self.assertEqual(result, ["hola"])
    
    def test_get_gestures_with_samples_ignore_non_directories(self):
        """Probar que ignora archivos que no son directorios"""
        # Crear gesto válido
        self._create_gesture_with_samples("hola")
        
        # Crear archivo que no es directorio
        file_path = os.path.join(self.frame_actions_path, "not_a_directory.txt")
        with open(file_path, 'w') as f:
            f.write("test")
        
        result = get_gestures_with_samples()
        self.assertEqual(result, ["hola"])
    
    def test_get_gestures_with_samples_nonexistent_directory(self):
        """Probar comportamiento cuando frame_actions no existe"""
        # Eliminar directorio
        shutil.rmtree(self.frame_actions_path)
        
        result = get_gestures_with_samples()
        self.assertEqual(result, [])


class TestDisplayText(unittest.TestCase):
    """Pruebas para la conversión automática de texto de display"""
    
    def test_get_display_text_simple(self):
        """Probar conversión simple"""
        result = get_display_text("hola")
        self.assertEqual(result, "HOLA")
    
    def test_get_display_text_with_underscores(self):
        """Probar conversión con guiones bajos"""
        result = get_display_text("buenos_dias")
        self.assertEqual(result, "BUENOS DIAS")
    
    def test_get_display_text_multiple_underscores(self):
        """Probar conversión con múltiples guiones bajos"""
        result = get_display_text("con_mucho_gusto")
        self.assertEqual(result, "CON MUCHO GUSTO")
    
    def test_get_display_text_mixed_case(self):
        """Probar conversión con mayúsculas y minúsculas mezcladas"""
        result = get_display_text("Por_Favor")
        self.assertEqual(result, "POR FAVOR")
    
    def test_get_display_text_empty_string(self):
        """Probar conversión de string vacío"""
        result = get_display_text("")
        self.assertEqual(result, "")


class TestDatabase(unittest.TestCase):
    """Pruebas para funciones de base de datos"""
    
    def setUp(self):
        """Crear base de datos temporal para pruebas"""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Mock del DATABASE_NAME
        self.patcher = patch('database.DATABASE_NAME', self.test_db_path)
        self.patcher.start()
        
        # Inicializar base de datos
        init_db()
    
    def tearDown(self):
        """Limpiar base de datos temporal"""
        self.patcher.stop()
        os.unlink(self.test_db_path)
    
    def test_add_and_check_user(self):
        """Probar agregar y verificar usuario"""
        # Agregar usuario
        user_id = add_user(
            username="test_user",
            password="test_password",
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
        self.assertIsNotNone(user_id)
        
        # Verificar usuario con credenciales correctas
        result = check_user("test_user", "test_password")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], user_id)  # user_id
        self.assertEqual(result[1], "user")   # role
        self.assertEqual(result[2], 0)        # must_change_password
    
    def test_check_user_invalid_credentials(self):
        """Probar verificación con credenciales inválidas"""
        # Agregar usuario
        add_user(username="test_user", password="correct_password")
        
        # Intentar con contraseña incorrecta
        result = check_user("test_user", "wrong_password")
        self.assertIsNone(result)
        
        # Intentar con usuario inexistente
        result = check_user("nonexistent_user", "any_password")
        self.assertIsNone(result)
    
    def test_create_session_and_add_interpretation(self):
        """Probar creación de sesión y agregado de interpretaciones"""
        # Agregar usuario
        user_id = add_user(username="test_user", password="test_password")
        
        # Crear sesión
        session_id = create_session(user_id)
        self.assertIsNotNone(session_id)
        
        # Agregar interpretaciones
        add_interpretation(session_id, "HOLA")
        add_interpretation(session_id, "ADIOS")
        
        # Verificar interpretaciones
        interpretations = get_session_interpretations(session_id)
        self.assertEqual(len(interpretations), 2)
        self.assertEqual(interpretations[0][0], "HOLA")
        self.assertEqual(interpretations[1][0], "ADIOS")
    
    def test_get_user_sessions(self):
        """Probar obtención de sesiones de usuario"""
        # Agregar usuario
        user_id = add_user(username="test_user", password="test_password")
        
        # Crear múltiples sesiones
        session1 = create_session(user_id)
        session2 = create_session(user_id)
        
        # Obtener sesiones
        sessions = get_user_sessions(user_id)
        self.assertEqual(len(sessions), 2)
        
        # Verificar que los IDs de sesión están presentes
        session_ids = [session[0] for session in sessions]
        self.assertIn(session1, session_ids)
        self.assertIn(session2, session_ids)


class TestKeypointProcessing(unittest.TestCase):
    """Pruebas para el procesamiento de keypoints"""
    
    def setUp(self):
        """Configurar entorno de prueba"""
        self.test_dir = tempfile.mkdtemp()
        self.frame_actions_path = os.path.join(self.test_dir, "frame_actions")
        self.keypoints_path = os.path.join(self.test_dir, "keypoints")
        os.makedirs(self.frame_actions_path)
        os.makedirs(self.keypoints_path)
        
        # Mock de paths
        self.frame_patcher = patch('training_utils.FRAME_ACTIONS_PATH', self.frame_actions_path)
        self.keypoints_patcher = patch('training_utils.KEYPOINTS_PATH', self.keypoints_path)
        self.frame_patcher.start()
        self.keypoints_patcher.start()
    
    def tearDown(self):
        """Limpiar directorios temporales"""
        self.frame_patcher.stop()
        self.keypoints_patcher.stop()
        shutil.rmtree(self.test_dir)
    
    def _create_gesture_with_samples(self, gesture_name, num_samples=2):
        """Crear gesto con muestras de prueba"""
        gesture_path = os.path.join(self.frame_actions_path, gesture_name)
        os.makedirs(gesture_path)
        
        for i in range(num_samples):
            sample_path = os.path.join(gesture_path, f"sample_{i}")
            os.makedirs(sample_path)
            
            # Crear archivos de imagen falsos
            for j in range(3):
                frame_file = os.path.join(sample_path, f"frame_{j:02d}.jpg")
                with open(frame_file, 'w') as f:
                    f.write("fake_image_data")
    
    @patch('training_utils.create_keypoints_for_gestures')
    def test_create_keypoints_for_all_gestures_with_gestures(self, mock_create_keypoints):
        """Probar procesamiento cuando hay gestos disponibles"""
        # Configurar mock
        mock_create_keypoints.return_value = True
        
        # Crear gestos de prueba
        self._create_gesture_with_samples("hola")
        self._create_gesture_with_samples("adios")
        
        # Función de callback de prueba
        progress_calls = []
        def test_callback(value, message):
            progress_calls.append((value, message))
        
        # Ejecutar función
        result = create_keypoints_for_all_gestures(progress_callback=test_callback)
        
        # Verificar resultado
        self.assertTrue(result)
        
        # Verificar que se llamó create_keypoints_for_gestures con los gestos correctos
        mock_create_keypoints.assert_called_once()
        args, kwargs = mock_create_keypoints.call_args
        self.assertEqual(args[0], ["adios", "hola"])  # Ordenados alfabéticamente
        
        # Verificar callbacks de progreso
        self.assertTrue(len(progress_calls) >= 1)
        self.assertTrue(any("Detectados 2 gestos" in call[1] for call in progress_calls))
    
    def test_create_keypoints_for_all_gestures_no_gestures(self):
        """Probar procesamiento cuando no hay gestos"""
        progress_calls = []
        def test_callback(value, message):
            progress_calls.append((value, message))
        
        # Ejecutar función sin gestos
        result = create_keypoints_for_all_gestures(progress_callback=test_callback)
        
        # Verificar resultado
        self.assertFalse(result)
        
        # Verificar mensaje de progreso
        self.assertEqual(len(progress_calls), 1)
        self.assertEqual(progress_calls[0][1], "No se encontraron gestos con muestras")


class TestIntegration(unittest.TestCase):
    """Pruebas de integración del flujo completo"""
    
    def setUp(self):
        """Configurar entorno completo de prueba"""
        self.test_dir = tempfile.mkdtemp()
        self.frame_actions_path = os.path.join(self.test_dir, "frame_actions")
        self.keypoints_path = os.path.join(self.test_dir, "keypoints")
        os.makedirs(self.frame_actions_path)
        os.makedirs(self.keypoints_path)
        
        # Base de datos temporal
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()
        self.test_db_path = self.test_db.name
        
        # Patches
        self.frame_patcher = patch('training_utils.FRAME_ACTIONS_PATH', self.frame_actions_path)
        self.keypoints_patcher = patch('training_utils.KEYPOINTS_PATH', self.keypoints_path)
        self.db_patcher = patch('database.DATABASE_NAME', self.test_db_path)
        
        self.frame_patcher.start()
        self.keypoints_patcher.start()
        self.db_patcher.start()
        
        # Inicializar base de datos
        init_db()
    
    def tearDown(self):
        """Limpiar entorno de prueba"""
        self.frame_patcher.stop()
        self.keypoints_patcher.stop()
        self.db_patcher.stop()
        shutil.rmtree(self.test_dir)
        os.unlink(self.test_db_path)
    
    def _create_complete_gesture(self, gesture_name):
        """Crear gesto completo con muestras"""
        gesture_path = os.path.join(self.frame_actions_path, gesture_name)
        os.makedirs(gesture_path)
        
        # Crear múltiples muestras
        for i in range(3):
            sample_path = os.path.join(gesture_path, f"sample_{i}")
            os.makedirs(sample_path)
            
            # Crear frames
            for j in range(15):  # MODEL_FRAMES = 15
                frame_file = os.path.join(sample_path, f"frame_{j:02d}.jpg")
                with open(frame_file, 'w') as f:
                    f.write(f"fake_frame_data_{j}")
    
    def test_complete_workflow(self):
        """Probar flujo completo: creación → detección → display → database"""
        # 1. Crear gestos
        self._create_complete_gesture("hola")
        self._create_complete_gesture("por_favor")
        
        # 2. Detectar gestos
        detected_gestures = get_gestures_with_samples()
        expected_gestures = ["hola", "por_favor"]
        self.assertEqual(detected_gestures, expected_gestures)
        
        # 3. Probar conversión de display text
        for gesture in detected_gestures:
            display_text = get_display_text(gesture)
            self.assertIsInstance(display_text, str)
            self.assertTrue(len(display_text) > 0)
        
        # 4. Probar integración con base de datos
        user_id = add_user(username="test_user", password="test_password")
        session_id = create_session(user_id)
        
        # Simular interpretaciones
        for gesture in detected_gestures:
            display_text = get_display_text(gesture)
            add_interpretation(session_id, display_text)
        
        # Verificar interpretaciones almacenadas
        interpretations = get_session_interpretations(session_id)
        self.assertEqual(len(interpretations), 2)
        
        stored_words = [interp[0] for interp in interpretations]
        self.assertIn("HOLA", stored_words)
        self.assertIn("POR FAVOR", stored_words)
    
    def test_edge_cases_workflow(self):
        """Probar casos extremos del flujo"""
        # Caso 1: No hay gestos
        gestures = get_gestures_with_samples()
        self.assertEqual(gestures, [])
        
        # Caso 2: Gesto con nombre complejo
        self._create_complete_gesture("muy_complejo_gesto_test")
        gestures = get_gestures_with_samples()
        self.assertEqual(gestures, ["muy_complejo_gesto_test"])
        
        display_text = get_display_text("muy_complejo_gesto_test")
        self.assertEqual(display_text, "MUY COMPLEJO GESTO TEST")
        
        # Caso 3: Base de datos con múltiples usuarios y sesiones
        user1 = add_user(username="user1", password="pass1")
        user2 = add_user(username="user2", password="pass2")
        
        session1 = create_session(user1)
        session2 = create_session(user2)
        
        add_interpretation(session1, "HOLA")
        add_interpretation(session2, "ADIOS")
        
        # Verificar aislamiento de datos
        interp1 = get_session_interpretations(session1)
        interp2 = get_session_interpretations(session2)
        
        self.assertEqual(len(interp1), 1)
        self.assertEqual(len(interp2), 1)
        self.assertEqual(interp1[0][0], "HOLA")
        self.assertEqual(interp2[0][0], "ADIOS")


def run_all_tests():
    """Ejecutar todas las pruebas y mostrar resultados"""
    # Crear suite de pruebas
    test_suite = unittest.TestSuite()
    
    # Agregar todas las clases de prueba
    test_classes = [
        TestGestureDetection,
        TestDisplayText,
        TestDatabase,
        TestKeypointProcessing,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Ejecutar pruebas con reporte detallado
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
    result = runner.run(test_suite)
    
    # Mostrar resumen
    print("\n" + "="*60)
    print("RESUMEN DE PRUEBAS")
    print("="*60)
    print(f"Pruebas ejecutadas: {result.testsRun}")
    print(f"Exitosas: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Fallidas: {len(result.failures)}")
    print(f"Errores: {len(result.errors)}")
    
    if result.failures:
        print("\nFALLOS:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nERRORES:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\nTasa de éxito: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("🧪 Iniciando pruebas unitarias del sistema de gestos simplificado...")
    print("="*60)
    
    success = run_all_tests()
    
    if success:
        print("\n✅ Todas las pruebas pasaron exitosamente!")
        sys.exit(0)
    else:
        print("\n❌ Algunas pruebas fallaron. Revisar los errores arriba.")
        sys.exit(1)