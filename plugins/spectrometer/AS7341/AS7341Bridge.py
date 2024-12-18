import sys
import os
try:
    from plugins.spectrometer.AS7341 import AS7341
except ModuleNotFoundError:
    import AS7341

import numpy as np
import time

INTEGRATION_CYCLE_DURATION = 2.78E-3  # ms
ASTEP_MAX = 2**16
ATIME_MAX = 255
INTEGRATION_TIME_MS_MAX = ATIME_MAX * ASTEP_MAX * INTEGRATION_CYCLE_DURATION

# Longueurs d'onde correspondantes aux canaux (en nm)
CHANNEL_WAVELENGTHS = {
    'C1': 415,   # Canal 1
    'C2': 445,   # Canal 2
    'C3': 480,   # Canal 3
    'C4': 515,   # Canal 4
    'C5': 555,   # Canal 5
    'C6': 590,   # Canal 6
    'C7': 630,   # Canal 7
    'C8': 670,   # Canal 8
    'NIR': 910   # Canal proche infrarouge
}

# Définition des registres de données pour les canaux spectraux
AS7341_CH0_DATA_L = 0x95


class AS7341Bridge:
    """
    Classe optimisée pour réduire le temps de mesure sur le capteur AS7341.
    - Optimisation du SMUX pour réduire les lectures séquentielles.
    - Sélection de canaux spécifiques pour minimiser le temps.
    - Support du mode de mesure en continu.
    """
    def __init__(self, integration_time_ms):
        self.integration_time_ms = integration_time_ms
        self.spec = None
        self.DeviceName = ""
        self.smux_configured = False

    def spec_open(self):
        """
        Initialise le capteur et démarre les mesures en continu.
        """
        try:
            self.spec = AS7341.AS7341()
            if not self.spec:
                raise RuntimeError("Erreur : Impossible d'initialiser l'instance AS7341.")
            
            # Configurer les paramètres de mesure
            self.spec.measureMode = 0
            self.spec.AS7341_AGAIN_config(128)
            self.DeviceName = "AS7341"
            self.set_integration_time()

            # Configurer le SMUX et démarrer les mesures en continu
            self.optimize_smux_for_selected_channels()
            self.spec.AS7341_startMeasure(0)  # Démarrage en continu
            print("AS7341 initialisé et lancé en mode continu.")
        except Exception as e:
            print(f"Erreur lors de l'initialisation du capteur AS7341 : {e}")
            self.spec = None
            raise

    def set_integration_time(self):
        """
        Configure le temps d'intégration sans optimisation (inchangé).
        """
        if self.integration_time_ms < 0 or self.integration_time_ms > INTEGRATION_TIME_MS_MAX:
            raise ValueError(f"Le temps d'intégration doit être entre 0 et {INTEGRATION_TIME_MS_MAX} ms")
        astep = 359
        atime = min(int(self.integration_time_ms / (astep * INTEGRATION_CYCLE_DURATION)), 255)
        self.spec.AS7341_ATIME_config(atime)
        self.spec.AS7341_ASTEP_config(astep)
        print(f"Temps d'intégration configuré : {INTEGRATION_CYCLE_DURATION * (atime + 1) * (astep + 1)} ms")

    def optimize_smux_for_selected_channels(self):
        """
        Configure le SMUX pour mesurer uniquement les canaux sélectionnés (415, 480, 555, 630, 670).
        """
        if self.spec is None:
            raise RuntimeError("Le capteur AS7341 n'est pas initialisé.")
        if not self.smux_configured:
            self.spec.Write_Byte(0x00, 0x30)  # Configuration SMUX optimisée pour canaux spécifiques
            self.spec.Write_Byte(0x01, 0x01)  # F1 (415 nm)
            self.spec.Write_Byte(0x02, 0x00)  # F3 (480 nm)
            self.spec.Write_Byte(0x03, 0x40)  # F5 (555 nm)
            self.spec.Write_Byte(0x04, 0x50)  # F7 (630 nm)
            self.spec.Write_Byte(0x05, 0x60)  # F8 (670 nm)
            self.spec.Write_Byte(0x06, 0x00)  # Désactiver les autres
            self.spec.Write_Byte(0x07, 0x00)  # Désactiver les autres
            self.smux_configured = True
            print("SMUX configuré pour les canaux sélectionnés.")

    def get_wavelengths(self):
        """
        Retourne les longueurs d'onde correspondant aux canaux sélectionnés.
        """
        selected_wavelengths = ['C1', 'C3', 'C5', 'C7', 'C8']
        return np.array([CHANNEL_WAVELENGTHS[ch] for ch in selected_wavelengths])

    def get_intensities(self):
        """
        Récupère les intensités des canaux mesurés en continu.
        """
        # Vérifier si la mesure est prête
        time.sleep(self.integration_time_ms*1e-3)
        if not self.spec.AS7341_MeasureComplete():
            raise RuntimeError("La mesure n'est pas encore terminée.")
        
        # Lire les données directement
        raw_data = self.spec.i2c.read_i2c_block_data(self.spec.address, AS7341_CH0_DATA_L, 10)  # 5 canaux x 2 octets
        intensities = np.frombuffer(bytearray(raw_data), dtype=np.uint16)
        return intensities

    def spec_close(self):
        """
        Ferme la connexion I2C.
        """
        if self.spec and self.spec.i2c is not None:
            self.spec.i2c.close()
            self.spec.i2c = None
            print("Connexion I2C fermée.")
