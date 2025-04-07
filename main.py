#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PiCarX - Programme Principal de Contrôle
--------------------------------------
Auteur: OUSMANE SANO
Date: 02/04/2025

Ce programme est le point d'entrée principal du système de contrôle du PiCarX.
Il orchestre les différents modules pour :
- Le suivi de ligne
- La détection de panneaux
- Le contrôle des moteurs
- La gestion des commandes externes
"""

import multiprocessing as mp
import logging
from datetime import datetime
import cv2
import numpy as np
import time
import readchar
from time import localtime, sleep, strftime
from vilib import Vilib
import os
from picarx import Picarx

# Importation des modules personnalisés
from src.vision.camera import CameraModule
from src.vision.line_detector import LineDetector
from src.vision.sign_detector import SignDetector
from src.control.motor_control import MotorController
from src.control.navigator import Navigator
from src.utils.config import Configuration
from src.control.robot_controller import RobotController

# Constantes optimisées
LINE_TRACK_SPEED = 10
LINE_TRACK_ANGLE_OFFSET = 20
AVOID_OBSTACLES_SPEED = 40
SafeDistance = 40   # > 40 safe
DangerDistance = 20 # > 20 && < 40 turn around, < 20 backward

def get_status(px, val_list):
    """Détection de ligne optimisée"""
    _state = px.get_line_status(val_list)
    if _state == [0, 0, 0]:
        return 'stop'
    elif _state[1] == 1:
        return 'forward'
    elif _state[0] == 1:
        return 'right'
    elif _state[2] == 1:
        return 'left'

def outHandle(px, last_line_state):
    """Gestion des sorties de ligne"""
    if last_line_state == 'left':
        px.set_dir_servo_angle(-30)
        px.backward(10)
    elif last_line_state == 'right':
        px.set_dir_servo_angle(30)
        px.backward(10)
    while True:
        gm_val_list = px.get_grayscale_data()
        gm_state = get_status(px, gm_val_list)
        if gm_state != last_line_state:
            break
    sleep(0.001)

def avoid_obstacles(px):
    """Éviter les obstacles"""
    try:
        distance = round(px.ultrasonic.read(), 2)
        print(f"Distance: {distance} cm")
        
        # Vérifier si la distance est valide
        if distance < 0 or distance > 1000:  # Valeurs invalides
            print("Erreur de lecture du capteur ultrasonique")
            return SafeDistance + 1  # Continuer comme si c'était sûr
        
        if distance >= SafeDistance:
            px.set_dir_servo_angle(0)
            px.forward(AVOID_OBSTACLES_SPEED)
        elif distance >= DangerDistance:
            px.set_dir_servo_angle(30)
            px.forward(AVOID_OBSTACLES_SPEED)
            sleep(0.1)
        else:
            px.set_dir_servo_angle(-30)
            px.backward(AVOID_OBSTACLES_SPEED)
            sleep(0.5)
        return distance
    except Exception as e:
        print(f"Erreur lors de la lecture du capteur: {e}")
        return SafeDistance + 1  # Continuer comme si c'était sûr

def line_track(px, last_line_state):
    """Suivi de ligne optimisé"""
    # Vérifier d'abord les obstacles
    distance = avoid_obstacles(px)
    if distance < SafeDistance:
        return last_line_state

    # Suivi de ligne
    gm_val_list = px.get_grayscale_data()
    gm_state = get_status(px, gm_val_list)

    if gm_state != "stop":
        last_line_state = gm_state
        if gm_state == 'forward':
            px.set_dir_servo_angle(0)
            px.forward(LINE_TRACK_SPEED)
        elif gm_state == 'left':
            px.set_dir_servo_angle(LINE_TRACK_ANGLE_OFFSET)
            px.forward(LINE_TRACK_SPEED)
        elif gm_state == 'right':
            px.set_dir_servo_angle(-LINE_TRACK_ANGLE_OFFSET)
            px.forward(LINE_TRACK_SPEED)
    else:
        outHandle(px, last_line_state)
    
    return last_line_state

class PiCarXController:
    """
    Classe principale du contrôleur PiCarX.
    Gère l'ensemble du système et coordonne les différents modules.
    """

    def __init__(self):
        """
        Initialise le contrôleur avec tous ses composants.
        Configure le logging et établit les connexions entre les modules.
        """
        # Configuration du système de logging
        self._setup_logging()
        self.logger.info("Initialisation du contrôleur PiCarX")
        
        # Initialisation des composants principaux
        try:
            self.config = Configuration()
            self.camera = CameraModule()
            self.line_detector = LineDetector()
            self.sign_detector = SignDetector()
            self.motor_controller = MotorController()
            self.navigator = Navigator(self.motor_controller)
            self.px = Picarx(ultrasonic_pins=['D2','D3'])  # trig, echo
            self.last_line_state = 'forward'  # État initial
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {str(e)}")
            raise

        # Configuration du multiprocessing
        self.vision_queue = mp.Queue()  # File pour les données de vision
        self.command_queue = mp.Queue()  # File pour les commandes externes
        self.running = mp.Value('b', True)  # Drapeau d'état du système

    def _setup_logging(self):
        """
        Configure le système de logging avec deux handlers :
        - Un pour les fichiers (conservation de l'historique)
        - Un pour la console (monitoring en temps réel)
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(
                    f'picarx_{datetime.now():%Y%m%d_%H%M%S}.log'
                ),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PiCarX')

    def vision_process(self):
        """
        Processus dédié à la vision.
        Gère l'acquisition et le traitement des images en continu.
        Détecte les lignes et les panneaux, puis envoie les informations
        au processus de navigation.
        """
        self.logger.info("Démarrage du processus de vision")
        
        while self.running.value:
            try:
                # Acquisition de l'image
                frame = self.camera.get_frame()
                if frame is None:
                    continue
                
                # Analyse de l'image
                line_info = self.line_detector.detect(frame)
                signs = self.sign_detector.detect(frame)
                
                # Envoi des résultats
                self.vision_queue.put({
                    'line_info': line_info,
                    'signs': signs,
                    'timestamp': datetime.now()
                })
            except Exception as e:
                self.logger.error(f"Erreur dans le processus vision: {str(e)}")

    def navigation_process(self):
        """
        Processus dédié à la navigation.
        Utilise les informations de vision pour piloter le robot.
        Gère également les commandes externes reçues.
        """
        self.logger.info("Démarrage du processus de navigation")
        
        while self.running.value:
            try:
                # Traitement des données de vision
                try:
                    vision_data = self.vision_queue.get(timeout=0.1)
                    if vision_data is not None:
                        self.navigator.update_from_vision(vision_data)
                except Exception as e:
                    self.logger.debug(f"Pas de nouvelles données de vision: {str(e)}")
                
                # Traitement des commandes externes
                try:
                    command = self.command_queue.get_nowait()
                    if command is not None:
                        self.navigator.handle_command(command)
                except:
                    pass  # Pas de nouvelle commande
                
                # Mise à jour de la navigation
                self.navigator.update()
                
            except Exception as e:
                self.logger.error(f"Erreur dans le processus navigation: {str(e)}")
                time.sleep(0.1)  # Petit délai pour éviter la surcharge

    def run(self):
        """
        Point d'entrée principal du système.
        Lance les processus de vision et de navigation.
        Gère l'arrêt propre du système.
        """
        try:
            # Création et démarrage des processus
            processes = [
                mp.Process(target=self.vision_process),
                mp.Process(target=self.navigation_process)
            ]
            
            for process in processes:
                process.start()
                
            # Attente de la fin des processus
            for process in processes:
                process.join()
                
        except KeyboardInterrupt:
            self.logger.info("Arrêt demandé par l'utilisateur")
            self.running.value = False
            
        finally:
            self.cleanup()

    def cleanup(self):
        """
        Nettoie les ressources du système.
        Arrête les moteurs et libère la caméra.
        """
        self.logger.info("Nettoyage des ressources")
        try:
            self.camera.release()
            self.motor_controller.stop()
            self.px.stop()
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage: {str(e)}")

def main():
    # Initialisation de la caméra et du robot
    Vilib.camera_start(vflip=False, hflip=False)
    Vilib.display(local=True, web=True)
    
    # Initialisation du robot avec les pins du capteur ultrasonique
    px = Picarx(ultrasonic_pins=['D2','D3'])  # trig, echo
    
    print("""
    Commandes:
    q: Prendre une photo
    1: Détecter rouge
    2: Détecter orange
    3: Détecter jaune
    4: Détecter vert
    5: Détecter bleu
    6: Détecter violet
    0: Désactiver détection
    f: Activer/Désactiver détection de visages
    s: Afficher informations détectées
    l: Démarrer/Arrêter le suivi de ligne
    x: Quitter
    """)

    colors = ['close', 'red', 'orange', 'yellow', 'green', 'blue', 'purple']
    face_active = False
    color_active = False
    line_following_active = False
    last_line_state = 'forward'  # État initial

    try:
        while True:
            key = readchar.readkey().lower()

            if key == 'x':
                break

            elif key == 'q':
                # Prendre une photo
                timestamp = strftime('%Y-%m-%d-%H-%M-%S', localtime(time()))
                name = f'photo_{timestamp}'
                username = os.getlogin()
                path = f"/home/{username}/Pictures/"
                Vilib.take_photo(name, path)
                print(f'Photo sauvegardée: {path}{name}.jpg')

            elif key in '0123456':
                # Détection de couleur
                index = int(key)
                color_active = (index != 0)
                Vilib.color_detect(colors[index])
                print(f'Détection couleur: {colors[index]}')

            elif key == 'f':
                # Détection de visages
                face_active = not face_active
                Vilib.face_detect_switch(face_active)
                print(f'Détection visages: {"activée" if face_active else "désactivée"}')

            elif key == 'l':
                # Activer/Désactiver le suivi de ligne
                line_following_active = not line_following_active
                if line_following_active:
                    print("Suivi de ligne activé")
                else:
                    px.stop()
                    print("Suivi de ligne désactivé")

            elif key == 's':
                # Afficher les informations détectées
                if color_active:
                    if Vilib.detect_obj_parameter['color_n'] > 0:
                        pos = (Vilib.detect_obj_parameter['color_x'],
                              Vilib.detect_obj_parameter['color_y'])
                        size = (Vilib.detect_obj_parameter['color_w'],
                               Vilib.detect_obj_parameter['color_h'])
                        print(f"Couleur détectée - Position: {pos}, Taille: {size}")
                    else:
                        print("Aucune couleur détectée")

                if face_active:
                    if Vilib.detect_obj_parameter['human_n'] > 0:
                        pos = (Vilib.detect_obj_parameter['human_x'],
                              Vilib.detect_obj_parameter['human_y'])
                        size = (Vilib.detect_obj_parameter['human_w'],
                               Vilib.detect_obj_parameter['human_h'])
                        print(f"Visage détecté - Position: {pos}, Taille: {size}")
                    else:
                        print("Aucun visage détecté")

            # Exécuter le suivi de ligne si actif
            if line_following_active:
                last_line_state = line_track(px, last_line_state)

            sleep(0.1)

    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
    finally:
        px.stop()
        Vilib.camera_close()
        print("Programme terminé")

if __name__ == "__main__":
    main()