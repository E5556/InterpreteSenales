import os
import cv2
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import pandas as pd
import shutil
from datetime import datetime
from mediapipe.python.solutions.holistic import Holistic
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.callbacks import Callback
from helpers import (create_folder, draw_keypoints, mediapipe_detection, 
                     save_frames, there_hand, get_sequences_and_labels, 
                     insert_keypoints_sequence)
from constants import *
from model import get_model

# --- Lógica de Extracción de Keypoints (Movida desde helpers.py) ---
def extract_keypoints(results):
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    face = np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark]).flatten() if results.face_landmarks else np.zeros(468*3)
    lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose, face, lh, rh])

def get_sorted_image_files(sample_path):
    """
    Obtiene archivos de imagen ordenados correctamente, manejando diferentes formatos:
    - frame_01.jpg, frame_02.jpg, ... (formato antiguo)
    - 1.jpg, 2.jpg, ... (formato nuevo)
    """
    import re
    
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

def get_keypoints(model, sample_path):
    '''
    ### OBTENER KEYPOINTS DE LA MUESTRA
    Retorna la secuencia de keypoints de la muestra con orden correcto
    '''
    kp_seq = np.array([])
    
    # Obtener archivos ordenados correctamente
    sorted_files = get_sorted_image_files(sample_path)
    
    for img_name in sorted_files:
        img_path = os.path.join(sample_path, img_name)
        frame = cv2.imread(img_path)
        if frame is not None:  # Verificar que la imagen se cargó correctamente
            results = mediapipe_detection(frame, model)
            kp_frame = extract_keypoints(results)
            kp_seq = np.concatenate([kp_seq, [kp_frame]] if kp_seq.size > 0 else [[kp_frame]])
    
    return kp_seq

# --- Lógica de Normalización de Muestras ---

def read_frames_from_directory(directory):
    """Leer frames de un directorio con orden correcto"""
    frames = []
    # Usar nuestra función mejorada de ordenamiento
    sorted_files = get_sorted_image_files(directory)
    
    for filename in sorted_files:
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            frame_path = os.path.join(directory, filename)
            frame = cv2.imread(frame_path)
            if frame is not None:  # Verificar si el frame fue leído correctamente
                frames.append(frame)
    return frames

def interpolate_frames(frames, target_frame_count=15):
    """Interpolar frames para alcanzar el conteo deseado"""
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

def normalize_frames(frames, target_frame_count=15):
    """Normalizar el número de frames manteniendo orden"""
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

def save_normalized_frames(directory, frames):
    """Guardar los frames normalizados con formato consistente"""
    for i, frame in enumerate(frames, start=1):
        frame_path = os.path.join(directory, f'frame_{i:02d}.jpg')
        cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 50])

def clear_directory(directory):
    """Limpiar el contenido de un directorio"""
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Error al eliminar {file_path}: {e}")

def normalize_gesture_samples(gesture_name, target_frame_count=15, progress_callback=None):
    """Normalizar muestras de un gesto específico"""
    gesture_path = os.path.join(FRAME_ACTIONS_PATH, gesture_name)
    
    if not os.path.exists(gesture_path):
        return False
    
    sample_dirs = [d for d in os.listdir(gesture_path) 
                   if os.path.isdir(os.path.join(gesture_path, d))]
    
    total_samples = len(sample_dirs)
    
    for i, sample_name in enumerate(sample_dirs):
        if progress_callback:
            progress = i / total_samples
            progress_callback(progress, f"Normalizando '{gesture_name}' - muestra {i+1}/{total_samples}")
        
        sample_directory = os.path.join(gesture_path, sample_name)
        
        # Leer frames originales
        frames = read_frames_from_directory(sample_directory)
        if not frames:
            continue  # Saltar si no hay frames
        
        # Normalizar frames
        normalized_frames = normalize_frames(frames, target_frame_count)
        
        # Limpiar directorio y guardar frames normalizados
        clear_directory(sample_directory)
        save_normalized_frames(sample_directory, normalized_frames)
    
    return True

