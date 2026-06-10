"""
Data Augmentation para keypoints de LSC.

Genera variantes aumentadas de cada archivo .h5 de keypoints:
  - Ruido gaussiano leve (simula variaciones de cámara/iluminación)
  - Flip horizontal (reflejo de la mano, amplía variabilidad)
  - Variación de velocidad (interpolación temporal ±20%)

Uso:
    python augment_data.py                  # aumenta todos los gestos
    python augment_data.py --gesture hola   # solo un gesto
    python augment_data.py --factor 3       # 3 copias aumentadas por muestra (default: 4)

Salida: data/keypoints/<gesto>_augmented.h5  (mismo formato que el original)
Los archivos originales NO se modifican.
"""

import argparse
import os
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

KEYPOINTS_PATH = os.path.join(os.path.dirname(__file__), "data", "keypoints")
MODEL_FRAMES   = 15
KP_LENGTH      = 1662

# ── Límites de los bloques de keypoints (MediaPipe Holistic) ──────────────────
# pose: 33 landmarks × 4 (x,y,z,vis) = 132
# face: 468 landmarks × 3 (x,y,z)    = 1404
# left_hand: 21 × 3                   = 63
# right_hand: 21 × 3                  = 63
# Total = 1662

POSE_END       = 132
FACE_END       = POSE_END + 1404          # 1536
LHAND_END      = FACE_END + 63            # 1599
RHAND_END      = LHAND_END + 63           # 1662

# Índices x dentro de cada bloque (para flip: invertir x = 1 - x)
# Pose: x está en posición 0,4,8,... (cada landmark ocupa 4 valores)
# Face/Hands: x está en posición 0,3,6,... (cada landmark ocupa 3 valores)

def _flip_keypoints(kp: np.ndarray) -> np.ndarray:
    """Refleja horizontalmente (x → 1-x) e intercambia mano izq/der."""
    flipped = kp.copy()

    # Pose (132 valores, 33 landmarks × 4)
    pose = flipped[:POSE_END].reshape(33, 4)
    pose[:, 0] = 1.0 - pose[:, 0]
    flipped[:POSE_END] = pose.flatten()

    # Face (1404 valores, 468 × 3)
    face = flipped[POSE_END:FACE_END].reshape(468, 3)
    face[:, 0] = 1.0 - face[:, 0]
    flipped[POSE_END:FACE_END] = face.flatten()

    # Hands: intercambiar izquierda ↔ derecha + flip x
    lh = flipped[FACE_END:LHAND_END].copy().reshape(21, 3)
    rh = flipped[LHAND_END:RHAND_END].copy().reshape(21, 3)
    lh[:, 0] = 1.0 - lh[:, 0]
    rh[:, 0] = 1.0 - rh[:, 0]
    flipped[FACE_END:LHAND_END]  = rh.flatten()   # rh pasa a slot de lh
    flipped[LHAND_END:RHAND_END] = lh.flatten()   # lh pasa a slot de rh

    return flipped


def _add_gaussian_noise(seq: np.ndarray, std: float = 0.005) -> np.ndarray:
    """Agrega ruido gaussiano leve a la secuencia (shape: frames × kp_len)."""
    noise = np.random.normal(0, std, seq.shape).astype(np.float32)
    return seq + noise


def _time_warp(seq: np.ndarray, factor: float) -> np.ndarray:
    """
    Comprime o expande la secuencia temporalmente y re-muestrea a MODEL_FRAMES.
    factor < 1 → más lento (expansión); factor > 1 → más rápido (compresión).
    """
    n_frames = seq.shape[0]
    # Índices originales
    orig_idx = np.linspace(0, n_frames - 1, n_frames)
    # Índices "estirados" según factor
    new_len  = max(3, int(round(n_frames * factor)))
    new_idx  = np.linspace(0, n_frames - 1, new_len)
    # Interpolar cada keypoint a lo largo del tiempo
    warped = np.zeros((new_len, seq.shape[1]), dtype=np.float32)
    for k in range(seq.shape[1]):
        f = interp1d(orig_idx, seq[:, k], kind='linear')
        warped[:, k] = f(new_idx)
    # Re-muestrar a MODEL_FRAMES fijos
    final_idx  = np.linspace(0, new_len - 1, MODEL_FRAMES)
    resampled  = np.zeros((MODEL_FRAMES, seq.shape[1]), dtype=np.float32)
    for k in range(seq.shape[1]):
        f = interp1d(np.arange(new_len), warped[:, k], kind='linear')
        resampled[:, k] = f(final_idx)
    return resampled


