#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script principal para ejecutar todas las pruebas del sistema de gestos
Ejecuta pruebas unitarias y de rendimiento
"""

import sys
import os
import subprocess
import time
from datetime import datetime

def print_header(title):
    """Imprimir encabezado formatado"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def run_command(command, description):
    """Ejecutar comando y capturar resultado"""
    print(f"\n🔧 {description}...")
    
    try:
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, command], 
            capture_output=True, 
            text=True, 
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        end_time = time.time()
        
        success = result.returncode == 0
        execution_time = end_time - start_time
        
        if success:
            print(f"✅ {description} completado en {execution_time:.2f}s")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ {description} falló en {execution_time:.2f}s")
            if result.stderr:
                print("STDERR:", result.stderr)
            if result.stdout:
                print("STDOUT:", result.stdout)
        
        return success, execution_time, result.stdout, result.stderr
        
    except Exception as e:
        print(f"❌ Error ejecutando {description}: {e}")
        return False, 0, "", str(e)

def check_dependencies():
    """Verificar dependencias necesarias"""
    print("🔍 Verificando dependencias...")
    
    required_modules = [
        'unittest',
        'tempfile', 
        'sqlite3',
        'numpy',
        'os',
        'shutil',
        'time',
        'statistics'
    ]
    
    optional_modules = [
        'psutil'  # Para pruebas de memoria
    ]
    
    missing_required = []
    missing_optional = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_required.append(module)
    
    for module in optional_modules:
        try:
            __import__(module)
        except ImportError:
            missing_optional.append(module)
    
    if missing_required:
        print(f"❌ Módulos requeridos faltantes: {', '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"⚠️ Módulos opcionales faltantes: {', '.join(missing_optional)}")
        print("   Algunas pruebas de rendimiento podrían saltarse")
    
    print("✅ Dependencias verificadas")
    return True

def check_project_files():
    """Verificar que los archivos del proyecto existan"""
    print("\n📁 Verificando archivos del proyecto...")
    
    required_files = [
        'constants.py',
        'training_utils.py',
        'database.py',
        'helpers.py',
        'main.py'
    ]
    
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Archivos faltantes: {', '.join(missing_files)}")
        return False
    
    print("✅ Archivos del proyecto verificados")
    return True

def generate_test_report(unit_success, unit_time, unit_output, perf_success, perf_time, perf_output):
    """Generar reporte final de pruebas"""
    print_header("📋 REPORTE FINAL DE PRUEBAS")
    
    # Estadísticas generales
    total_time = unit_time + perf_time
    total_tests = 2
    passed_tests = int(unit_success) + int(perf_success)
    
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tiempo total de ejecución: {total_time:.2f}s")
    print(f"Pruebas ejecutadas: {total_tests}")
    print(f"Pruebas exitosas: {passed_tests}")
    print(f"Tasa de éxito: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\n📊 RESULTADOS DETALLADOS:")
    
    # Pruebas unitarias
    status_unit = "✅ PASÓ" if unit_success else "❌ FALLÓ"
    print(f"  • Pruebas Unitarias: {status_unit} ({unit_time:.2f}s)")
    
    # Pruebas de rendimiento
    status_perf = "✅ PASÓ" if perf_success else "❌ FALLÓ"
    print(f"  • Pruebas de Rendimiento: {status_perf} ({perf_time:.2f}s)")
    
    # Extraer métricas de rendimiento si están disponibles
    if perf_success and perf_output:
        if "PUNTUACIÓN GENERAL:" in perf_output:
            score_line = [line for line in perf_output.split('\n') if "PUNTUACIÓN GENERAL:" in line]
            if score_line:
                print(f"  • Puntuación de Rendimiento: {score_line[0].split(':')[1].strip()}")
    
    # Recomendaciones finales
    print("\n💡 RECOMENDACIONES:")
    
    if unit_success and perf_success:
        print("  ✅ Sistema listo para producción")
        print("  ✅ Todas las funcionalidades probadas exitosamente")
        print("  ✅ Rendimiento dentro de parámetros aceptables")
    elif unit_success and not perf_success:
        print("  ⚠️ Funcionalidad correcta pero problemas de rendimiento")
        print("  🔧 Revisar optimizaciones antes de usar en producción")
    elif not unit_success and perf_success:
        print("  ❌ Errores funcionales críticos detectados")
        print("  🚫 NO usar en producción hasta corregir errores")
    else:
        print("  ❌ Sistema tiene problemas funcionales y de rendimiento")
        print("  🚫 Requiere revisión completa antes de cualquier uso")
    
    # Próximos pasos
    print("\n🚀 PRÓXIMOS PASOS:")
    if passed_tests == total_tests:
        print("  1. Sistema listo para pruebas de integración")
        print("  2. Considerar pruebas con usuarios reales")
        print("  3. Monitorear rendimiento en producción")
    else:
        print("  1. Revisar y corregir errores detectados")
        print("  2. Re-ejecutar pruebas hasta que pasen")
        print("  3. Considerar refactoring si los problemas persisten")

def main():
    """Función principal"""
    print_header("🧪 SISTEMA DE PRUEBAS AUTOMATIZADAS")
    print("Sistema de Gestión de Gestos Simplificado")
    print(f"Ejecutado en: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificaciones previas
    if not check_dependencies():
        print("\n❌ Dependencias faltantes. Instalar antes de continuar.")
        sys.exit(1)
    
    if not check_project_files():
        print("\n❌ Archivos del proyecto faltantes. Verificar estructura.")
        sys.exit(1)
    
    print("\n🎯 Iniciando secuencia de pruebas...")
    
    # Ejecutar pruebas unitarias
    print_header("🔬 PRUEBAS UNITARIAS")
    unit_success, unit_time, unit_output, unit_error = run_command(
        "test_gesture_system.py", 
        "Ejecutando pruebas unitarias"
    )
    
    # Ejecutar pruebas de rendimiento
    print_header("⚡ PRUEBAS DE RENDIMIENTO")
    perf_success, perf_time, perf_output, perf_error = run_command(
        "test_performance.py",
        "Ejecutando pruebas de rendimiento"
    )
    
    # Generar reporte final
    generate_test_report(unit_success, unit_time, unit_output, perf_success, perf_time, perf_output)
    
    # Código de salida
    if unit_success and perf_success:
        print("\n🎉 ¡Todas las pruebas completadas exitosamente!")
        sys.exit(0)
    else:
        print("\n⚠️ Algunas pruebas fallaron. Revisar detalles arriba.")
        sys.exit(1)

if __name__ == '__main__':
    main()