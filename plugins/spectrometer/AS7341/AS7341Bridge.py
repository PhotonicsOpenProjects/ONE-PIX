import smbus2
import time
import numpy as np
# Adresse I2C du capteur AS7341
AS7341_I2C_ADDR = 0x39

# Commandes et registres spécifiques
AS7341_ENABLE = 0x80
AS7341_ATIME = 0x81
AS7341_CONFIG = 0x70
AS7341_STATUS = 0x93
AS7341_DATA_START = 0x95

# Sélection de la banque A ou B
AS7341_CFG0 = 0xA9

# Longueurs d'onde correspondantes aux canaux (en nm)
CHANNEL_WAVELENGTHS = {
    'F1': 415,   # Canal 1
    'F2': 445,   # Canal 2
    'F3': 480,   # Canal 3
    'F4': 515,   # Canal 4
    'F5': 555,   # Canal 5
    'F6': 590,   # Canal 6
    'F7': 630,   # Canal 7
    'NIR': 910  # Canal proche infrarouge
    
    }

# Temps d'intégration de base par cycle en ms
INTEGRATION_TIME_BASE_MS = 2.78

class AS7341Bridge:
    """Class AS7341Bridge allows to use OceanInsight spectrometers with the ONE-PIX
    kit. Available spectrometers relies on the seabreeze library."""
    def __init__(self, integration_time_ms,i2c_bus=1, address=AS7341_I2C_ADDR):
        self.bus = None
        self.address = address
        self.i2c_bus = i2c_bus
        self.integration_time_ms = integration_time_ms
        self.spec = []
        self.DeviceName = ""
        

    def spec_open(self):
        """
        spec_open allows to initialise the connection with the spectrometer.

        Returns
        -------
        None.

        """
        self.bus = smbus2.SMBus(self.i2c_bus)
        """Initialisation interne du capteur."""
        self.bus.write_byte_data(self.address, AS7341_ENABLE, 0x03)  # Activer le capteur
        self.set_integration_time()  # Définir un temps d'intégration par défaut
        self.bus.write_byte_data(self.address, AS7341_CONFIG, 0x00)  # Configuration de base
        time.sleep(0.1)  # Attendre que le capteur se stabilise
        self.DeviceName = "AS7341"
   
    def set_integration_time(self):
        """
        set_integration_time allows to set integration time in milliseconds.

        Returns
        -------
        None.

        """
        """Définir le temps d'intégration du capteur en millisecondes."""
        if self.integration_time_ms < 0 or self.integration_time_ms > 711:
            raise ValueError("Le temps d'intégration doit être entre 0 et 711 ms")
        
        # Calculer la valeur du registre ATIME correspondant
        atime = int(self.integration_time_ms / INTEGRATION_TIME_BASE_MS) - 1
        
        # S'assurer que la valeur ATIME est dans les limites acceptables (0 à 255)
        atime = max(0, min(atime, 255))
        
        self.bus.write_byte_data(self.address, AS7341_ATIME, atime)
    
    def _activate_bank(self, bank):
        """Activer la banque A ou B pour la lecture."""
        if bank == 'A':
            self.bus.write_byte_data(self.address, AS7341_CFG0, 0x00)
        elif bank == 'B':
            self.bus.write_byte_data(self.address, AS7341_CFG0, 0x10)
        else:
            raise ValueError("La banque doit être 'A' ou 'B'")
    
    def get_wavelengths(self):
        """Récupérer les longueurs d'onde correspondant aux canaux mesurés."""
        return np.array(list(CHANNEL_WAVELENGTHS.values()))

    def get_intensities(self):
        """Lire les données spectrales de tous les canaux."""
        spectrum = []

        # Lire les canaux de la banque A
        self._activate_bank('A')
        time.sleep(0.01)  # Attendre un court instant pour que la banque soit active
        for i in range(8):
            # Lire deux octets (16 bits) pour chaque canal spectral
            value = self.bus.read_word_data(self.address, AS7341_DATA_START + 2 * i)
            spectrum.append(value)

        # Lire les canaux de la banque B (NIR et CLEAR)
        self._activate_bank('B')
        time.sleep(0.01)  # Attendre un court instant pour que la banque soit active
        # Mesure du canal NIR
        value = self.bus.read_word_data(self.address, AS7341_DATA_START + 2 * 1)
        spectrum.append(value)

        return spectrum

    def spec_close(self):
        """Fermer la connexion I2C."""
        if self.bus is not None:
            self.bus.close()
            self.bus = None
