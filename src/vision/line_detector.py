# -*- coding: utf-8 -*-

"""
Module de Détection de Ligne
---------------------------
Ce module utilise OpenCV pour détecter et analyser
la ligne que le robot doit suivre.

Il fournit des informations sur :
- La position de la ligne
- L'angle de la ligne
- La qualité de la détection
"""

import cv2
import numpy as np
import logging

class LineDetector:
    """
    Classe gérant la détection de ligne au sol.
    Utilise des techniques de traitement d'image pour isoler
    et analyser la ligne à suivre.
    """

    def __init__(self, threshold=127):
        """
        Initialise le détecteur de ligne.

        Args:
            threshold (int): Seuil de binarisation (0-255)
                           Plus la valeur est haute, plus la détection
                           sera sensible aux lignes claires.
        """
        self.threshold = threshold
        self.logger = logging.getLogger('PiCarX.LineDetector')
        self.logger.info("Initialisation du détecteur de ligne")

    def preprocess_image(self, frame):
        """
        Prétraite l'image pour faciliter la détection.

        Args:
            frame (np.array): Image source en BGR

        Returns:
            np.array: Image binaire prétraitée
        """
        # Conversion en niveaux de gris
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Application d'un flou gaussien pour réduire le bruit
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Binarisation de l'image
        _, binary = cv2.threshold(
            blurred,
            self.threshold,
            255,
            cv2.THRESH_BINARY_INV
        )
        
        return binary

    def detect(self, frame):
        """
        Détecte la ligne dans l'image fournie.

        Args:
            frame (np.array): Image à analyser

        Returns:
            dict: Informations sur la ligne détectée
                - detected (bool): Présence d'une ligne
                - position (tuple): Position (x, y) du centre de la ligne
                - angle (float): Angle de la ligne en degrés
        """
        try:
            # Prétraitement optimisé
            binary = self.preprocess_image(frame)
            
            # ROI plus précise
            height, width = binary.shape
            roi_height = height // 3  # Réduit la zone d'analyse
            roi = binary[height-roi_height:, :]
            
            # Détection des contours avec paramètres optimisés
            contours, _ = cv2.findContours(
                roi,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            if not contours:
                return {'detected': False, 'position': None, 'angle': None}
            
            # Filtrage des contours par taille
            min_contour_area = 100  # Ajuster selon la résolution
            valid_contours = [c for c in contours if cv2.contourArea(c) > min_contour_area]
            
            if not valid_contours:
                return {'detected': False, 'position': None, 'angle': None}
            
            # Analyse du plus grand contour valide
            largest_contour = max(valid_contours, key=cv2.contourArea)
            M = cv2.moments(largest_contour)
            
            if M["m00"] == 0:
                return {'detected': False, 'position': None, 'angle': None}
            
            # Calcul optimisé du centre
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"]) + (height - roi_height)
            
            # Calcul de l'angle avec lissage
            vx, vy, x, y = cv2.fitLine(largest_contour, cv2.DIST_L2, 0, 0.01, 0.01)
            angle = np.arctan2(vy, vx) * 180 / np.pi
            
            return {
                'detected': True,
                'position': (cx, cy),
                'angle': angle,
                'confidence': cv2.contourArea(largest_contour) / (roi_height * width)
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la détection: {str(e)}")
            return {
                'detected': False,
                'position': None,
                'angle': None
            }