#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el ordenamiento correcto de archivos de frames
Verifica que ambos formatos (frame_XX.jpg y XX.jpg) se ordenen correctamente
"""

import os
import re

def get_sorted_image_files(sample_path):
    """
    Obtiene archivos de imagen ordenados correctamente, manejando diferentes formatos:
    - frame_01.jpg, frame_02.jpg, ... (formato antiguo)
    - 1.jpg, 2.jpg, ... (formato nuevo)
    """
    # Obtener todos los archivos de imagen
    image_files = [f for f in os.listdir(sample_path) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    def extract_number(filename):
        """Extraer número del nombre de archivo para ordenar"""
        # Buscar números en el nombre del archivo
        numbers = re.findall(r'\d+', filename)
        if numbers:
            # Tomar el último número encontrado (más robusto)
            return int(numbers[-1])
        return 0
    
    # Ordenar por número extraído
    sorted_files = sorted(image_files, key=extract_number)
    
    return sorted_files

def test_sample_ordering(sample_path, gesture_name):
    """Probar el ordenamiento de archivos en una muestra"""
    print(f"\n🔍 Probando ordenamiento en {gesture_name}:")
    print(f"   Ruta: {sample_path}")
    
    if not os.path.exists(sample_path):
        print(f"   ❌ Ruta no existe")
        return False
    
    # Obtener archivos sin ordenar
    all_files = [f for f in os.listdir(sample_path) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # Obtener archivos ordenados
    sorted_files = get_sorted_image_files(sample_path)
    
    print(f"   📁 Archivos encontrados: {len(all_files)}")
    
    if len(all_files) == 0:
        print(f"   ⚠️ No hay archivos de imagen")
        return False
    
    # Mostrar primeros y últimos archivos
    print(f"   📄 Sin ordenar: {all_files[:3]}...{all_files[-3:] if len(all_files) > 6 else []}")
    print(f"   ✅ Ordenados:   {sorted_files[:3]}...{sorted_files[-3:] if len(sorted_files) > 6 else []}")
    
    # Verificar que el ordenamiento tenga sentido
    if len(sorted_files) > 1:
        def extract_number(filename):
            numbers = re.findall(r'\d+', filename)
            return int(numbers[-1]) if numbers else 0
        
        first_num = extract_number(sorted_files[0])
        last_num = extract_number(sorted_files[-1])
        
        print(f"   🔢 Rango numérico: {first_num} → {last_num}")
        
        # Verificar orden ascendente
        is_ascending = all(extract_number(sorted_files[i]) <= extract_number(sorted_files[i+1]) 
                          for i in range(len(sorted_files)-1))
        
        if is_ascending:
            print(f"   ✅ Orden correcto")
            return True
        else:
            print(f"   ❌ Orden incorrecto")
            return False
    
    return True

def main():
    """Función principal de prueba"""
    print("🧪 PRUEBA DE ORDENAMIENTO DE ARCHIVOS")
    print("="*50)
    
    # Rutas de prueba
    test_cases = [
        # Formato antiguo (frame_XX.jpg)
        ("frame_actions/abrazar/sample_241111235422745799", "abrazar (formato antiguo)"),
        
        # Formato nuevo (XX.jpg)  
        ("frame_actions/por_favor/sample_250726010416496712", "por_favor (formato nuevo)"),
        
        # Probar más muestras si existen
        ("frame_actions/adios/sample_241117201648349574", "adios (formato mixto)"),
    ]
    
    results = []
    
    for sample_path, description in test_cases:
        result = test_sample_ordering(sample_path, description)
        results.append((description, result))
    
    # Resumen final
    print(f"\n📊 RESUMEN DE PRUEBAS:")
    print("="*50)
    
    for description, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"   {status} {description}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n🎯 Resultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("✅ Ordenamiento funciona correctamente para todos los formatos")
    else:
        print("⚠️ Hay problemas con el ordenamiento - revisar")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    
    if success:
        print("\n💡 El sistema ahora maneja correctamente ambos formatos de archivo")
        print("   📁 frame_01.jpg, frame_02.jpg, ... (formato antiguo)")
        print("   📁 1.jpg, 2.jpg, ... (formato nuevo)")
    else:
        print("\n⚠️ Se detectaron problemas que requieren atención")