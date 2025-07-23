import os
import cv2

# SETTINGS
MIN_LENGTH_FRAMES = 5
LENGTH_KEYPOINTS = 1662
MODEL_FRAMES = 15

# PATHS
ROOT_PATH = os.getcwd()
FRAME_ACTIONS_PATH = os.path.join(ROOT_PATH, "frame_actions")
DATA_PATH = os.path.join(ROOT_PATH, "data")
DATA_JSON_PATH = os.path.join(DATA_PATH, "data.json")
MODEL_FOLDER_PATH = os.path.join(ROOT_PATH, "models")
MODEL_PATH = os.path.join(MODEL_FOLDER_PATH, f"actions_{MODEL_FRAMES}.keras")
KEYPOINTS_PATH = os.path.join(DATA_PATH, "keypoints")
WORDS_JSON_PATH = os.path.join(MODEL_FOLDER_PATH, "words.json")

# SHOW IMAGE PARAMETERS
FONT = cv2.FONT_HERSHEY_PLAIN
FONT_SIZE = 1.5
FONT_POS = (5, 30)

words_text = {
    "bienvenido": "BIENVENIDO",
    "hola": "HOLA",
    "buenos_dias": "BUENOS DIAS",
    "buenas_tardes": "BUENAS TARDES",
    "buenas_noches": "BUENAS NOCHES",
    "abrazar": "ABRAZAR",
    "como_esta": "COMO ESTÁ?",
    "con_mucho_gusto": "CON MUCHO GUSTO",
    "adulto": "ADULTO",
    "adios": "ADIOS",
    "felicitaciones": "FELICITACIONES",
    "perdon": "PERDON",
}