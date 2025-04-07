# -*- coding: utf-8 -*-

"""
Module de Contrôle des Moteurs
----------------------------
Gère les moteurs du PiCarX en fournissant une interface
de haut niveau pour le contrôle du mouvement.
"""

import time
import logging
from picarx import Picarx

class MotorController:
    """
    Contrôleur des moteurs du PiCarX.
    Gère les mouvements de base et les ajustements fins.
    """

    def __init__(self):
        """
        Initialise le contrôleur de moteurs.
        Configure les paramètres de base et les limites de sécurité.
        """
        self.logger = logging.getLogger('PiCarX.MotorController')
        
        try:
            self.px = Picarx()
            # Arrêt initial des deux moteurs
            self.px.set_motor_speed(1, 0)  # Moteur gauche
            self.px.set_motor_speed(2, 0)  # Moteur droit
            
            # Paramètres de contrôle
            self.max_speed = 50  # Vitesse maximale (0-100)
            self.min_speed = 10  # Vitesse minimale
            self.max_steering = 30  # Angle maximum de braquage
            
            # État actuel
            self.current_speed = 0
            self.current_steering = 0
            
            self.logger.info("Contrôleur moteur initialisé avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur d'initialisation: {str(e)}")
            raise

    def set_speed(self, speed):
        """
        Définit la vitesse du robot.

        Args:
            speed (float): Vitesse désirée (-100 à 100)
                         Négatif pour marche arrière
        """
        try:
            # Limitation de la vitesse
            speed = max(min(speed, self.max_speed), -self.max_speed)
            
            # Application de la vitesse aux deux moteurs
            if speed >= 0:
                # Marche avant
                self.px.set_motor_speed(1, speed)    # Moteur gauche
                self.px.set_motor_speed(2, -speed)   # Moteur droit (inversé)
            else:
                # Marche arrière
                self.px.set_motor_speed(1, speed)    # Moteur gauche
                self.px.set_motor_speed(2, -speed)   # Moteur droit (inversé)
            
            self.current_speed = speed
            
        except Exception as e:
            self.logger.error(f"Erreur lors du réglage de la vitesse: {str(e)}")

    def set_steering(self, angle):
        """
        Définit l'angle de braquage.

        Args:
            angle (float): Angle de braquage (-30 à 30 degrés)
                         Négatif pour tourner à gauche
        """
        try:
            # Limitation de l'angle
            angle = max(min(angle, self.max_steering), -self.max_steering)
            
            # Application de l'angle
            self.px.set_dir_servo_angle(angle)
            self.current_steering = angle
            
            # Ajustement des vitesses des moteurs pour le virage
            if self.current_speed != 0:
                power_scale = (100 - abs(angle)) / 100.0
                if angle > 0:  # Virage à droite
                    self.px.set_motor_speed(1, self.current_speed)
                    self.px.set_motor_speed(2, -self.current_speed * power_scale)
                else:  # Virage à gauche
                    self.px.set_motor_speed(1, self.current_speed * power_scale)
                    self.px.set_motor_speed(2, -self.current_speed)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du braquage: {str(e)}")

    def stop(self):
        """Arrête le robot en douceur."""
        try:
            # Décélération progressive
            while abs(self.current_speed) > 5:
                new_speed = self.current_speed * 0.8
                self.set_speed(new_speed)
                time.sleep(0.1)
            
            # Arrêt complet
            self.px.stop()
            self.set_steering(0)
            self.current_speed = 0
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt: {str(e)}")
            # Arrêt d'urgence
            self.emergency_stop()

    def emergency_stop(self):
        """Arrêt d'urgence immédiat."""
        try:
            self.px.stop()
            self.current_speed = 0
            self.current_steering = 0
            self.logger.warning("Arrêt d'urgence effectué")
        except Exception as e:
            self.logger.error(f"Échec de l'arrêt d'urgence: {str(e)}")

    def avoid_obstacles(self):
        """Évitement d'obstacles optimisé"""
        distance = self.px.get_distance()
        if distance >= SafeDistance:
            self.px.set_dir_servo_angle(0)
            self.px.forward(AVOID_OBSTACLES_SPEED)
        elif distance >= DangerDistance:
            self.px.set_dir_servo_angle(30)
            self.px.forward(AVOID_OBSTACLES_SPEED)
            time.sleep(0.1)
        else:
            self.px.set_dir_servo_angle(-30)
            self.px.backward(AVOID_OBSTACLES_SPEED)
            time.sleep(0.5)

    def outHandle(self):
        """Gestion des sorties de ligne"""
        global last_line_state
        if last_line_state == 'left':
            self.px.set_dir_servo_angle(-30)
            self.px.backward(10)
        elif last_line_state == 'right':
            self.px.set_dir_servo_angle(30)
            self.px.backward(10)
        while True:
            gm_val_list = self.px.get_grayscale_data()
            gm_state = get_status(gm_val_list)
            if gm_state != last_line_state:
                break
        time.sleep(0.001)
