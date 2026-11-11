import json
import os
import io
import numpy as np
from onepix.hardware.SpectrometerBridge import *
from onepix.hardware.CameraBridge import *
from onepix.hardware.Projection import *
from onepix.hardware.display_timing import frame_multiple_hint, recommended_min_integration_time_ms
from onepix.hardware.gray_response import load_lut

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
            # Show the next pattern this long (ms) before the end of a
            # measurement, hiding part of the projector's dead time. 0 = off;
            # measure it with app/cli/probe_settle_time.py --fine.
            "latency_hiding_ms": hardware_dict.get("latency_hiding_ms", 0),
            # Brightest gray level projected (1-255). Lower it when the projector saturates the
            # spectrometer on the brightest patterns; 255 leaves the patterns as they are.
            "max_gray_level": hardware_dict.get("max_gray_level", 255),
            # Measured gray-level response of the projector (app/cli/probe_gray_response.py), a path
            # relative to this file; its inverse makes the light proportional to the gray patterns.
            "gray_response_path": hardware_dict.get("gray_response_path", ""),
        }

        # Écraser avec les valeurs fournies en argument
        params.update(kwargs)

        # Attribuer dynamiquement les attributs
        for key, value in params.items():
            setattr(self, key, value)
        self.max_gray_level = self._valid_gray_level(self.max_gray_level)

        # Includes the stale-scan flush SpectrometerBridge now does before
        # every kept measurement (see thread_singlepixel_measure) so the
        # acquisition duration estimate - and the watchdog timeout derived
        # from it in Acquisition.thread_acquisition() - stays realistic.
        # An on-demand spectrometer has nothing to flush.
        self.periode_mes = None

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

            hint = frame_multiple_hint(self.integration_time_ms)
            if hint is not None:
                logger.warning(
                    f"integration_time_ms ({self.integration_time_ms} ms) is not a whole number of "
                    f"display frames: the projector's flicker makes each reading fluctuate (about 20 % "
                    f"at 30 ms on a 60 Hz display). Try {hint} ms."
                )

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
        flush_periods = 0 if self.spectrometer.on_demand else SpectrometerBridge.STALE_SCAN_FLUSH_PERIODS
        self.periode_mes = int((self.repetition + flush_periods) * self.integration_time_ms)
        self.camera = CameraBridge(self.name_camera)
        self.projection = Projection(
            self.height, self.width, self.periode_pattern, self.proj_position,
            early_show_ms=self.latency_hiding_ms,
            max_gray_level=self.max_gray_level,
            gray_lut=self._load_gray_lut(),
        )
        logging.info("onepix Hardware class is init ")

    @staticmethod
    def _valid_gray_level(value):
        """max_gray_level as an int in 1-255. A value outside that range is brought back to it and an
        unreadable one falls back to 255 (patterns unchanged), with a warning, rather than blacking
        the patterns out or crashing the hardware initialisation."""
        try:
            level = int(float(value))
        except (TypeError, ValueError):
            logger.warning("max_gray_level %r is not a number: using 255", value)
            return 255
        bounded = min(255, max(1, level))
        if bounded != value:
            logger.warning("max_gray_level %r brought to %d (valid range 1-255)", value, bounded)
        return bounded

    def _load_gray_lut(self):
        if not self.gray_response_path:
            return None
        path = os.path.join(os.path.dirname(os.path.abspath(self.hardware_config_path)), self.gray_response_path)
        try:
            return load_lut(path, self.max_gray_level)
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"gray response {path} not used, patterns are displayed as they are: {e}")
            return None

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

