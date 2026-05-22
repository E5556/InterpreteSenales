#!/usr/bin/env python3
"""
Conversation Manager - Sistema de Conversación Continua
Permite detectar múltiples señas y construir frases fluidas
"""

import time
import numpy as np
from collections import deque
from typing import List, Optional, Tuple

class ConversationManager:
    def __init__(self, 
                 max_phrase_length: int = 10,
                 gesture_timeout: float = 2.0,
                 phrase_timeout: float = 5.0,
                 confidence_threshold: float = 0.7):
        """
        Inicializa el gestor de conversación
        
        Args:
            max_phrase_length: Máximo número de palabras en una frase
            gesture_timeout: Tiempo máximo entre gestos (segundos)
            phrase_timeout: Tiempo máximo para completar una frase (segundos)
            confidence_threshold: Umbral de confianza mínimo para aceptar gestos
        """
        self.max_phrase_length = max_phrase_length
        self.gesture_timeout = gesture_timeout
        self.phrase_timeout = phrase_timeout
        self.confidence_threshold = confidence_threshold
        
        # Estado de la conversación
        self.current_phrase = []  # Lista de palabras en la frase actual
        self.last_gesture_time = 0  # Timestamp del último gesto detectado
        self.phrase_start_time = 0  # Timestamp de inicio de la frase actual
        self.is_recording_phrase = False  # Si estamos grabando una frase
        self.gesture_buffer = deque(maxlen=5)  # Buffer de gestos recientes
        
        # Configuración de detección
        self.min_gesture_interval = 0.3  # Mínimo tiempo entre gestos (segundos) - más rápido
        self.gesture_cooldown = 0.2  # Tiempo de cooldown después de detectar un gesto - más rápido
        
        # Estado de detección de manos
        self.hands_detected = False  # Si hay manos detectadas en la cámara
        self.last_hands_detection_time = 0  # Timestamp de la última detección de manos
        self.hands_timeout = 3.0  # Tiempo sin manos antes de completar frase
        
        # Estadísticas
        self.total_gestures_detected = 0
        self.total_phrases_completed = 0
        
    def add_gesture(self, gesture: str, confidence: float, timestamp: float = None) -> bool:
        """
        Añade un nuevo gesto a la conversación
        
        Args:
            gesture: Palabra/gesto detectado
            confidence: Nivel de confianza (0.0 - 1.0)
            timestamp: Timestamp del gesto (si None, usa tiempo actual)
            
        Returns:
            True si el gesto fue añadido, False si fue rechazado
        """
        if timestamp is None:
            timestamp = time.time()
            
        # Verificar umbral de confianza
        if confidence < self.confidence_threshold:
            return False
            
        # Verificar intervalo mínimo entre gestos
        if timestamp - self.last_gesture_time < self.min_gesture_interval:
            return False
            
        # Si no estamos grabando una frase, iniciar una nueva
        if not self.is_recording_phrase:
            self.start_new_phrase(timestamp)
            
        # Verificar timeout de gesto - solo si no hay frase en construcción
        if timestamp - self.last_gesture_time > self.gesture_timeout:
            # Solo completar frase anterior si existe y no estamos en medio de una frase
            if self.current_phrase and not self.is_recording_phrase:
                self.complete_phrase()
            # Iniciar nueva frase solo si no hay una en construcción
            if not self.is_recording_phrase:
                self.start_new_phrase(timestamp)
            
        # Añadir gesto a la frase actual
        self.current_phrase.append(gesture)
        self.last_gesture_time = timestamp
        self.total_gestures_detected += 1
        
        # Añadir al buffer de gestos recientes
        self.gesture_buffer.append({
            'gesture': gesture,
            'confidence': confidence,
            'timestamp': timestamp
        })
        
        # NO completar la frase inmediatamente - solo verificar límite máximo
        if len(self.current_phrase) >= self.max_phrase_length:
            self.complete_phrase()
            
        return True
    
    def update_hands_detection(self, hands_detected: bool, timestamp: float = None):
        """
        Actualiza el estado de detección de manos
        
        Args:
            hands_detected: True si hay manos detectadas, False si no
            timestamp: Timestamp de la detección (si None, usa tiempo actual)
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Solo actualizar si hay un cambio real en el estado
        if self.hands_detected != hands_detected:
            self.hands_detected = hands_detected
            self.last_hands_detection_time = timestamp
            
            # Si se detectan manos y estamos en una frase, reiniciar el conteo
            if hands_detected and self.is_recording_phrase:
                print(f"🔄 Manos detectadas - reiniciando conteo de timeout")
            elif not hands_detected and self.is_recording_phrase:
                print(f"✋ Sin manos detectadas - iniciando conteo de timeout")
        
    def should_complete_phrase(self) -> bool:
        """
        Determina si la frase debe completarse basándose en la detección de manos
        
        Returns:
            True si la frase debe completarse, False en caso contrario
        """
        current_time = time.time()
        
        # Solo completar si:
        # 1. Estamos grabando una frase
        # 2. No hay manos detectadas
        # 3. Ha pasado suficiente tiempo sin manos
        # 4. La frase tiene al menos una palabra
        if (self.is_recording_phrase and 
            not self.hands_detected and
            current_time - self.last_hands_detection_time > self.hands_timeout and
            len(self.current_phrase) >= 1):
            return True
            
        return False
        
    def start_new_phrase(self, timestamp: float = None):
        """Inicia una nueva frase"""
        if timestamp is None:
            timestamp = time.time()
            
        self.current_phrase = []
        self.phrase_start_time = timestamp
        self.is_recording_phrase = True
        
    def complete_phrase(self) -> Optional[str]:
        """
        Completa la frase actual y la retorna
        
        Returns:
            Frase completada como string, o None si no hay frase
        """
        if not self.current_phrase:
            return None
            
        # Crear frase final
        phrase = " ".join(self.current_phrase)
        
        # Estadísticas
        self.total_phrases_completed += 1
        
        # Limpiar estado
        self.current_phrase = []
        self.is_recording_phrase = False
        
        return phrase
        
    def check_timeout(self) -> Optional[str]:
        """
        Verifica si hay timeout y completa la frase si es necesario
        
        Returns:
            Frase completada si hay timeout, None en caso contrario
        """
        # Usar la nueva lógica basada en detección de manos
        if self.should_complete_phrase():
            return self.complete_phrase()
            
        return None
        
    def get_current_phrase(self) -> str:
        """Retorna la frase actual en construcción"""
        return " ".join(self.current_phrase) if self.current_phrase else ""
        
    def get_status(self) -> dict:
        """Retorna el estado actual del gestor de conversación"""
        current_time = time.time()
        
        return {
            'is_recording': self.is_recording_phrase,
            'current_phrase': self.get_current_phrase(),
            'phrase_length': len(self.current_phrase),
            'time_since_last_gesture': current_time - self.last_gesture_time if self.last_gesture_time > 0 else 0,
            'phrase_duration': current_time - self.phrase_start_time if self.is_recording_phrase else 0,
            'total_gestures': self.total_gestures_detected,
            'total_phrases': self.total_phrases_completed,
            'recent_gestures': list(self.gesture_buffer)
        }
        
    def reset(self):
        """Reinicia el estado del gestor de conversación"""
        self.current_phrase = []
        self.last_gesture_time = 0
        self.phrase_start_time = 0
        self.is_recording_phrase = False
        self.gesture_buffer.clear()
        self.hands_detected = False
        self.last_hands_detection_time = 0
        
    def set_confidence_threshold(self, threshold: float):
        """Ajusta el umbral de confianza"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        
    def set_gesture_timeout(self, timeout: float):
        """Ajusta el timeout entre gestos"""
        self.gesture_timeout = max(0.1, timeout)
        
    def set_phrase_timeout(self, timeout: float):
        """Ajusta el timeout para completar frases"""
        self.phrase_timeout = max(1.0, timeout)
        
    def set_hands_timeout(self, timeout: float):
        """Ajusta el timeout sin manos para completar frases"""
        self.hands_timeout = max(1.0, timeout)
        
    def force_complete_phrase(self) -> Optional[str]:
        """
        Fuerza la finalización de la frase actual, incluso si tiene una sola palabra
        
        Returns:
            Frase completada, o None si no hay frase
        """
        if self.current_phrase:
            return self.complete_phrase()
        return None
        
    def check_single_gesture_timeout(self) -> Optional[str]:
        """
        Verifica si hay timeout para gestos individuales (frases de una palabra)
        
        Returns:
            Frase completada si hay timeout, None en caso contrario
        """
        current_time = time.time()
        
        # Si tenemos una sola palabra y ha pasado mucho tiempo, completarla
        if (self.is_recording_phrase and 
            len(self.current_phrase) == 1 and
            current_time - self.last_gesture_time > self.phrase_timeout * 2):  # Doble timeout para gestos individuales
            return self.complete_phrase()
            
        return None