def normalize_all_gestures(gesture_names, progress_callback=None):
    """Normalizar muestras de todos los gestos"""
    total_gestures = len(gesture_names)
    
    for i, gesture_name in enumerate(gesture_names):
        if progress_callback:
            base_progress = i / total_gestures
            def gesture_progress(sub_progress, message):
                overall_progress = base_progress + (sub_progress / total_gestures)
                progress_callback(overall_progress, message)
        else:
            gesture_progress = None
        
        success = normalize_gesture_samples(gesture_name, MODEL_FRAMES, gesture_progress)
        
        if not success:
            if progress_callback:
                progress_callback(i / total_gestures, f"Error normalizando '{gesture_name}'")
    
    if progress_callback:
        progress_callback(1.0, "¡Normalización de todos los gestos completada!")
    
    return True

# --- Detección Simplificada de Gestos ---

def get_all_gesture_folders():
    """
    Obtiene TODOS los gestos (carpetas) en frame_actions/, incluso si están vacíos.
    Útil para el gesture manager que necesita mostrar gestos recién creados.
    """
    if not os.path.exists(FRAME_ACTIONS_PATH):
        return []
    
    all_gestures = []
    
    for gesture_name in os.listdir(FRAME_ACTIONS_PATH):
        gesture_path = os.path.join(FRAME_ACTIONS_PATH, gesture_name)
        
        # Solo carpetas
        if os.path.isdir(gesture_path):
            all_gestures.append(gesture_name)
    
    return sorted(all_gestures)

def get_gestures_with_samples():
    """
    Obtiene automáticamente todos los gestos que tienen muestras en frame_actions/
    Solo incluye carpetas que realmente tienen samples con frames
    """
    if not os.path.exists(FRAME_ACTIONS_PATH):
        return []
    
    gestures_with_samples = []
    
    for gesture_name in os.listdir(FRAME_ACTIONS_PATH):
        gesture_path = os.path.join(FRAME_ACTIONS_PATH, gesture_name)
        
        # Solo carpetas
        if not os.path.isdir(gesture_path):
            continue
            
        # Verificar que tenga samples
        try:
            sample_folders = [item for item in os.listdir(gesture_path) 
                             if os.path.isdir(os.path.join(gesture_path, item))]
            
            # Solo incluir si tiene al menos 1 sample con frames
            if sample_folders:
                # Verificar que al menos un sample tenga frames
                has_frames = False
                for sample_folder in sample_folders:
                    sample_path = os.path.join(gesture_path, sample_folder)
                    if os.path.exists(sample_path):
                        frame_files = [f for f in os.listdir(sample_path) 
                                      if f.endswith(('.jpg', '.jpeg', '.png'))]
                        if frame_files:
                            has_frames = True
                            break
                
                if has_frames:
                    gestures_with_samples.append(gesture_name)
        except OSError:
            # Saltar carpetas que no se pueden leer
            continue
    
    return sorted(gestures_with_samples)

def create_keypoints_for_all_gestures(progress_callback=None):
    """
    Versión simplificada que automáticamente detecta y procesa TODOS los gestos con muestras
    """
    # Detectar automáticamente gestos con muestras
    gesture_names = get_gestures_with_samples()
    
    if not gesture_names:
        if progress_callback:
            progress_callback(1.0, "No se encontraron gestos con muestras")
        return False
    
    if progress_callback:
        progress_callback(0.1, f"Detectados {len(gesture_names)} gestos: {', '.join(gesture_names)}")
    
    # Usar la función existente
    return create_keypoints_for_gestures(gesture_names, progress_callback)

