import os
import cv2

# SETTINGS
MIN_LENGTH_FRAMES = 5
LENGTH_KEYPOINTS = 1662
MODEL_FRAMES = 15  # Configurado para 15 frames para compatibilidad con el modelo actual

# CAMERA SETTINGS
CAMERA_INDEX = 0  # Cambia este número para seleccionar otra cámara (0=primera, 1=segunda, etc.)

# DATABASE
from config import get_database_path
def get_database_name():
    return get_database_path()
DATABASE_NAME = get_database_name()  # Mantener compatibilidad hacia atrás

# PATHS
ROOT_PATH = os.getcwd()
FRAME_ACTIONS_PATH = os.path.join(ROOT_PATH, "frame_actions")
DATA_PATH = os.path.join(ROOT_PATH, "data")
DATA_JSON_PATH = os.path.join(DATA_PATH, "data.json")
MODEL_FOLDER_PATH = os.path.join(ROOT_PATH, "models")
MODEL_PATH = os.path.join(MODEL_FOLDER_PATH, f"actions_{MODEL_FRAMES}.keras")
KEYPOINTS_PATH = os.path.join(DATA_PATH, "keypoints")
# WORDS_JSON_PATH eliminado - ahora se usa detección automática

# SHOW IMAGE PARAMETERS
FONT = cv2.FONT_HERSHEY_PLAIN
FONT_SIZE = 1.5
FONT_POS = (5, 30)

# Función para generar automáticamente el texto de display
def get_display_text(gesture_id):
    """Convierte ID de gesto a texto de display automáticamente"""
    return gesture_id.replace('_', ' ').upper()

# Diccionario obsoleto eliminado - ahora se usa get_display_text()