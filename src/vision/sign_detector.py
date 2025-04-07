"""
Module de détection des panneaux de signalisation
"""

import logging
import cv2
import numpy as np

class SignDetector:
    def __init__(self):
        """Initialise le détecteur de panneaux"""
        self.logger = logging.getLogger('PiCarX.SignDetector')
        self.colors = {
            'red': ([0, 100, 100], [10, 255, 255]),
            'blue': ([100, 100, 100], [130, 255, 255]),
            'yellow': ([20, 100, 100], [30, 255, 255])
        }

    def detect(self, frame):
        """
        Détecte les panneaux dans l'image
        
        Args:
            frame: Image à analyser
            
        Returns:
            list: Liste des panneaux détectés
        """
        try:
            # Conversion en HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            detected_signs = []
            for color_name, (lower, upper) in self.colors.items():
                # Création du masque
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                
                # Détection des contours
                contours, _ = cv2.findContours(
                    mask,
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )
                
                # Filtrage des contours
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > 100:  # Seuil minimal
                        x, y, w, h = cv2.boundingRect(contour)
                        detected_signs.append({
                            'color': color_name,
                            'position': (x + w//2, y + h//2),
                            'size': (w, h),
                            'confidence': area / (frame.shape[0] * frame.shape[1])
                        })
            
            return detected_signs
            
        except Exception as e:
            self.logger.error(f"Erreur détection panneaux: {str(e)}")
            return [] 