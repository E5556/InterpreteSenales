import json
import os
import cv2
from mediapipe.python.solutions.holistic import FACEMESH_CONTOURS, POSE_CONNECTIONS, HAND_CONNECTIONS
from mediapipe.python.solutions.drawing_utils import draw_landmarks, DrawingSpec
import numpy as np
import pandas as pd
from typing import NamedTuple
from constants import *

# GENERAL
def mediapipe_detection(image, model):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = model.process(image)
    return results

def create_folder(path):
    '''
    ### CREAR CARPETA SI NO EXISTE
    Si ya existe, no hace nada.
    '''
    if not os.path.exists(path):
        os.makedirs(path)

def there_hand(results: NamedTuple) -> bool:
    """
    Detecta si hay manos presentes en el frame con detección de calidad.
    Nota: MediaPipe hand landmarks no tienen atributo 'visibility' (solo pose lo tiene).
    Se valida calidad verificando que las coordenadas estén en rango [0,1].
    """
    left_hand_present = results.left_hand_landmarks is not None
    right_hand_present = results.right_hand_landmarks is not None

    if not (left_hand_present or right_hand_present):
        return False

    min_valid_landmarks = 15

    if left_hand_present:
        left_valid = sum(
            1 for lm in results.left_hand_landmarks.landmark
            if 0.0 <= lm.x <= 1.0 and 0.0 <= lm.y <= 1.0
        )
        if left_valid >= min_valid_landmarks:
            return True

    if right_hand_present:
        right_valid = sum(
            1 for lm in results.right_hand_landmarks.landmark
            if 0.0 <= lm.x <= 1.0 and 0.0 <= lm.y <= 1.0
        )
        if right_valid >= min_valid_landmarks:
            return True

    return False

# get_word_ids eliminada - ahora se usa detección automática desde training_utils

# CAPTURE SAMPLES
def draw_keypoints(image, results):
    '''
    Dibuja los keypoints en la imagen
    '''
    draw_landmarks(
        image,
        results.face_landmarks,
        FACEMESH_CONTOURS,
        DrawingSpec(color=(80, 110, 10), thickness=1, circle_radius=1),
        DrawingSpec(color=(80, 256, 121), thickness=1, circle_radius=1),
    )
    # Draw pose connections
    draw_landmarks(
        image,
        results.pose_landmarks,
        POSE_CONNECTIONS,
        DrawingSpec(color=(80, 22, 10), thickness=2, circle_radius=4),
        DrawingSpec(color=(80, 44, 121), thickness=2, circle_radius=2),
    )
    # Draw left hand connections
    draw_landmarks(
        image,
        results.left_hand_landmarks,
        HAND_CONNECTIONS,
        DrawingSpec(color=(121, 22, 76), thickness=2, circle_radius=4),
        DrawingSpec(color=(121, 44, 250), thickness=2, circle_radius=2),
    )
    # Draw right hand connections
    draw_landmarks(
        image,
        results.right_hand_landmarks,
        HAND_CONNECTIONS,
        DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=4),
        DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2),
    )

def save_frames(frames, output_folder):
    for num_frame, frame in enumerate(frames):
        frame_path = os.path.join(output_folder, f"{num_frame + 1}.jpg")
        cv2.imwrite(frame_path, cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA))

# CREATE KEYPOINTS
# (Funciones movidas a training_utils.py)

def insert_keypoints_sequence(df, n_sample:int, kp_seq):
    '''
    ### INSERTA LOS KEYPOINTS DE LA MUESTRA AL DATAFRAME
    Retorna el mismo DataFrame pero con los keypoints de la muestra agregados
    '''
    for frame, keypoints in enumerate(kp_seq):
        data = {'sample': n_sample, 'frame': frame + 1, 'keypoints': [keypoints]}
        df_keypoints = pd.DataFrame(data)
        df = pd.concat([df, df_keypoints])
    
    return df

# TRAINING MODEL
def get_sequences_and_labels(word_ids):
    sequences = []
    labels = []

    for word_index, word_id in enumerate(word_ids):
        hdf_path = os.path.join(KEYPOINTS_PATH, f"{word_id}.h5")
        print(f"Cargando datos desde {hdf_path}")
        try:
            data = pd.read_hdf(hdf_path, key='data')
            if data.empty:
                print(f"El archivo {hdf_path} está vacío.")
                continue
            print(f"Datos cargados para {word_id}: {data.head()}")
            for _, df_sample in data.groupby('sample'):
                seq_keypoints = [fila['keypoints'] for _, fila in df_sample.iterrows()]
                sequences.append(seq_keypoints)
                labels.append(word_index)
        except Exception as e:
            print(f"Error al cargar datos desde {hdf_path}: {e}")

    return sequences, labels
