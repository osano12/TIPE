"""
Module de gestion de la caméra
"""

from vilib import Vilib
import cv2
import logging
import time
import os
import subprocess
import numpy as np
from time import strftime, localtime, time, sleep
import threading

class CameraModule:
    """
    Module de gestion de la caméra utilisant vilib.
    Fournit des fonctionnalités de vision avancées.
    """
    def __init__(self):
        """Initialise la caméra"""
        self.logger = logging.getLogger('PiCarX.Camera')
        self.temp_file = "/tmp/picarx_frame.jpg"
        self.face_detection_active = False
        self.color_detection_active = False
        self.qr_detection_active = False
        self.qr_thread = None
        self.streaming_process = None
        self.streaming_active = False
        self._check_camera()
        
        # Initialisation optimisée de la caméra
        Vilib.camera_start(vflip=False, hflip=False)
        Vilib.display(local=False, web=True)
        sleep(0.8)  # Attente optimisée pour l'initialisation

    def _check_camera(self):
        """Vérifie si la caméra est disponible"""
        try:
            # Vérification avec libcamera-still
            result = subprocess.run(
                ["libcamera-still", "--list-cameras"],
                capture_output=True,
                text=True
            )
            if "Available cameras" not in result.stdout:
                raise RuntimeError("Aucune caméra disponible")
            self.logger.info("Caméra trouvée")
        except Exception as e:
            self.logger.error(f"Erreur de vérification caméra: {str(e)}")
            raise

    def get_frame(self):
        """Capture une image avec libcamera"""
        try:
            # Capture d'une image avec libcamera-still
            result = subprocess.run([
                "libcamera-still",
                "-n",                    # Pas de prévisualisation
                "--immediate",           # Capture immédiate
                "-o", self.temp_file,    # Fichier de sortie
                "--width", "320",        # Largeur
                "--height", "240",       # Hauteur
                "--timeout", "1000",     # Timeout en ms
                "--nopreview"           # Pas de prévisualisation
            ], capture_output=True)
            
            if result.returncode != 0:
                self.logger.error(f"Erreur capture: {result.stderr.decode()}")
                return None
            
            # Lecture de l'image avec OpenCV
            frame = cv2.imread(self.temp_file)
            if frame is None:
                self.logger.warning("Échec de lecture de l'image")
                return None
                
            return frame
            
        except Exception as e:
            self.logger.error(f"Erreur capture image: {str(e)}")
            return None

    def release(self):
        """Libère les ressources de la caméra"""
        try:
            if os.path.exists(self.temp_file):
                os.remove(self.temp_file)
            self.stop_streaming()
            self.stop_face_detection()
            self.stop_color_detection()
            self.stop_qr_detection()
            Vilib.camera_close()
            self.logger.info("Ressources de la caméra libérées")
        except Exception as e:
            self.logger.error(f"Erreur lors de la libération de la caméra: {str(e)}")

    def start_face_detection(self):
        """Détection de visage optimisée"""
        Vilib.face_detect_switch(True)
        self.logger.info("Détection de visage activée")

    def stop_face_detection(self):
        """Désactive la détection de visages"""
        self.face_detection_active = False
        Vilib.face_detect_switch(False)
        self.logger.info("Détection de visages désactivée")

    def start_color_detection(self, color="red"):
        """Détection de couleur optimisée"""
        Vilib.color_detect(color)
        self.logger.info(f"Détection de couleur {color} activée")

    def stop_color_detection(self):
        """Désactive la détection de couleur"""
        self.color_detection_active = False
        Vilib.color_detect('close')
        self.logger.info("Détection de couleur désactivée")

    def start_qr_detection(self):
        """Active la détection de QR codes"""
        self.qr_detection_active = True
        
        def qr_detection_thread():
            Vilib.qrcode_detect_switch(True)
            last_text = None
            while self.qr_detection_active:
                text = Vilib.detect_obj_parameter['qr_data']
                if text != "None" and text != last_text:
                    last_text = text
                    self.logger.info(f'QR code détecté: {text}')
                sleep(0.5)
            Vilib.qrcode_detect_switch(False)

        self.qr_thread = threading.Thread(target=qr_detection_thread)
        self.qr_thread.daemon = True
        self.qr_thread.start()
        self.logger.info("Détection de QR codes activée")

    def stop_qr_detection(self):
        """Désactive la détection de QR codes"""
        self.qr_detection_active = False
        if self.qr_thread:
            self.qr_thread.join()
        self.logger.info("Détection de QR codes désactivée")

    def take_photo(self):
        """Capture de photo optimisée"""
        _time = strftime('%Y-%m-%d-%H-%M-%S',localtime(time()))
        name = f'photo_{_time}'
        path = f"{os.path.expanduser('~')}/Pictures/picar-x/"
        os.makedirs(path, exist_ok=True)
        Vilib.take_photo(name, path)
        self.logger.info(f'Photo sauvegardée: {path}{name}.jpg')
        return f'{path}{name}.jpg'

    def get_detection_info(self):
        """Retourne les informations de détection actuelles"""
        info = {}
        
        if self.color_detection_active:
            info['color'] = {
                'count': Vilib.detect_obj_parameter['color_n'],
                'position': (Vilib.detect_obj_parameter['color_x'],
                           Vilib.detect_obj_parameter['color_y']),
                'size': (Vilib.detect_obj_parameter['color_w'],
                        Vilib.detect_obj_parameter['color_h'])
            }
            
        if self.face_detection_active:
            info['face'] = {
                'count': Vilib.detect_obj_parameter['human_n'],
                'position': (Vilib.detect_obj_parameter['human_x'],
                           Vilib.detect_obj_parameter['human_y']),
                'size': (Vilib.detect_obj_parameter['human_w'],
                        Vilib.detect_obj_parameter['human_h'])
            }
            
        return info 

    def start_streaming(self):
        """Démarrage du streaming optimisé"""
        if not self.streaming_active:
            Vilib.camera_start(vflip=False, hflip=False)
            Vilib.display(local=False, web=True)
            self.streaming_active = True
            self.logger.info("Streaming démarré")

    def stop_streaming(self):
        """Arrête le streaming MJPG"""
        if self.streaming_process:
            self.streaming_process.terminate()
            self.streaming_active = False

    def start_streaming(self):
        """Démarre le streaming MJPG sur le port 8080"""
        try:
            cmd = [
                'mjpg_streamer',
                '-i', 'input_uvc.so -r 640x480 -f 30',
                '-o', 'output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www'
            ]
            
            self.streaming_process = subprocess.Popen(
                ' '.join(cmd),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.streaming_active = True
            
            # Afficher l'URL d'accès
            import socket
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            print(f"\nFlux vidéo disponible sur : http://{ip_address}:8080")
            print("Utilisez cette adresse dans votre navigateur pour voir le flux vidéo")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du streaming: {str(e)}")

    def stop_streaming(self):
        """Arrête le streaming MJPG"""
        if self.streaming_process:
            self.streaming_process.terminate()
            self.streaming_active = False

    def start_streaming(self):
        """Démarre le streaming MJPG sur le port 8080"""
        try:
            cmd = [
                'mjpg_streamer',
                '-i', 'input_uvc.so -r 640x480 -f 30',
                '-o', 'output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www'
            ]
            
            self.streaming_process = subprocess.Popen(
                ' '.join(cmd),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.streaming_active = True
            
            # Afficher l'URL d'accès
            import socket
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            print(f"\nFlux vidéo disponible sur : http://{ip_address}:8080")
            print("Utilisez cette adresse dans votre navigateur pour voir le flux vidéo")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du streaming: {str(e)}")

    def stop_streaming(self):
        """Arrête le streaming MJPG"""
        if self.streaming_process:
            self.streaming_process.terminate()
            self.streaming_active = False

    def start_object_detection(self):
        """Détection d'objets optimisée"""
        Vilib.object_detect_switch(True)
        self.logger.info("Détection d'objets activée") 