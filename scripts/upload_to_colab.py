"""
Herramienta local de preparación para entrenamiento en Google Colab.
Verifica los archivos .h5 disponibles e informa cuáles subir a Drive.

Uso:
    python scripts/upload_to_colab.py
"""
import os
import sys

KEYPOINTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'keypoints')
DRIVE_FOLDER = "InterpreteSenales_Training/keypoints"

def main():
    print("=" * 55)
    print("  Preparación para entrenamiento en Google Colab")
    print("=" * 55)

    if not os.path.exists(KEYPOINTS_PATH):
        print(f"\n❌ Carpeta de keypoints no encontrada: {KEYPOINTS_PATH}")
        print("   Ejecuta primero el Paso 1 (Normalizar + Procesar Keypoints).")
        sys.exit(1)

    all_h5   = sorted(f for f in os.listdir(KEYPOINTS_PATH) if f.endswith('.h5'))
    orig     = [f for f in all_h5 if '_augmented' not in f]
    augmented = [f for f in all_h5 if '_augmented' in f]

    if not orig:
        print("\nNo hay archivos .h5 en data/keypoints/")
        print("   Ejecuta primero el Paso 1 desde el Panel de Entrenamiento.")
        sys.exit(1)

    h5_files = all_h5  # subir todos

    def _print_group(files, label):
        total = 0
        print(f"\n  {label}:")
        for f in files:
            path = os.path.join(KEYPOINTS_PATH, f)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            total += os.path.getsize(path)
            aug_tag = " (aumentado)" if '_augmented' in f else ""
            print(f"   {f:<35} {size_mb:>7.1f} MB{aug_tag}")
        return total

    print(f"\nArchivos .h5 listos para subir ({len(h5_files)} en total):")
    total_bytes  = _print_group(orig, f"Originales ({len(orig)} gestos)")
    total_bytes += _print_group(augmented, f"Aumentados ({len(augmented)} gestos — generados con augment_data.py)")

    total_mb = total_bytes / (1024 * 1024)
    if not augmented:
        print("\n  CONSEJO: ejecuta 'python augment_data.py' para generar datos")
        print("  aumentados. Mejora la robustez del modelo sin capturar mas gestos.")
    print(f"\n  Total a subir: {total_mb:.1f} MB")

    print("\n" + "=" * 55)
    print("  PASOS PARA SUBIR A GOOGLE DRIVE")
    print("=" * 55)
    print(f"""
1. Abre Google Drive en tu navegador
2. Crea esta estructura de carpetas:

   Mi unidad/
   └── {DRIVE_FOLDER.split('/')[0]}/
       ├── keypoints/    ← sube aquí los .h5
       └── output/       ← Colab guardará el modelo aquí

3. Sube estos archivos a la carpeta 'keypoints':""")

    for f in sorted(h5_files):
        path = os.path.normpath(os.path.join(KEYPOINTS_PATH, f))
        print(f"   {path}")

    print(f"""
4. Abre el notebook colab_training.ipynb en Google Colab
5. Ejecuta todas las celdas en orden
6. El modelo se guardará en Drive: {DRIVE_FOLDER.replace('keypoints','output')}/actions_15.keras
7. Descárgalo y ejecuta: python scripts/download_from_colab.py
""")

if __name__ == '__main__':
    main()
