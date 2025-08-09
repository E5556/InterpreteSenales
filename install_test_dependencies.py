#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para instalar dependencias necesarias para las pruebas completas
"""

import subprocess
import sys
import os

def install_package(package_name):
    """Instalar un paquete usando pip"""
    try:
        print(f"📦 Instalando {package_name}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {package_name} instalado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando {package_name}: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr}")
        return False

def check_package(package_name, import_name=None):
    """Verificar si un paquete está instalado"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def main():
    """Instalar todas las dependencias necesarias"""
    print("🚀 Instalador de dependencias para pruebas completas")
    print("="*60)
    
    # Lista de dependencias necesarias
    dependencies = [
        ("opencv-python", "cv2"),
        ("mediapipe", "mediapipe"),
        ("tensorflow", "tensorflow"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("scikit-learn", "sklearn"),
        ("matplotlib", "matplotlib"),
        ("PyQt5", "PyQt5"),
        ("tables", "tables"),
        ("requests", "requests"),
        ("psutil", "psutil")  # Opcional para pruebas de memoria
    ]
    
    print("🔍 Verificando dependencias actuales...")
    
    missing_packages = []
    installed_packages = []
    
    for package_name, import_name in dependencies:
        if check_package(package_name, import_name):
            installed_packages.append(package_name)
            print(f"✅ {package_name} ya instalado")
        else:
            missing_packages.append(package_name)
            print(f"❌ {package_name} faltante")
    
    if not missing_packages:
        print("\n🎉 ¡Todas las dependencias ya están instaladas!")
        print("💡 Puedes ejecutar las pruebas completas con: python run_tests.py")
        return True
    
    print(f"\n📋 Faltan {len(missing_packages)} dependencias:")
    for package in missing_packages:
        print(f"  • {package}")
    
    # Preguntar al usuario si quiere instalar
    response = input("\n¿Instalar dependencias faltantes? (y/N): ").strip().lower()
    if response not in ['y', 'yes', 'sí', 's']:
        print("❌ Instalación cancelada por el usuario")
        return False
    
    print("\n🔧 Instalando dependencias faltantes...")
    
    failed_installations = []
    successful_installations = []
    
    for package_name in missing_packages:
        if install_package(package_name):
            successful_installations.append(package_name)
        else:
            failed_installations.append(package_name)
    
    # Reporte final
    print("\n" + "="*60)
    print("📊 REPORTE DE INSTALACIÓN")
    print("="*60)
    
    print(f"Dependencias previamente instaladas: {len(installed_packages)}")
    print(f"Instalaciones exitosas: {len(successful_installations)}")
    print(f"Instalaciones fallidas: {len(failed_installations)}")
    
    if successful_installations:
        print("\n✅ Instaladas exitosamente:")
        for package in successful_installations:
            print(f"  • {package}")
    
    if failed_installations:
        print("\n❌ Instalaciones fallidas:")
        for package in failed_installations:
            print(f"  • {package}")
        
        print("\n💡 Para instalar manualmente:")
        for package in failed_installations:
            print(f"   pip install {package}")
    
    if not failed_installations:
        print("\n🎉 ¡Todas las dependencias instaladas exitosamente!")
        print("🧪 Ahora puedes ejecutar:")
        print("   python run_tests.py          # Pruebas completas")
        print("   python test_gesture_system.py # Solo pruebas unitarias")
        print("   python test_performance.py    # Solo pruebas de rendimiento")
        print("   python test_simplified.py     # Pruebas sin dependencias")
        return True
    else:
        print(f"\n⚠️ {len(failed_installations)} dependencias fallaron en instalarse")
        print("🔧 Revisar errores arriba e instalar manualmente")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)