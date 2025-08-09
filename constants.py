import os
import cv2

# SETTINGS
MIN_LENGTH_FRAMES = 5
LENGTH_KEYPOINTS = 1662
MODEL_FRAMES = 15

# DATABASE
DATABASE_NAME = "usuarios.db"

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