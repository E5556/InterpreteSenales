import os
import pandas as pd
from mediapipe.python.solutions.holistic import Holistic
from helpers import *
from constants import *

import sys
import tables

print(f"Python executable: {sys.executable}")
print(f"PyTables version: {tables.__version__}")

def create_keypoints(word_id, words_path, hdf_path):
    '''
    ### CREAR KEYPOINTS PARA UNA PALABRA
    Recorre la carpeta de frames de la palabra y guarda sus keypoints en `hdf_path`
    '''
    data = pd.DataFrame([])
    frames_path = os.path.join(words_path, word_id)
    
    with Holistic() as holistic:
        print(f'Creando keypoints de "{word_id}"...')
        sample_list = os.listdir(frames_path)
        sample_count = len(sample_list)
        
        for n_sample, sample_name in enumerate(sample_list, start=1):
            sample_path = os.path.join(frames_path, sample_name)
            keypoints_sequence = get_keypoints(holistic, sample_path)
            data = insert_keypoints_sequence(data, n_sample, keypoints_sequence)
            print(f"{n_sample}/{sample_count}", end="\r")

    # Asegúrate de que todas las columnas tengan tipos de datos consistentes y compatibles
    data = data.apply(pd.to_numeric, errors='ignore')

    # Guardar los keypoints en un archivo HDF5
    data.to_hdf(hdf_path, key="data", mode="w")
    print(f"Keypoints creados! ({sample_count} muestras)", end="\n")


if __name__ == "__main__":
    # Crea la carpeta `keypoints` en caso no exista
    create_folder(KEYPOINTS_PATH)
    
    # GENERAR TODAS LAS PALABRAS
    word_ids = [word for word in os.listdir(os.path.join(ROOT_PATH, FRAME_ACTIONS_PATH))]
    
    # GENERAR PARA UNA PALABRA O CONJUNTO
    word_ids = ["buenos_dias" , "hola", "bienvenido", "abrazar","buenas_noches", "Buenas_tardes", "como_esta", "con_mucho_gusto","adulto", "felicitacion", "perdon", "adios"]
    # word_ids = ["buenos_dias", "como_estas", "disculpa", "gracias", "hola-der", "hola-izq", "mal", "mas_o_menos", "me_ayudas", "por_favor"]
    
    for word_id in word_ids:
        hdf_path = os.path.join(KEYPOINTS_PATH, f"{word_id}.h5")
        create_keypoints(word_id, FRAME_ACTIONS_PATH, hdf_path)