def normalize_and_create_keypoints_single_gesture(gesture_name, progress_callback=None):
    """
    FLUJO OPTIMIZADO PARA UN SOLO GESTO: Normaliza + crea keypoints específicamente para un gesto.
    Más eficiente para cuando se agrega/actualiza un gesto específico sin reprocesar otros.
    """
    if progress_callback:
        progress_callback(0.05, f"Procesando gesto: '{gesture_name}'")
    
    # Verificar que el gesto exista y tenga muestras
    gesture_path = os.path.join(FRAME_ACTIONS_PATH, gesture_name)
    if not os.path.exists(gesture_path):
        if progress_callback:
            progress_callback(1.0, f"Error: Gesto '{gesture_name}' no encontrado")
        return False
    
    sample_dirs = [d for d in os.listdir(gesture_path) 
                   if os.path.isdir(os.path.join(gesture_path, d))]
    
    if not sample_dirs:
        if progress_callback:
            progress_callback(1.0, f"Error: No hay muestras para el gesto '{gesture_name}'")
        return False
    
    # FASE 1/2: Normalización del gesto específico
    if progress_callback:
        progress_callback(0.1, f"FASE 1/2: Normalizando '{gesture_name}' ({len(sample_dirs)} muestras)...")
    
    def normalize_progress(value, message):
        normalized_progress = 0.1 + (value * 0.4)
        if progress_callback:
            progress_callback(normalized_progress, f"NORMALIZACIÓN: {message}")
    
    try:
        success = normalize_gesture_samples(gesture_name, MODEL_FRAMES, normalize_progress)
        if not success:
            if progress_callback:
                progress_callback(0.1, f"Error normalizando '{gesture_name}'")
            return False
    except Exception as e:
        if progress_callback:
            progress_callback(0.1, f"Error en normalización: {str(e)}")
        return False
    
    # FASE 2/2: Creación de keypoints para el gesto específico
    if progress_callback:
        progress_callback(0.5, f"FASE 2/2: Creando keypoints para '{gesture_name}'...")
    
    def keypoints_progress(value, message):
        keypoints_progress_val = 0.5 + (value * 0.5)
        if progress_callback:
            progress_callback(keypoints_progress_val, f"KEYPOINTS: {message}")
    
    try:
        result = create_keypoints_for_gestures([gesture_name], keypoints_progress)
        if progress_callback:
            progress_callback(1.0, f"¡Gesto '{gesture_name}' procesado completamente!")
        return result
    except Exception as e:
        if progress_callback:
            progress_callback(0.5, f"Error en keypoints: {str(e)}")
        return False

def normalize_and_create_keypoints(progress_callback=None):
    """
    FLUJO COMPLETO: Detecta gestos → Normaliza muestras → Crea keypoints
    Esta función implementa el flujo correcto del README.md
    """
    # Paso 1: Detectar automáticamente gestos con muestras
    gesture_names = get_gestures_with_samples()
    
    if not gesture_names:
        if progress_callback:
            progress_callback(1.0, "No se encontraron gestos con muestras")
        return False
    
    if progress_callback:
        progress_callback(0.05, f"Detectados {len(gesture_names)} gestos: {', '.join(gesture_names)}")
    
    # Paso 2: Normalizar muestras (0.05 - 0.50)
    if progress_callback:
        progress_callback(0.1, "FASE 1/2: Normalizando muestras...")
    
    def normalize_progress(value, message):
        # Mapear progreso de normalización a rango 0.1 - 0.5
        normalized_progress = 0.1 + (value * 0.4)
        if progress_callback:
            progress_callback(normalized_progress, f"NORMALIZACIÓN: {message}")
    
    try:
        normalize_all_gestures(gesture_names, normalize_progress)
    except Exception as e:
        if progress_callback:
            progress_callback(0.1, f"Error en normalización: {str(e)}")
        return False
    
    # Paso 3: Crear keypoints (0.50 - 1.0)
    if progress_callback:
        progress_callback(0.5, "FASE 2/2: Creando keypoints...")
    
    def keypoints_progress(value, message):
        # Mapear progreso de keypoints a rango 0.5 - 1.0
        keypoints_progress_val = 0.5 + (value * 0.5)
        if progress_callback:
            progress_callback(keypoints_progress_val, f"KEYPOINTS: {message}")
    
    try:
        result = create_keypoints_for_gestures(gesture_names, keypoints_progress)
        if progress_callback:
            progress_callback(1.0, "¡Proceso completo: Normalización + Keypoints terminado!")
        return result
    except Exception as e:
        if progress_callback:
            progress_callback(0.5, f"Error en keypoints: {str(e)}")
        return False

