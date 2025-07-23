import numpy as np
import os
import sys
import tensorflow as tf

from model import get_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical
from helpers import get_word_ids, get_sequences_and_labels
from constants import *

def training_model(model_path, epochs=500):
    try:
        print("Cargando IDs de palabras...")
        word_ids = get_word_ids(WORDS_JSON_PATH)
        print(f"IDs de palabras cargados: {word_ids}")

        print("Obteniendo secuencias y etiquetas...")
        sequences, labels = get_sequences_and_labels(word_ids)
        print(f"Secuencias y etiquetas obtenidas. Número de secuencias: {len(sequences)}")

        print("Rellenando secuencias...")
        sequences = pad_sequences(sequences, maxlen=int(MODEL_FRAMES), padding='pre', truncating='post', dtype='float16')
        print("Secuencias rellenadas.")

        X = np.array(sequences)
        y = to_categorical(labels).astype(int)
        print(f"Datos preparados. Forma de X: {X.shape}, forma de y: {y.shape}")

        early_stopping = EarlyStopping(monitor='accuracy', patience=10, restore_best_weights=True)
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.05, random_state=42)
        print("Datos divididos en conjuntos de entrenamiento y validación.")

        print("Obteniendo modelo...")
        model = get_model(int(MODEL_FRAMES), len(word_ids))
        print("Modelo obtenido. Iniciando entrenamiento...")

        model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=epochs, batch_size=8, callbacks=[early_stopping])
        print("Entrenamiento del modelo completado.")

        model.summary()
        model.save(model_path)
        print(f"Modelo guardado en {model_path}")

    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    model_path = f'models\\actions_{MODEL_FRAMES}.keras'
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    print(f"Guardando modelo en {model_path}")
    training_model(model_path, epochs=500)