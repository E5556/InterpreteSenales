"""
Herramienta local para validar e instalar el modelo descargado de Google Colab.
Verifica que el .keras sea compatible y lo copia a la ruta correcta.

Uso:
    python scripts/download_from_colab.py <ruta_al_archivo_descargado.keras>

Ejemplo:
    python scripts/download_from_colab.py C:\\Users\\e5556\\Downloads\\actions_15.keras
"""
import sys
import os
import shutil

MODEL_DEST = os.path.join(os.path.dirname(__file__), '..', 'models', 'actions_15.keras')
MODEL_DEST = os.path.normpath(MODEL_DEST)
KEYPOINTS_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data', 'keypoints'))

def main():
    print("=" * 55)
    print("  Instalación de modelo entrenado en Colab")
    print("=" * 55)

    if len(sys.argv) < 2:
        print("\nUso: python scripts/download_from_colab.py <ruta_al_.keras>")
        print("\nEjemplo:")
        print('  python scripts/download_from_colab.py "C:\\Users\\e5556\\Downloads\\actions_15.keras"')
        sys.exit(1)

    source = sys.argv[1]

    if not os.path.exists(source):
        print(f"\n❌ Archivo no encontrado: {source}")
        sys.exit(1)

    size_mb = os.path.getsize(source) / (1024 * 1024)
    print(f"\n📦 Archivo encontrado: {source}")
    print(f"   Tamaño: {size_mb:.2f} MB")

    # Validar que carga correctamente
    print("\n🔍 Validando modelo...")
    try:
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        import tensorflow as tf
        model = tf.keras.models.load_model(source)
        input_shape = model.input_shape
        output_shape = model.output_shape
        print(f"   ✅ Modelo cargado correctamente")
        print(f"   Input:  {input_shape}  → debe ser (None, 15, 1662)")
        print(f"   Output: {output_shape} → número de gestos")

        # Verificar compatibilidad de dimensiones
        if input_shape[1] != 15 or input_shape[2] != 1662:
            print(f"\n⚠️  ADVERTENCIA: dimensiones inesperadas.")
            print(f"   Esperado (None, 15, 1662) — obtenido {input_shape}")
            print(f"   El modelo puede no ser compatible con esta versión de la app.")
            resp = input("\n¿Instalar de todas formas? (s/n): ").strip().lower()
            if resp != 's':
                print("Instalación cancelada.")
                sys.exit(0)

        # Contar gestos detectados en keypoints
        n_gestos_local = len([f for f in os.listdir(KEYPOINTS_PATH) if f.endswith('.h5')]) if os.path.exists(KEYPOINTS_PATH) else "?"
        n_gestos_modelo = output_shape[-1]
        if isinstance(n_gestos_local, int) and n_gestos_local != n_gestos_modelo:
            print(f"\n⚠️  El modelo tiene {n_gestos_modelo} gestos pero localmente hay {n_gestos_local} archivos .h5.")
            print(f"   Asegúrate de que los .h5 subidos a Colab sean los mismos que tienes ahora.")

    except Exception as e:
        print(f"\n❌ Error al cargar el modelo: {e}")
        print("   El archivo puede estar corrupto o ser incompatible.")
        sys.exit(1)

    # Backup del modelo anterior si existe
    if os.path.exists(MODEL_DEST):
        backup = MODEL_DEST.replace('.keras', '_backup.keras')
        shutil.copy2(MODEL_DEST, backup)
        print(f"\n💾 Backup del modelo anterior guardado en:")
        print(f"   {backup}")

    # Instalar modelo nuevo
    os.makedirs(os.path.dirname(MODEL_DEST), exist_ok=True)
    shutil.copy2(source, MODEL_DEST)
    print(f"\n✅ Modelo instalado correctamente en:")
    print(f"   {MODEL_DEST}")
    print("\n🚀 Ya puedes abrir la app y probar el reconocimiento.")

if __name__ == '__main__':
    main()
