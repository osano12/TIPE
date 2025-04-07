# -*- coding: utf-8 -*-

"""
Module de Configuration
---------------------
Gère les paramètres de configuration du système PiCarX.
Permet de charger/sauvegarder les configurations depuis un fichier.
"""

import yaml
import logging
from pathlib import Path

class Configuration:
    """
    Gestionnaire de configuration du système.
    Centralise tous les paramètres configurables.
    """

    def __init__(self, config_file="config.yaml"):
        """
        Initialise la configuration.

        Args:
            config_file (str): Chemin vers le fichier de configuration
        """
        self.logger = logging.getLogger('PiCarX.Config')
        self.config_file = Path(config_file)
        
        # Configuration par défaut
        self.default_config = {
            'camera': {
                'resolution': (640, 480),
                'framerate': 30,
                'exposure': 'auto'
            },
            'line_detector': {
                'threshold': 127,
                'roi_height': 0.5  # Portion de l'image à analyser
            },
            'sign_detector': {
                'min_size': (30, 30),
                'confidence_threshold': 0.7
            },
            'motor': {
                'max_speed': 50,
                'min_speed': 10,
                'max_steering': 30,
                'acceleration': 0.5  # Taux d'accélération
            },
            'navigation': {
                'base_speed': 30,
                'stop_wait_time': 2,
                'turn_duration': 1
            }
        }
        
        # Chargement de la configuration
        self.config = self.load_config()

    def load_config(self):
        """
        Charge la configuration depuis le fichier.
        Utilise les valeurs par défaut si le fichier n'existe pas.

        Returns:
            dict: Configuration chargée
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    
                # Fusion avec la configuration par défaut
                config = self.default_config.copy()
                self._deep_update(config, loaded_config)
                
                self.logger.info("Configuration chargée avec succès")
                return config
            else:
                self.logger.warning(
                    f"Fichier de configuration non trouvé: {self.config_file}"
                )
                return self.default_config.copy()
                
        except Exception as e:
            self.logger.error(f"Erreur de chargement config: {str(e)}")
            return self.default_config.copy()

    def save_config(self):
        """Sauvegarde la configuration actuelle dans le fichier."""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            self.logger.info("Configuration sauvegardée")
        except Exception as e:
            self.logger.error(f"Erreur de sauvegarde config: {str(e)}")

    def _deep_update(self, base_dict, update_dict):
        """
        Met à jour récursivement un dictionnaire.

        Args:
            base_dict (dict): Dictionnaire de base
            update_dict (dict): Nouvelles valeurs
        """
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def get(self, key, default=None):
        """
        Récupère une valeur de configuration.

        Args:
            key (str): Clé de configuration (notation pointée possible)
            default: Valeur par défaut si la clé n'existe pas

        Returns:
            Valeur de configuration
        """
        try:
            # Gestion des clés imbriquées (e.g., "camera.resolution")
            keys = key.split('.')
            value = self.config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key, value):
        """
        Définit une valeur de configuration.

        Args:
            key (str): Clé de configuration
            value: Nouvelle valeur
        """
        try:
            keys = key.split('.')
            config = self.config
            for k in keys[:-1]:
                config = config.setdefault(k, {})
            config[keys[-1]] = value
        except Exception as e:
            self.logger.error(f"Erreur de modification config: {str(e)}")
