import logging
from ..vision.camera import CameraModule
from .motor_control import MotorController
import time

class RobotController:
    """
    Contrôleur principal du robot.
    Intègre la vision et le contrôle moteur.
    """
    def __init__(self):
        self.logger = logging.getLogger('PiCarX.Controller')
        self.camera = CameraModule()
        self.motor = MotorController()
        
        # Paramètres de suivi
        self.tracking_enabled = False
        self.target_color = None
        
    def start_color_tracking(self, color):
        """Active le suivi de couleur"""
        self.tracking_enabled = True
        self.target_color = color
        self.camera.start_color_detection(color)
        
    def stop_color_tracking(self):
        """Désactive le suivi de couleur"""
        self.tracking_enabled = False
        self.camera.stop_color_detection()
        self.motor.stop()
        
    def update(self):
        """Mise à jour principale du robot"""
        if not self.tracking_enabled:
            return
            
        # Obtenir les informations de détection
        info = self.camera.get_detection_info()
        
        if 'color' in info:
            color_info = info['color']
            if color_info['count'] > 0:
                # Calculer l'erreur de position
                x_pos = color_info['position'][0]
                width = color_info['size'][0]
                
                # Centre de l'image est à 320 (pour une image 640x480)
                error = (x_pos - 320) / 320  # Normalisation entre -1 et 1
                
                # Calculer l'angle de direction
                steering_angle = -30 * error  # -30 à +30 degrés
                
                # Ajuster la vitesse en fonction de la taille de l'objet
                # Plus l'objet est grand (proche), plus on ralentit
                speed = 30 * (1 - min(width/640, 0.8))
                
                # Appliquer les commandes
                self.motor.set_steering(steering_angle)
                self.motor.set_speed(speed)
            else:
                # Aucun objet détecté, tourner sur place pour chercher
                self.motor.set_steering(30)
                self.motor.set_speed(10)
        
    def cleanup(self):
        """Nettoie les ressources du robot"""
        self.camera.release()
        self.motor.stop()
