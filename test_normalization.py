#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la normalización de muestras
Verifica que las muestras se normalicen correctamente a 15 frames
"""

import os
import sys

def test_normalization_sample(sample_path, gesture_name):
    """Probar la normalización de una muestra específica"""
    print(f"\n🔍 Analizando muestra de {gesture_name}:")
    print(f"   Ruta: {sample_path}")
    
    if not os.path.exists(sample_path):
        print(f"   ❌ Ruta no existe")
        return False, 0, 0
    
    # Contar archivos antes
    image_files = [f for f in os.listdir(sample_path) 
                   if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    original_count = len(image_files)
    print(f"   📁 Frames originales: {original_count}")
    
    if original_count == 0:
        print(f"   ⚠️ No hay archivos de imagen")
        return False, 0, 0
    
    # Mostrar algunos nombres de archivos para verificar formato
    sample_files = image_files[:5]
    print(f"   📄 Ejemplos de archivos: {sample_files}")
    
    # Verificar formato de nombres
    has_frame_prefix = any(f.startswith('frame_') for f in image_files)
    has_numeric_only = any(f.replace('.jpg', '').replace('.jpeg', '').replace('.png', '').isdigit() for f in image_files)
    
    format_type = "unknown"
    if has_frame_prefix:
        format_type = "frame_XX.jpg (normalizado)"
    elif has_numeric_only:
        format_type = "XX.jpg (original)"
    
    print(f"   🏷️ Formato detectado: {format_type}")
    
    return True, original_count, format_type

def analyze_gesture_samples(gesture_name):
    """Analizar todas las muestras de un gesto"""
    gesture_path = os.path.join("frame_actions", gesture_name)
    
    if not os.path.exists(gesture_path):
        print(f"❌ Gesto '{gesture_name}' no existe")
        return
    
    print(f"\n📊 ANÁLISIS DE GESTO: {gesture_name.upper()}")
    print("="*50)
    
    # Obtener todas las muestras
    sample_dirs = [d for d in os.listdir(gesture_path) 
                   if os.path.isdir(os.path.join(gesture_path, d))]
    
    if not sample_dirs:
        print(f"   ⚠️ No hay muestras para el gesto '{gesture_name}'")
        return
    
    print(f"   📁 Total de muestras: {len(sample_dirs)}")
    
    # Analizar algunas muestras
    sample_count = min(3, len(sample_dirs))
    frame_counts = []
    formats = []
    
    for i, sample_dir in enumerate(sample_dirs[:sample_count]):
        sample_path = os.path.join(gesture_path, sample_dir)
        success, count, format_type = test_normalization_sample(sample_path, f"{gesture_name}-{i+1}")
        
        if success:
            frame_counts.append(count)
            formats.append(format_type)
    
    # Resumen
    if frame_counts:
        print(f"\n   📈 Resumen de frames:")
        print(f"      • Mínimo: {min(frame_counts)} frames")
        print(f"      • Máximo: {max(frame_counts)} frames")
        print(f"      • Promedio: {sum(frame_counts)/len(frame_counts):.1f} frames")
        
        # Verificar si necesita normalización
        needs_normalization = any(count != 15 for count in frame_counts)
        has_mixed_formats = len(set(formats)) > 1
        
        if needs_normalization:
            print(f"   ⚠️ REQUIERE NORMALIZACIÓN (objetivo: 15 frames)")
        else:
            print(f"   ✅ Ya normalizado (todos tienen 15 frames)")
        
        if has_mixed_formats:
            print(f"   ⚠️ FORMATOS MIXTOS detectados: {set(formats)}")
        else:
            print(f"   ✅ Formato consistente: {formats[0] if formats else 'N/A'}")

def main():
    """Función principal de análisis"""
    print("🧪 ANÁLISIS DE NORMALIZACIÓN DE MUESTRAS")
    print("="*60)
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("frame_actions"):
        print("❌ Directorio 'frame_actions' no encontrado")
        print("   Ejecutar desde el directorio raíz del proyecto")
        return
    
    # Obtener lista de gestos
    gestures = [d for d in os.listdir("frame_actions") 
                if os.path.isdir(os.path.join("frame_actions", d))]
    
    if not gestures:
        print("❌ No se encontraron gestos en frame_actions/")
        return
    
    print(f"📁 Gestos encontrados: {len(gestures)}")
    print(f"   {', '.join(gestures)}")
    
    # Analizar gestos principales
    priority_gestures = ["abrazar", "por_favor", "adios", "hola"]
    
    for gesture in priority_gestures:
        if gesture in gestures:
            analyze_gesture_samples(gesture)
    
    # Mostrar recomendaciones
    print(f"\n💡 RECOMENDACIONES:")
    print("="*60)
    print("1. Ejecutar normalización si hay muestras con ≠ 15 frames")
    print("2. Usar el botón 'Normalizar + Procesar Keypoints' en la interfaz")
    print("3. Verificar que todas las muestras tengan formato consistente")
    print("4. El flujo correcto es: Capturar → Normalizar → Keypoints → Entrenar")
    
    print(f"\n🚀 PARA NORMALIZAR:")
    print("   • Ir al Panel de Entrenamiento en la interfaz de admin")
    print("   • Hacer clic en 'Normalizar + Procesar Keypoints'")
    print("   • El sistema detectará y normalizará automáticamente")

if __name__ == '__main__':
    main()