# --- Lógica de Creación de Keypoints ---

def create_keypoints_for_gestures(gesture_names, progress_callback=None):
    """
    Procesa las carpetas de muestras para una lista de gestos y crea los archivos HDF5 de keypoints.
    """
    create_folder(KEYPOINTS_PATH)
    total_gestures = len(gesture_names)
    
    for i, gesture_name in enumerate(gesture_names):
        hdf_path = os.path.join(KEYPOINTS_PATH, f"{gesture_name}.h5")
        frames_path = os.path.join(FRAME_ACTIONS_PATH, gesture_name)
        
        if progress_callback:
            progress_callback(i / total_gestures, f"Procesando '{gesture_name}'...")
        
        data = pd.DataFrame([])
        with Holistic() as holistic:
            sample_list = os.listdir(frames_path)
            for n_sample, sample_name in enumerate(sample_list, start=1):
                sample_path = os.path.join(frames_path, sample_name)
                keypoints_sequence = get_keypoints(holistic, sample_path)
                data = insert_keypoints_sequence(data, n_sample, keypoints_sequence)
        
        # Guardar con formato optimizado para evitar advertencias de PyTables
        try:
            # Intentar guardar con formato fixed (más eficiente)
            data.to_hdf(hdf_path, key="data", mode="w", format="fixed")
        except Exception:
            # Si falla, usar formato table (más compatible pero con advertencias)
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*performance may suffer.*")
                data.to_hdf(hdf_path, key="data", mode="w")

    if progress_callback:
        progress_callback(1.0, "¡Proceso de creación de keypoints completado!")
    return True

# --- Lógica de Entrenamiento ---

class TrainingCallback(Callback):
    def __init__(self, epoch_callback):
        self.epoch_callback = epoch_callback

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        self.epoch_callback(epoch + 1, logs)

def get_gestures_with_valid_keypoints():
    """
    Obtiene solo los gestos que tienen keypoints válidos (archivos .h5 existentes).
    Evita errores de entrenamiento por gestos sin keypoints.
    """
    gestures_with_samples = get_gestures_with_samples()
    valid_gestures = []
    
    for gesture in gestures_with_samples:
        hdf_path = os.path.join(KEYPOINTS_PATH, f"{gesture}.h5")
        if os.path.exists(hdf_path):
            try:
                # Verificar que el archivo no esté corrupto
                import pandas as pd
                data = pd.read_hdf(hdf_path, key='data')
                if not data.empty:
                    valid_gestures.append(gesture)
                else:
                    print(f"⚠️ Saltando '{gesture}': archivo keypoints vacío")
            except Exception as e:
                print(f"⚠️ Saltando '{gesture}': error en keypoints - {e}")
        else:
            print(f"⚠️ Saltando '{gesture}': no tiene keypoints generados")
    
    print(f"✅ Gestos válidos para entrenamiento: {len(valid_gestures)}/{len(gestures_with_samples)}")
    return valid_gestures

def train_model_logic(epochs=500, epoch_callback=None):
    """
    Entrena el modelo de red neuronal.
    Solo incluye gestos con keypoints válidos.
    """
    word_ids = get_gestures_with_valid_keypoints()  # Usar gestos con keypoints válidos
    
    if len(word_ids) < 2:
        raise ValueError(f"Se necesitan al menos 2 gestos con keypoints válidos para entrenar. "
                        f"Encontrados: {len(word_ids)}")
    
    sequences, labels = get_sequences_and_labels(word_ids)
    
    sequences = pad_sequences(sequences, maxlen=int(MODEL_FRAMES), padding='pre', truncating='post', dtype='float32')
    
    X = np.array(sequences)
    y = to_categorical(labels).astype(int)
    
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.1, stratify=y, random_state=42)
    
    model = get_model(int(MODEL_FRAMES), len(word_ids))
    
    callbacks = []
    if epoch_callback:
        callbacks.append(TrainingCallback(epoch_callback))

    history = model.fit(X_train, y_train, validation_data=(X_val, y_val), 
                        epochs=epochs, batch_size=16, callbacks=callbacks, verbose=0)
    
    model.save(MODEL_PATH)
    
    return history.history