def augment_gesture(gesture: str, factor: int = 4) -> int:
    """
    Lee <gesture>.h5, genera `factor` copias aumentadas por muestra original,
    guarda resultado en <gesture>_augmented.h5.
    Retorna el número total de muestras aumentadas generadas.
    """
    src = os.path.join(KEYPOINTS_PATH, f"{gesture}.h5")
    dst = os.path.join(KEYPOINTS_PATH, f"{gesture}_augmented.h5")

    if not os.path.exists(src):
        print(f"  [!] No encontrado: {src}")
        return 0

    df = pd.read_hdf(src, "data")
    samples_orig = df["sample"].nunique()
    print(f"  {gesture}: {samples_orig} muestras originales -> generando {samples_orig * factor} aumentadas")

    rows = []
    new_sample_id = 1

    # Agrupar por muestra → (15 frames × 1662 kp)
    for sid, grp in df.groupby("sample"):
        grp_sorted = grp.sort_values("frame")
        seq = np.array([np.array(row) for row in grp_sorted["keypoints"]], dtype=np.float32)
        # seq shape: (15, 1662)

        augmentations = _build_augmentations(seq, factor)

        for aug_seq in augmentations:
            for frame_idx in range(MODEL_FRAMES):
                rows.append({
                    "sample":    new_sample_id,
                    "frame":     frame_idx + 1,
                    "keypoints": aug_seq[frame_idx].tolist(),
                })
            new_sample_id += 1

    df_aug = pd.DataFrame(rows)
    df_aug.to_hdf(dst, key="data", mode="w")
    print(f"  OK Guardado: {dst}  ({new_sample_id - 1} muestras totales)")
    return new_sample_id - 1


def _build_augmentations(seq: np.ndarray, factor: int) -> list:
    """
    Genera `factor` variantes de una secuencia combinando las técnicas.
    Siempre incluye variantes diversas cuando factor >= 4.
    """
    variants = []
    rng = np.random.default_rng()

    techniques = [
        # (nombre, función)
        ("noise",       lambda s: _add_gaussian_noise(s, std=rng.uniform(0.003, 0.008))),
        ("flip",        lambda s: np.array([_flip_keypoints(f) for f in s])),
        ("slow",        lambda s: _time_warp(s, factor=rng.uniform(0.75, 0.90))),
        ("fast",        lambda s: _time_warp(s, factor=rng.uniform(1.10, 1.25))),
        ("noise+flip",  lambda s: np.array([_flip_keypoints(f) for f in _add_gaussian_noise(s, 0.004)])),
        ("noise+slow",  lambda s: _time_warp(_add_gaussian_noise(s, 0.004), rng.uniform(0.80, 0.95))),
        ("noise+fast",  lambda s: _time_warp(_add_gaussian_noise(s, 0.004), rng.uniform(1.05, 1.20))),
        ("flip+slow",   lambda s: _time_warp(np.array([_flip_keypoints(f) for f in s]), rng.uniform(0.80, 0.95))),
    ]

    selected = techniques[:factor] if factor <= len(techniques) else techniques
    for _, fn in selected:
        variants.append(fn(seq).astype(np.float32))

    return variants


def main():
    parser = argparse.ArgumentParser(description="Data augmentation para keypoints LSC")
    parser.add_argument("--gesture", type=str, default=None,
                        help="Nombre del gesto a aumentar (default: todos)")
    parser.add_argument("--factor",  type=int, default=4,
                        help="Copias aumentadas por muestra original (default: 4)")
    args = parser.parse_args()

    gestures = (
        [args.gesture] if args.gesture
        else [f.replace(".h5", "") for f in os.listdir(KEYPOINTS_PATH)
              if f.endswith(".h5") and not f.endswith("_augmented.h5")]
    )

    print(f"\n=== Data Augmentation LSC ===")
    print(f"Factor: ×{args.factor} por muestra  |  Gestos: {gestures}\n")

    total = 0
    for g in gestures:
        total += augment_gesture(g, factor=args.factor)

    print(f"\nListo. Total muestras aumentadas generadas: {total}")
    print("   Archivos en: data/keypoints/*_augmented.h5")
    print("   Para entrenar: combina originales + aumentados en el notebook de Colab.")


if __name__ == "__main__":
    main()
