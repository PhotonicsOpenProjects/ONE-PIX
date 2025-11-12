import importlib
import importlib.metadata
import numpy as np
import time
import warnings
import cv2
import logging

from onepix.logging_config import root
logger = logging.getLogger(__name__)


class SpectrometerBridge:
    """
    Generic ONE-PIX spectrometer bridge (plugin-based).

    Each concrete spectrometer must be installed as a Python package
    declaring an entry-point in 'onepix.spectrometers'.

    Example in pyproject.toml of a plugin:
        [project.entry-points."onepix.spectrometers"]
        stub = "Stub"         # -> import Stub
    """

    def __init__(self, spectro_name, integration_time_ms, wl_lim, repetition):
        try:
            self.spectro_name = spectro_name
            self.integration_time_ms = integration_time_ms
            self.wl_lim = wl_lim
            self.repetition = repetition
            self.DeviceName = ""

            logger.info(f"🧩 Initialisation du spectromètre : {spectro_name}")

            # 🔍 Resolve plugin package via entry-point
            self.pkg_name = self._resolve_plugin_package(spectro_name)
            logger.info(f"📦 Plugin détecté : {self.pkg_name}")

            # 📦 Import plugin module
            module = importlib.import_module(self.pkg_name)

            # 🔍 Find bridge class (either <Name>Bridge or <Name>)
            class_name = f"{spectro_name}Bridge"
            if hasattr(module, class_name):
                bridge_class = getattr(module, class_name)
            elif hasattr(module, spectro_name):
                bridge_class = getattr(module, spectro_name)
            else:
                raise ImportError(
                    f"Aucune classe '{class_name}' ni '{spectro_name}' trouvée dans {self.pkg_name}"
                )

            # Instantiate concrete spectrometer
            self.spectrometer = bridge_class(integration_time_ms)
            logger.info(f"{self.spectro_name} spectrometer plugin initialisé")

        except Exception as e:
            raise Exception(f'Spectrometer bridge "{spectro_name}" could not be loaded: {e}')

    # -------------------------------------------------------------------------
    # 🔍 Resolve plugin package from entry-points
    # -------------------------------------------------------------------------
    def _resolve_plugin_package(self, spectro_name: str) -> str:
        eps = importlib.metadata.entry_points()
        if hasattr(eps, "select"):  # Python ≥3.10
            eps_group = eps.select(group="onepix.spectrometers")
        else:
            eps_group = eps.get("onepix.spectrometers", [])

        for ep in eps_group:
            if ep.name.lower() == spectro_name.lower():
                return ep.value

        raise ImportError(
            f"❌ Aucun plugin trouvé pour le spectromètre '{spectro_name}'. "
            "Vérifie qu’il est bien installé et déclare une entry point dans 'onepix.spectrometers'."
        )

    # -------------------------------------------------------------------------
    # --- identical implementation from your working version ------------------
    # -------------------------------------------------------------------------
    def spec_open(self):
        self.spectrometer.spec_open()
        self.DeviceName = self.spectrometer.DeviceName
        wavelengths = self.spectrometer.get_wavelengths()
        self.wavelengths = wavelengths                      # <-- keep for compat
        self.idx_wl_lim = [
            np.abs(wavelengths - self.wl_lim[0]).argmin(),
            np.abs(wavelengths - self.wl_lim[1]).argmin(),
        ]
        logging.info(f'{self.spectro_name} spectrometer plugin is open')

    def set_integration_time(self):
        self.spectrometer.integration_time_ms = self.integration_time_ms
        self.spectrometer.set_integration_time()
        logging.info(f'{self.spectro_name} integration time is fix to {self.integration_time_ms} ms')

    def get_wavelengths(self):
        self.wavelengths = self.spectrometer.get_wavelengths()[
            self.idx_wl_lim[0]: self.idx_wl_lim[1] + 1
        ]
        return self.wavelengths

    def get_intensities(self):
        spectrum = self.spectrometer.get_intensities()[
            self.idx_wl_lim[0]: self.idx_wl_lim[1] + 1
        ]
        return spectrum

    def spec_close(self):
        self.spectrometer.spec_close()
        logging.info(f'{self.spectro_name} spectrometer plugin was close')

    def get_optimal_integration_time(self, verbose=True):
        repetitions = 2
        max_counts = 30000
        tolerance = 2500
        max_iterations = 10
        max_integration_time = 10000
        min_integration_time = 1

        self.set_integration_time()
        delta_wl = round(0.05 * np.size(self.get_wavelengths()))
        count = 0

        while True:
            measurements = [self.get_intensities() for _ in range(repetitions)]

            mean_measurement = np.mean(np.array(measurements), axis=0)[delta_wl:-delta_wl]
            if mean_measurement is not None and mean_measurement.size > 0:
                peak_intensity = max(mean_measurement)
            else:
                peak_intensity = np.max(np.asarray(measurements))
            delta_intensity = peak_intensity - max_counts

            if verbose:
                logging.info(f"T{count}={self.integration_time_ms} ms with intensity peak at {round(peak_intensity)} counts")

            if abs(delta_intensity) < tolerance:
                break

            if count >= max_iterations:
                warnings.warn(f"Stopped after {count} iterations. Final integration time: {self.integration_time_ms} ms.")
                break

            adjustment_factor = max_counts / peak_intensity
            self.integration_time_ms = int(self.integration_time_ms * adjustment_factor)

            if self.integration_time_ms < min_integration_time:
                self.integration_time_ms = min_integration_time
            elif self.integration_time_ms > max_integration_time:
                self.integration_time_ms = 1000

            self.set_integration_time()
            count += 1

        self.spectro_flag = False
        if verbose:
            logging.info(f"Final integration time (ms): {self.integration_time_ms}")
        cv2.destroyAllWindows()
        return self.integration_time_ms

    def thread_singlepixel_measure(self, event, spectra, dynamic_tint=False):
        logging.info(f"{self.spectro_name} spectrometer begin to measure")
        if spectra is None or not isinstance(spectra, np.ndarray):
            raise ValueError("The spectra parameter must be a valid NumPy array.")

        try:
            cnt = 0
            self.spectra = spectra
            nb_patterns = np.size(spectra, 0)
            coeff = 1
            integration_times = []
            while cnt < nb_patterns:
                if event.is_set():
                    if dynamic_tint and cnt < nb_patterns - 1:
                        self.get_optimal_integration_time()
                        integration_times.append(self.integration_time_ms)

                    chronograms = []
                    for _ in range(self.repetition):
                        intensities = self.get_intensities()
                        if intensities is None:
                            raise RuntimeError("Failed to retrieve intensities from the spectrometer.")
                        chronograms.append(coeff * intensities)
                    self.spectra[cnt, :] = np.mean(chronograms, axis=0) / self.integration_time_ms
                    cnt += 1
                    event.clear()
                else:
                    time.sleep(1e-6)
            logging.info(f"{self.spectro_name} spectrometer acquisition complete")
        except Exception as e:
            logging.error(f"An error occurred during spectrometer acquisition: {e}")
        finally:
            pass
