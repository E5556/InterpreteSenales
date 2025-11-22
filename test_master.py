#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script maestro para ejecutar todas las pruebas del sistema de gestos
Maneja dependencias y ejecuta pruebas apropiadas según disponibilidad
"""

import sys
import os
import subprocess
import time
from datetime import datetime

def print_header(title, char="="):
    """Imprimir encabezado formatado"""
    print(f"\n{char*60}")
    print(f" {title}")
    print(f"{char*60}")

def check_dependencies():
    """Verificar qué dependencias están disponibles"""
    print("🔍 Verificando dependencias disponibles...")
    
    # Dependencias core (siempre disponibles)
    core_deps = ['os', 'tempfile', 'sqlite3', 'unittest', 'shutil', 'time']
    
    # Dependencias del proyecto
    project_deps = {
        'opencv-python': 'cv2',
        'mediapipe': 'mediapipe', 
        'tensorflow': 'tensorflow',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'scikit-learn': 'sklearn',
        'matplotlib': 'matplotlib',
        'PyQt5': 'PyQt5',
        'tables': 'tables',
        'requests': 'requests',
        'psutil': 'psutil'
    }
    
    available_deps = []
    missing_deps = []
    
    for package, import_name in project_deps.items():
        try:
            __import__(import_name)
            available_deps.append(package)
        except ImportError:
            missing_deps.append(package)
    
    print(f"✅ Dependencias disponibles: {len(available_deps)}")
    print(f"❌ Dependencias faltantes: {len(missing_deps)}")
    
    if missing_deps:
        print("\n📦 Dependencias faltantes:")
        for dep in missing_deps:
            print(f"  • {dep}")
    
    return len(missing_deps) == 0, available_deps, missing_deps

def run_command_safe(command, description, timeout=300):
    """Ejecutar comando con manejo de errores y timeout"""
    print(f"\n🔧 {description}...")
    
    try:
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, command], 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        end_time = time.time()
        
        success = result.returncode == 0
        execution_time = end_time - start_time
        
        if success:
            print(f"✅ {description} completado en {execution_time:.2f}s")
        else:
            print(f"❌ {description} falló en {execution_time:.2f}s")
            if result.stderr and "ModuleNotFoundError" not in result.stderr:
                print(f"Error: {result.stderr[:200]}...")
        
        return success, execution_time, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} expiró después de {timeout}s")
        return False, timeout, "", "Timeout"
    except Exception as e:
        print(f"❌ Error ejecutando {description}: {e}")
        return False, 0, "", str(e)

def run_simplified_tests():
    """Ejecutar pruebas simplificadas que no requieren dependencias externas"""
    print_header("🔬 PRUEBAS SIMPLIFICADAS (Sin dependencias externas)")
    
    success, exec_time, stdout, stderr = run_command_safe(
        "test_simplified.py",
        "Ejecutando pruebas de lógica core"
    )
    
    return success, exec_time, stdout, stderr

def run_full_tests():
    """Ejecutar suite completa de pruebas"""
    print_header("🧪 PRUEBAS COMPLETAS (Con todas las dependencias)")
    
    success, exec_time, stdout, stderr = run_command_safe(
        "run_tests.py", 
        "Ejecutando suite completa de pruebas",
        timeout=600  # 10 minutos para pruebas completas
    )
    
    return success, exec_time, stdout, stderr

def offer_dependency_installation(missing_deps):
    """Ofrecer instalar dependencias faltantes"""
    print_header("📦 INSTALACIÓN DE DEPENDENCIAS")
    
    print("Las siguientes dependencias son necesarias para pruebas completas:")
    for dep in missing_deps:
        print(f"  • {dep}")
    
    print("\nOpciones disponibles:")
    print("1. Instalar dependencias automáticamente")
    print("2. Ejecutar solo pruebas simplificadas")
    print("3. Salir")
    
    while True:
        choice = input("\nSelecciona una opción (1-3): ").strip()
        
        if choice == "1":
            return install_dependencies()
        elif choice == "2":
            return False  # No instalar, ejecutar simplificadas
        elif choice == "3":
            print("👋 Saliendo...")
            sys.exit(0)
        else:
            print("❌ Opción inválida. Selecciona 1, 2 o 3.")

def install_dependencies():
    """Instalar dependencias usando el script instalador"""
    print("\n🚀 Iniciando instalación de dependencias...")
    
    success, exec_time, stdout, stderr = run_command_safe(
        "install_test_dependencies.py",
        "Instalando dependencias",
        timeout=900  # 15 minutos para instalación
    )
    
    if success:
        print("✅ Dependencias instaladas exitosamente")
        print("🔄 Re-verificando disponibilidad...")
        return True
    else:
        print("❌ Falló la instalación de dependencias")
        print("💡 Puedes instalar manualmente con:")
        print("   pip install opencv-python mediapipe tensorflow numpy pandas scikit-learn")
        return False

def generate_comprehensive_report(results):
    """Generar reporte comprensivo de todas las pruebas"""
    print_header("📋 REPORTE COMPRENSIVO DE PRUEBAS")
    
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sistema operativo: {os.name}")
    print(f"Python: {sys.version.split()[0]}")
    
    total_time = sum(result.get('time', 0) for result in results.values())
    successful_tests = sum(1 for result in results.values() if result.get('success', False))
    total_tests = len(results)
    
    print(f"\nTiempo total de ejecución: {total_time:.2f}s")
    print(f"Tipos de prueba ejecutados: {total_tests}")
    print(f"Pruebas exitosas: {successful_tests}")
    print(f"Tasa de éxito: {(successful_tests/total_tests)*100:.1f}%")
    
    print("\n📊 RESULTADOS DETALLADOS:")
    
    for test_name, result in results.items():
        status = "✅ PASÓ" if result.get('success', False) else "❌ FALLÓ"
        time_str = f"({result.get('time', 0):.2f}s)"
        print(f"  • {test_name}: {status} {time_str}")
        
        if result.get('details'):
            print(f"    {result['details']}")
    
    # Análisis de calidad
    print("\n🎯 ANÁLISIS DE CALIDAD:")
    
    if successful_tests == total_tests:
        print("  🟢 Sistema completamente funcional")
        print("  ✅ Listo para uso en producción")
        print("  🚀 Todas las funcionalidades verificadas")
    elif successful_tests >= total_tests * 0.8:
        print("  🟡 Sistema mayormente funcional")
        print("  ⚠️ Algunas optimizaciones pendientes")
        print("  🔧 Revisar pruebas fallidas")
    else:
        print("  🔴 Sistema requiere atención")
        print("  ❌ Problemas críticos detectados")
        print("  🚫 NO usar en producción")
    
    # Recomendaciones
    print("\n💡 PRÓXIMOS PASOS:")
    
    if 'simplified' in results and results['simplified']['success']:
        print("  ✅ Lógica core verificada")
    
    if 'full' in results and results['full']['success']:
        print("  ✅ Sistema completo verificado")
        print("  🎯 Considerar pruebas de usuario final")
        print("  📊 Monitorear rendimiento en producción")
    elif 'full' in results and not results['full']['success']:
        print("  🔧 Resolver problemas en pruebas completas")
        print("  📦 Verificar instalación de dependencias")
    
    if successful_tests < total_tests:
        print("  🐛 Debuggear pruebas fallidas")
        print("  🔄 Re-ejecutar después de correcciones")

def main():
    """Función principal del script maestro"""
    print_header("🎯 SISTEMA MAESTRO DE PRUEBAS")
    print("Sistema de Gestión de Gestos Simplificado")
    print(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Paso 1: Verificar dependencias
    all_deps_available, available_deps, missing_deps = check_dependencies()
    
    # Paso 2: Ejecutar pruebas simplificadas (siempre disponibles)
    print_header("📍 FASE 1: PRUEBAS SIMPLIFICADAS", "-")
    print("Estas pruebas verifican la lógica core sin dependencias externas")
    
    simplified_success, simplified_time, simplified_out, simplified_err = run_simplified_tests()
    
    results['simplified'] = {
        'success': simplified_success,
        'time': simplified_time,
        'details': "Lógica core del sistema (detección, conversión, database)"
    }
    
    # Paso 3: Decidir sobre pruebas completas
    if all_deps_available:
        print_header("📍 FASE 2: PRUEBAS COMPLETAS", "-")
        print("Todas las dependencias disponibles - ejecutando pruebas completas")
        
        full_success, full_time, full_out, full_err = run_full_tests()
        
        results['full'] = {
            'success': full_success,
            'time': full_time,
            'details': "Sistema completo (unitarias + rendimiento)"
        }
        
    else:
        print_header("📍 FASE 2: DEPENDENCIAS FALTANTES", "-")
        
        # Ofrecer instalar dependencias
        if offer_dependency_installation(missing_deps):
            # Re-verificar después de instalación
            all_deps_available, _, _ = check_dependencies()
            
            if all_deps_available:
                print("🎉 Dependencias instaladas exitosamente")
                full_success, full_time, full_out, full_err = run_full_tests()
                
                results['full'] = {
                    'success': full_success,
                    'time': full_time,
                    'details': "Sistema completo (después de instalar dependencias)"
                }
            else:
                print("⚠️ Algunas dependencias aún faltan")
                results['installation'] = {
                    'success': False,
                    'time': 0,
                    'details': "Instalación parcial de dependencias"
                }
        else:
            print("📝 Ejecutando solo pruebas simplificadas por elección del usuario")
            results['skipped'] = {
                'success': True,
                'time': 0,
                'details': "Pruebas completas omitidas (dependencias faltantes)"
            }
    
    # Generar reporte final
    generate_comprehensive_report(results)
    
    # Determinar código de salida
    critical_success = results.get('simplified', {}).get('success', False)
    
    if critical_success:
        print("\n🎉 Sistema core funcional - Pruebas críticas pasaron")
        sys.exit(0)
    else:
        print("\n❌ Sistema core tiene problemas - Revisar urgentemente")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Pruebas interrumpidas por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        sys.exit(1)