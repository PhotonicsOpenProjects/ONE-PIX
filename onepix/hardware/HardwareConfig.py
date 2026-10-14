import json
import os
import io
import numpy as np
from onepix.hardware.SpectrometerBridge import *
from onepix.hardware.CameraBridge import *
from onepix.hardware.Projection import *
from onepix.hardware.display_timing import recommended_min_integration_time_ms

import logging
from onepix.logging_config import root  
logger = logging.getLogger(__name__)

# import screeninfo

# screenWidth = screeninfo.get_monitors()[0].width
# try:
#     proj_shape = screeninfo.get_monitors()[1]
#     logging.info('your second screen will be use as a projector')
# except IndexError:
#     logging.warning('No double screen was detected : Please use a projector to use ONE-PIX')
#     # sys.exit()


class Hardware:

    def __init__(self, hardware_config_path=None, acquisition_parameter_path=None, **kwargs):
        self.root_path = os.getcwd()
        conf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "conf")

        # Charger les fichiers JSON (chemins fournis par l'appelant, sinon défaut conf/)
        self.hardware_config_path = hardware_config_path or os.path.join(conf_path, "hardware_config.json")
        self.acquisition_parameter_path = acquisition_parameter_path or os.path.join(conf_path, "acquisition_parameters.json")

        hardware_dict = self._load_json(self.hardware_config_path)
        param_dict = self._load_json(self.acquisition_parameter_path)

        # Définition des paramètres par défaut depuis JSON
        params = {
            "name_spectro": hardware_dict.get("name_spectro"),
            "name_camera": hardware_dict.get("name_camera"),
            "integration_time_ms": param_dict.get("integration_time_ms"),
            "repetition": param_dict.get("spectro_scans2avg"),
            "height": hardware_dict.get("height"),
            "width": hardware_dict.get("width"),
            "proj_position": np.array(hardware_dict.get("proj_position", [])),
            "spectra": [],
            "res": [],
            "normalised_datacube": [],
            "spectro_flag": False,
            "wl_lim": hardware_dict.get("wl_lim"),
            "interp_method": None,
            # Time (ms) each pattern stays on screen before the
            # spectrometer is triggered - i.e. the settle time given to
            # the projector/display to actually finish updating. Too
            # short a value and the measurement can start while the
            # previous pattern is still on screen (or mid-transition),
            # corrupting every spectrum with crosstalk from its
            # neighbour and turning the reconstructed image into noise
            # instead of the expected sparse Fourier spectrum. Exposed
            # in hardware_config.json (default 60) so it can be tuned
            # per projector without editing code.
            "periode_pattern": hardware_dict.get("periode_pattern", 60),
        }

        # Écraser avec les valeurs fournies en argument
        params.update(kwargs)

        # Attribuer dynamiquement les attributs
        for key, value in params.items():
            setattr(self, key, value)

        # Includes the stale-scan flush SpectrometerBridge now does before
        # every kept measurement (see thread_singlepixel_measure) so the
        # acquisition duration estimate - and the watchdog timeout derived
        # from it in Acquisition.thread_acquisition() - stays realistic.
        self.periode_mes = int(
            (self.repetition + SpectrometerBridge.STALE_SCAN_FLUSH_PERIODS)
            * self.integration_time_ms
        )

        # A single-chip DLP projector (colour wheel + DMD PWM) flickers a
        # "static" pattern at the wheel's rotation rate - a spectrometer
        # window shorter than that captures a random phase slice of it
        # instead of the pattern's true value, adding noise that no
        # amount of settle time (periode_pattern) or stale-scan flushing
        # fixes. See onepix/hardware/display_timing.py and
        # app/cli/probe_projection_frequency.py (measures the actual
        # flicker period on a given projector instead of guessing).
        try:
            min_recommended_ms = recommended_min_integration_time_ms()

            if self.integration_time_ms < min_recommended_ms:
                logger.warning(
                    f"integration_time_ms ({self.integration_time_ms} ms) is "
                    f"below the ~{min_recommended_ms:.1f} ms floor recommended "
                    "to average out a DLP projector's colour-wheel/DMD-PWM "
                    "flicker regardless of its phase. If measurements look "
                    "noisier than expected, try raising it (or run "
                    "app/cli/probe_projection_frequency.py to measure this "
                    "projector's actual flicker period instead of guessing)."
                )
        except Exception:
            logger.exception(
                "Could not evaluate the recommended minimum integration "
                "time (non-fatal, continuing)"
            )

        # Initialisation des objets externes
        self.spectrometer = SpectrometerBridge(
            self.name_spectro, self.integration_time_ms, self.wl_lim, self.repetition
        )
        self.camera = CameraBridge(self.name_camera)
        self.projection = Projection(
            self.height, self.width, self.periode_pattern, self.proj_position
        )
        logging.info("onepix Hardware class is init ")

    @staticmethod
    def _load_json(path):
        """Charge un fichier JSON en gérant les erreurs."""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning(f"⚠️ Warning: {path} not found. Using empty config.")
            return {}

    def is_raspberrypi(self):
        """
        is_raspberrypi return a boolean to determine if the current OS is a raspberrry

        """
        try:
            with io.open("/sys/firmware/devicetree/base/model", "r") as m:
                if "raspberry pi" in m.read().lower():
                    return True
        except Exception:
            pass
        return False

    def hardware_initialisation(self):

        # Spectrometer connection
        if self.spectrometer.DeviceName == "":
            self.spectrometer.spec_open()

        self.spectrometer.set_integration_time()
        self.spectrometer.get_wavelengths()
        logging.info(f"all hardware  is now open and ready to use")

