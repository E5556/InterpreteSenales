import cv2
import numpy as np
import os
import shutil
from constants import *


# Leer frames de un directorio con orden correcto
def read_frames_from_directory(directory):
    frames = []
    # Ordenar los archivos numéricamente si sus nombres contienen números
    filenames = sorted(os.listdir(directory), key=lambda x: int(x.split('_')[-1].split('.')[0]))

    for filename in filenames:
        if filename.endswith('.jpg'):
            frame = cv2.imread(os.path.join(directory, filename))
            if frame is not None:  # Verificar si el frame fue leído correctamente
                frames.append(frame)
    return frames


# Interpolar frames para alcanzar el conteo deseado
def interpolate_frames(frames, target_frame_count=15):
    current_frame_count = len(frames)
    indices = np.linspace(0, current_frame_count - 1, target_frame_count)
    interpolated_frames = []

    for i in range(len(indices)):
        lower_idx = int(indices[i])
        upper_idx = min(lower_idx + 1, current_frame_count - 1)
        weight = indices[i] - lower_idx
        # Interpolar frames evitando la repetición del último frame
        if lower_idx == upper_idx:
            interpolated_frames.append(frames[lower_idx])
        else:
            interpolated_frame = cv2.addWeighted(frames[lower_idx], 1 - weight, frames[upper_idx], weight, 0)
            interpolated_frames.append(interpolated_frame)

    return interpolated_frames


# Normalizar el número de frames manteniendo orden
def normalize_frames(frames, target_frame_count=15):
    current_frame_count = len(frames)
    if current_frame_count < target_frame_count:
        # Interpolación si hay menos frames
        return interpolate_frames(frames, target_frame_count)
    elif current_frame_count > target_frame_count:
        # Muestreo uniforme si hay más frames
        indices = np.linspace(0, current_frame_count - 1, target_frame_count).astype(int)
        return [frames[i] for i in indices]
    else:
        return frames


# Procesar un directorio específico
def process_directory(word_directory, target_frame_count=15):
    for sample_name in os.listdir(word_directory):
        sample_directory = os.path.join(word_directory, sample_name)
        if os.path.isdir(sample_directory):
            frames = read_frames_from_directory(sample_directory)
            if not frames:
                continue  # Saltar si no hay frames

            normalized_frames = normalize_frames(frames, target_frame_count)
            clear_directory(sample_directory)  # Limpiar antes de guardar
            save_normalized_frames(sample_directory, normalized_frames)


# Guardar los frames normalizados
def save_normalized_frames(directory, frames):
    for i, frame in enumerate(frames, start=1):
        cv2.imwrite(os.path.join(directory, f'frame_{i:02}.jpg'), frame, [cv2.IMWRITE_JPEG_QUALITY, 50])


# Limpiar el contenido de un directorio
def clear_directory(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Error al eliminar {file_path}: {e}")


# Ejecución principal
if __name__ == "__main__":
    word_ids = [word for word in os.listdir(os.path.join(ROOT_PATH, FRAME_ACTIONS_PATH))]

    for word_id in word_ids:
        word_path = os.path.join(FRAME_ACTIONS_PATH, word_id)
        if os.path.isdir(word_path):
            print(f'Normalizando frames para "{word_id}"...')
            process_directory(word_path, MODEL_FRAMES)

    # sample_directory = r"E:\Data\LSP Project\RED NEURONAL\frame_actions\buenos_dias\sample_240113195007489206"
    # frames = read_frames_from_directory(sample_directory)
    # normalized_frames = normalize_frames(frames, 15)
    # clear_directory(sample_directory)
    # save_normalized_frames(sample_directory, normalized_frames)