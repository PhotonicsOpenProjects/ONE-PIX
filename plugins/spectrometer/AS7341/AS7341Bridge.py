import sys
import os
try:
    from plugins.spectrometer.AS7341 import AS7341
except ModuleNotFoundError:
    import AS7341
    
import numpy as np
import time

INTEGRATION_CYCLE_DURATION=2.78E-3 #ms
ASTEP_MAX=2**16
ATIME_MAX=255
INTEGRATION_TIME_MS_MAX=ATIME_MAX*ASTEP_MAX*INTEGRATION_CYCLE_DURATION

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
    'NIR': 910  # Canal proche infrarouge
    }

class AS7341Bridge:
    """Class AS7341Bridge allows to use AS7341 spectral sensor with the ONE-PIX
    kit. Available spectrometers relies on the seabreeze library."""
    def __init__(self, integration_time_ms):
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
        
        self.spec = AS7341.AS7341()
        self.spec.measureMode = 0
        self.spec.AS7341_AGAIN_config(64)
        self.spec.AS7341_EnableLED(False) 
        self.DeviceName = "AS7341"
        self.set_integration_time()
   

    def get_optimal_registers(self):
        """
        # Essayer des valeurs croissantes de ATIME pour trouver une solution acceptable
        target=(self.integration_time_ms/INTEGRATION_CYCLE_DURATION)
        print(target)
        atime_range=np.arange(256)
        astep_range=(target//(atime_range+1)-1)

        astep_idx0=np.abs(astep_range-ASTEP_MAX).argmin()
        astep=int(astep_range[astep_idx0])-1
        atime=int(target/(astep+1))-1

        while astep > ASTEP_MAX or atime > ATIME_MAX or atime<20:
            #print(astep,atime)
            astep_idx0+=1
            astep=int(astep_range[astep_idx0])-1
            atime=int(target//(astep+1))-1
            if astep_idx0>len(astep_range)-1:
                raise ValueError("Impossible de trouver des valeurs ATIME et ASTEP pour ce temps d'intégration")
        print(f"{atime=}, {astep=}")
        """
        target=(self.integration_time_ms/INTEGRATION_CYCLE_DURATION)
        astep=359
        atime=min(int(target/astep),255)
        print(f"{atime=}, {astep=}")
        return astep,atime

    
    def set_integration_time(self):
        """
        set_integration_time allows to set integration time in milliseconds.

        Returns
        -------
        None.

        """
        """Définir le temps d'intégration du capteur en millisecondes."""
        if self.integration_time_ms < 0 or self.integration_time_ms > INTEGRATION_TIME_MS_MAX:
            raise ValueError(f"Le temps d'intégration doit être entre 0 et {INTEGRATION_TIME_MS_MAX} ms")
        
        astep,atime=self.get_optimal_registers()
        self.spec.AS7341_ATIME_config(atime)
        self.spec.AS7341_ASTEP_config(astep)
        print(f"Integration time is : {INTEGRATION_CYCLE_DURATION*(atime+1)*(astep+1)} ms")
    
    def get_wavelengths(self):
        """Récupérer les longueurs d'onde correspondant aux canaux mesurés."""
        return np.array(list(CHANNEL_WAVELENGTHS.values()))

    def get_intensities(self):
        """Lire les données spectrales de tous les canaux."""
        spectrum = []
        self.spec.AS7341_ControlLed(True,10)
        self.spec.AS7341_startMeasure(0)
        self.spec.AS7341_ReadSpectralDataOne()
        spectrum.extend([self.spec.channel1,self.spec.channel2,self.spec.channel3,self.spec.channel4])
        self.spec.AS7341_startMeasure(1)
        self.spec.AS7341_ReadSpectralDataTwo()
        spectrum.extend([self.spec.channel5,self.spec.channel6,self.spec.channel7,self.spec.channel8,self.spec.NIR])
        
        return np.array(spectrum)

    def spec_close(self):
        """Fermer la connexion I2C."""
        if self.spec.i2c is not None:
            self.spec.i2c.close()
            self.spec.i2c = None