class ContinuousGestureDetector:
    """
    Detector de gestos continuo que trabaja con el ConversationManager
    """
    
    def __init__(self, conversation_manager: ConversationManager):
        self.conversation_manager = conversation_manager
        self.is_detecting = False
        self.last_detection_time = 0
        self.detection_cooldown = 0.5  # Cooldown entre detecciones
        
    def process_frame(self, keypoints_sequence, model, word_ids) -> Tuple[bool, str]:
        """
        Procesa un frame y detecta gestos
        
        Args:
            keypoints_sequence: Secuencia de keypoints
            model: Modelo de predicción
            word_ids: Lista de IDs de palabras
            
        Returns:
            Tuple (gesto_detectado, frase_completada)
        """
        current_time = time.time()
        
        # Verificar cooldown
        if current_time - self.last_detection_time < self.detection_cooldown:
            return False, None
            
        try:
            # Realizar predicción
            res = model.predict(np.expand_dims(keypoints_sequence, axis=0), verbose=0)[0]
            confidence = res[np.argmax(res)]
            
            if confidence > self.conversation_manager.confidence_threshold:
                word_id = word_ids[np.argmax(res)].split('-')[0]
                
                # Obtener texto de visualización
                from constants import get_display_text
                gesture_text = get_display_text(word_id)
                
                if gesture_text:
                    # Añadir gesto al gestor de conversación
                    gesture_added = self.conversation_manager.add_gesture(
                        gesture_text, 
                        confidence, 
                        current_time
                    )
                    
                    if gesture_added:
                        self.last_detection_time = current_time
                        
                        # Verificar si se completó una frase
                        completed_phrase = self.conversation_manager.check_timeout()
                        return True, completed_phrase
                        
        except Exception as e:
            print(f"Error en detección continua: {e}")
            
        return False, None