# --- Lógica de Visualización ---

def plot_training_history(history):
    """
    Genera y guarda una imagen con las gráficas de precisión y pérdida.
    Retorna la ruta del archivo de imagen guardado.
    """
    acc = history['accuracy']
    val_acc = history['val_accuracy']
    loss = history['loss']
    val_loss = history['val_loss']
    epochs_range = range(len(acc))

    plt.figure(figsize=(15, 5), dpi=100)  # Mayor DPI para mejor calidad
    plt.subplot(1, 2, 1)
    plt.plot(epochs_range, acc, label='Precisión de Entrenamiento', linewidth=2)
    plt.plot(epochs_range, val_acc, label='Precisión de Validación', linewidth=2)
    plt.legend(loc='lower right')
    plt.title('Precisión de Entrenamiento y Validación', fontsize=14, fontweight='bold')
    plt.xlabel('Época', fontsize=12)
    plt.ylabel('Precisión', fontsize=12)
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.plot(epochs_range, loss, label='Pérdida de Entrenamiento', linewidth=2)
    plt.plot(epochs_range, val_loss, label='Pérdida de Validación', linewidth=2)
    plt.legend(loc='upper right')
    plt.title('Pérdida de Entrenamiento y Validación', fontsize=14, fontweight='bold')
    plt.xlabel('Época', fontsize=12)
    plt.ylabel('Pérdida', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_path = os.path.join(MODEL_FOLDER_PATH, "training_history.png")
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')  # Mayor DPI y ajuste automático
    plt.close()
    return plot_path

def generate_confusion_matrix_logic():
    """
    Carga el modelo entrenado, genera la matriz de confusión y la guarda como imagen.
    Retorna la ruta del archivo de imagen guardado.
    """
    model = tf.keras.models.load_model(MODEL_PATH)
    word_ids = get_gestures_with_valid_keypoints()  # Usar solo gestos con keypoints válidos
    sequences, labels = get_sequences_and_labels(word_ids)
    
    sequences = pad_sequences(sequences, maxlen=int(MODEL_FRAMES), padding='pre', truncating='post', dtype='float32')
    
    y_true = np.array(labels)
    y_pred_probs = model.predict(sequences)
    y_pred = np.argmax(y_pred_probs, axis=1)
    
    # Solución: Especificar el rango completo de etiquetas posibles
    possible_labels = np.arange(len(word_ids))
    cm = confusion_matrix(y_true, y_pred, labels=possible_labels)
    
    # Crear figura con mejor resolución
    fig, ax = plt.subplots(figsize=(12, 10), dpi=100)
    
    # Usar imshow para mejor control visual
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    
    # Configurar etiquetas
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           xticklabels=word_ids,
           yticklabels=word_ids,
           title='Matriz de Confusión',
           ylabel='Etiqueta Real',
           xlabel='Etiqueta Predicha')
    
    # Rotar etiquetas del eje X para mejor legibilidad
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Añadir valores numéricos en las celdas
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",
                    fontsize=10, fontweight='bold')
    
    # Añadir barra de color
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Número de Predicciones', rotation=270, labelpad=20)
    
    plt.tight_layout()
    
    matrix_path = os.path.join(MODEL_FOLDER_PATH, "confusion_matrix.png")
    plt.savefig(matrix_path, dpi=150, bbox_inches='tight')
    plt.close()
    return matrix_path

# La lógica de captura se manejará directamente en la ventana de captura para
# poder retornar los frames en tiempo real, por lo que no se incluye aquí una función central.

# NOTA: Se asume que pandas está instalado, añadir a requirements si es necesario.
# (Lo más probable es que ya esté por otra dependencia) 