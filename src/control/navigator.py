# -*- coding: utf-8 -*-

"""
Module de Navigation
------------------
Gère la logique de navigation du robot en combinant
les informations de vision et les commandes de contrôle.
"""

import logging
import time
from enum import Enum

class NavigationState(Enum):
    """États possibles du système de navigation."""
    SUIVRE_LIGNE = "suivre_ligne"
    TRAITER_PANNEAU = "traiter_panneau"
    ATTENTE_COMMANDE = "attente_commande"
    ARRET = "arret"

class Navigator:
    """
    Gestionnaire de navigation du PiCarX.
    Coordonne le suivi de ligne et la réaction aux panneaux.
    """

    def __init__(self, motor_controller):
        """
        Initialise le navigateur.

        Args:
            motor_controller (MotorController): Contrôleur des moteurs
        """
        self.logger = logging.getLogger('PiCarX.Navigator')
        self.motor_controller = motor_controller
        
        # Paramètres de navigation
        self.base_speed = 30
        self.min_speed = 15
        self.max_steering = 30
        
        # État actuel
        self.state = NavigationState.SUIVRE_LIGNE
        self.last_line_pos = None
        self.panneau_en_cours = None
        
        self.logger.info("Navigateur initialisé")

    def update_from_vision(self, vision_data):
        """
        Met à jour la navigation selon les données de vision.

        Args:
            vision_data (dict): Données de vision (ligne et panneaux)
        """
        try:
            if not vision_data:
                return

            line_info = vision_data.get('line_info', {})
            signs = vision_data.get('signs', [])
            
            # Traitement des panneaux prioritaires
            if signs and self.state != NavigationState.TRAITER_PANNEAU:
                self.handle_sign(signs[0])
            
            # Suivi de ligne si pas d'autre action en cours
            elif self.state == NavigationState.SUIVRE_LIGNE:
                self.follow_line(line_info)
                
        except Exception as e:
            self.logger.error(f"Erreur de mise à jour navigation: {str(e)}")

    def follow_line(self, line_info):
        """
        Implémente la logique de suivi de ligne.

        Args:
            line_info (dict): Informations sur la ligne détectée
        """
        try:
            if not line_info.get('detected'):
                if self.last_line_pos:
                    # Continuer dans la dernière direction connue
                    self.motor_controller.set_speed(self.min_speed)
                else:
                    # Arrêt si pas de référence
                    self.motor_controller.stop()
                return

            # Calcul de l'erreur de position
            position = line_info['position']
            center_x = position[0]
            frame_width = 640  # Largeur supposée de l'image
            
            # Calcul de l'angle de correction
            error = (center_x - frame_width/2) / (frame_width/2)
            steering_angle = -error * self.max_steering
            
            # Application des commandes
            self.motor_controller.set_steering(steering_angle)
            
            # Ajustement de la vitesse selon l'angle
            speed = self.base_speed * (1 - abs(error))
            speed = max(speed, self.min_speed)
            self.motor_controller.set_speed(speed)
            
            self.last_line_pos = position
            
        except Exception as e:
            self.logger.error(f"Erreur suivi de ligne: {str(e)}")
            self.motor_controller.stop()

    def handle_sign(self, sign_info):
        """
        Gère la réaction à un panneau détecté.

        Args:
            sign_info (dict): Informations sur le panneau détecté
        """
        try:
            self.state = NavigationState.TRAITER_PANNEAU
            sign_class = sign_info['class']
            
            if sign_class == 'STOP':
                self.handle_stop_sign()
            elif sign_class == 'GAUCHE':
                self.handle_turn_sign(-90)
            elif sign_class == 'DROITE':
                self.handle_turn_sign(90)
                
        except Exception as e:
            self.logger.error(f"Erreur traitement panneau: {str(e)}")
            self.state = NavigationState.SUIVRE_LIGNE

    def handle_stop_sign(self):
        """Gère l'arrêt au panneau STOP."""
        try:
            self.motor_controller.stop()
            time.sleep(2)  # Attente réglementaire
            self.state = NavigationState.SUIVRE_LIGNE
        except Exception as e:
            self.logger.error(f"Erreur arrêt STOP: {str(e)}")

    def handle_turn_sign(self, angle):
        """
        Gère les virages aux panneaux directionnels.

        Args:
            angle (float): Angle de virage souhaité
        """
        try:
            # Ralentissement
            self.motor_controller.set_speed(self.min_speed)
            
            # Application du virage
            self.motor_controller.set_steering(angle)
            time.sleep(1)  # Durée du virage
            
            # Retour en mode normal
            self.motor_controller.set_steering(0)
            self.state = NavigationState.SUIVRE_LIGNE
        except Exception as e:
            self.logger.error(f"Erreur virage: {str(e)}")
            self.motor_controller.stop()

    def handle_command(self, command):
        """
        Traite les commandes externes.

        Args:
            command (dict): Commande à exécuter
        """
        try:
            if not command:
                return

            if command.get('type') == 'speed':
                self.motor_controller.set_speed(command['value'])
            elif command.get('type') == 'turn':
                self.motor_controller.set_steering(command['value'])
            elif command.get('type') == 'stop':
                self.motor_controller.stop()
                
        except Exception as e:
            self.logger.error(f"Erreur traitement commande: {str(e)}")

    def update(self):
        """Met à jour l'état de la navigation."""
        try:
            # Vérification de l'état des moteurs
            if self.state == NavigationState.ARRET:
                self.motor_controller.stop()
        except Exception as e:
            self.logger.error(f"Erreur mise à jour: {str(e)}")
