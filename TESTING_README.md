# 🧪 Sistema de Pruebas - Gestos Simplificado

Este documento describe el sistema completo de pruebas para el proyecto de interpretación de gestos simplificado.

## 📋 Índice

- [Descripción General](#descripción-general)
- [Tipos de Pruebas](#tipos-de-pruebas)
- [Ejecución de Pruebas](#ejecución-de-pruebas)
- [Estructura de Archivos](#estructura-de-archivos)
- [Interpretación de Resultados](#interpretación-de-resultados)

## 📖 Descripción General

El sistema de pruebas verifica:
- ✅ **Funcionalidad**: Todas las funciones trabajan correctamente
- ⚡ **Rendimiento**: El sistema es eficiente y escalable
- 🔧 **Integración**: Los componentes trabajan juntos sin problemas
- 🛡️ **Robustez**: Manejo correcto de casos extremos

## 🔬 Tipos de Pruebas

### 1. Pruebas Unitarias (`test_gesture_system.py`)

#### **TestGestureDetection**
- Detección automática de gestos con muestras
- Manejo de directorios vacíos
- Filtrado de carpetas sin contenido válido
- Casos extremos de estructura de archivos

#### **TestDisplayText**
- Conversión automática de nombres de gestos
- Manejo de guiones bajos y caracteres especiales
- Casos de strings vacíos y complejos

#### **TestDatabase**
- Operaciones CRUD de usuarios
- Gestión de sesiones e interpretaciones
- Verificación de integridad de datos
- Autenticación y autorización

#### **TestKeypointProcessing**
- Procesamiento automático de keypoints
- Validación de entrada y salida
- Manejo de errores en procesamiento

#### **TestIntegration**
- Flujo completo desde creación hasta almacenamiento
- Interacción entre componentes
- Casos de uso reales

### 2. Pruebas de Rendimiento (`test_performance.py`)

#### **Escalabilidad de Detección**
- Rendimiento con 1 a 100 gestos
- Tiempo promedio por gesto
- Factor de escalamiento

#### **Rendimiento de Conversión**
- Velocidad de conversión de texto
- Diferentes tipos de nombres
- Throughput en operaciones masivas

#### **Rendimiento de Base de Datos**
- Inserción masiva de usuarios
- Creación de sesiones
- Almacenamiento de interpretaciones
- Operaciones por segundo

#### **Uso de Memoria**
- Consumo de memoria en operaciones
- Detección de memory leaks
- Eficiencia de limpieza

#### **Operaciones Concurrentes**
- Simulación de múltiples operaciones
- Throughput bajo carga
- Estabilidad del sistema

## 🚀 Ejecución de Pruebas

### Ejecución Completa (Recomendado)
```bash
python run_tests.py
```

### Ejecución Individual

#### Solo Pruebas Unitarias
```bash
python test_gesture_system.py
```

#### Solo Pruebas de Rendimiento
```bash
python test_performance.py
```

### Requisitos Previos

#### Dependencias Requeridas
- `unittest` (incluido en Python)
- `tempfile` (incluido en Python)
- `sqlite3` (incluido en Python)
- `numpy`
- `os`, `shutil`, `time`, `statistics` (incluidos en Python)

#### Dependencias Opcionales
- `psutil` (para pruebas de memoria detalladas)
```bash
pip install psutil
```

## 📁 Estructura de Archivos

```
testing/
├── test_gesture_system.py    # Pruebas unitarias principales
├── test_performance.py       # Pruebas de rendimiento y escalabilidad
├── run_tests.py              # Script ejecutor principal
└── TESTING_README.md          # Esta documentación
```

## 📊 Interpretación de Resultados

### Salida de Pruebas Unitarias

```
🧪 Iniciando pruebas unitarias del sistema de gestos simplificado...
============================================================

test_get_gestures_with_samples_empty_directory ... ok
test_get_gestures_with_samples_with_valid_gestures ... ok
...

============================================================
RESUMEN DE PRUEBAS
============================================================
Pruebas ejecutadas: 25
Exitosas: 25
Fallidas: 0
Errores: 0

Tasa de éxito: 100.0%

✅ Todas las pruebas pasaron exitosamente!
```

### Salida de Pruebas de Rendimiento

```
🔍 Probando escalabilidad de detección de gestos...
    1 gestos: 0.0012s
    5 gestos: 0.0045s
   10 gestos: 0.0089s
   ...

📊 REPORTE DE RENDIMIENTO
============================================================
🎯 MÉTRICAS CLAVE:
  • Detección de gestos: 0.89ms por gesto
  • Throughput DB: 245 interpretaciones/s
  • Operaciones concurrentes: 892 detecciones/s
  • Uso de memoria: +12.3 MB máximo

🏆 PUNTUACIÓN GENERAL: 95/100
   🟢 Excelente rendimiento
```

### Códigos de Salida

- **0**: Todas las pruebas pasaron exitosamente
- **1**: Algunas pruebas fallaron o hubo errores

## 🎯 Métricas de Referencia

### Rendimiento Aceptable

| Métrica | Valor Objetivo | Crítico |
|---------|----------------|---------|
| Detección por gesto | < 2ms | > 10ms |
| Interpretaciones/s | > 100 | < 50 |
| Escalabilidad (100 vs 1) | < 5x | > 20x |
| Uso de memoria | < 50MB | > 200MB |
| Tasa de éxito unitarias | 100% | < 95% |

### Puntuación de Rendimiento

- **90-100**: 🟢 Excelente rendimiento
- **70-89**: 🟡 Buen rendimiento, mejoras menores
- **50-69**: 🟠 Rendimiento aceptable, optimización recomendada
- **< 50**: 🔴 Rendimiento deficiente, optimización requerida

## 🐛 Solución de Problemas

### Errores Comunes

#### "ModuleNotFoundError"
```bash
# Asegurar que está en el directorio correcto
cd /path/to/proyecto

# Instalar dependencias faltantes
pip install numpy psutil
```

#### "No such file or directory"
```bash
# Verificar que los archivos del proyecto existen
ls -la constants.py training_utils.py database.py
```

#### Pruebas fallan por permisos
```bash
# Ejecutar con permisos adecuados
chmod +x run_tests.py
python run_tests.py
```

### Depuración Avanzada

#### Ejecutar prueba específica
```python
# En test_gesture_system.py
if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestGestureDetection('test_get_gestures_with_samples_with_valid_gestures'))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
```

#### Ver salida detallada
```bash
python test_gesture_system.py -v
```

## 🔄 Integración Continua

### Pre-commit Hook
```bash
#!/bin/sh
# .git/hooks/pre-commit
python run_tests.py
if [ $? -ne 0 ]; then
    echo "Pruebas fallaron. Commit cancelado."
    exit 1
fi
```

### Automatización
```bash
# Ejecutar pruebas cada noche
0 2 * * * cd /path/to/proyecto && python run_tests.py >> tests.log 2>&1
```

## 📈 Métricas y Monitoreo

### Tracking de Rendimiento
- Ejecutar pruebas regularmente
- Mantener histórico de métricas
- Alertas si el rendimiento degrada

### Reportes de Calidad
- Cobertura de código
- Complejidad ciclomática
- Deuda técnica

## 🤝 Contribuciones

### Agregar Nuevas Pruebas

1. **Pruebas Unitarias**: Agregar a `TestXXX` en `test_gesture_system.py`
2. **Pruebas de Rendimiento**: Agregar método a `PerformanceTestSuite`
3. **Documentar**: Actualizar este README

### Estándares de Calidad

- Todas las funciones públicas deben tener pruebas
- Cobertura mínima del 90%
- Pruebas deben ser independientes y determinísticas
- Tiempo de ejecución < 60 segundos total

---

*Última actualización: 2024*