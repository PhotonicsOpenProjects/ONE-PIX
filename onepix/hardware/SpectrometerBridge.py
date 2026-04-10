import importlib
import importlib.metadata
import numpy as np
import time
import warnings
import cv2
import logging
import inspect

from onepix.logging_config import root
logger = logging.getLogger(__name__)


class SpectrometerBridge:
    """
    Generic ONE-PIX spectrometer bridge (plugin-based).

    Compatible with:
    - entry points returning a module (Model)
    - entry points returning a class (Model:Model)
    - legacy plugins

    Convention supportée :
        model = "Model"
        → module Model
        → class Model
    """

    def __init__(self, spectro_name, integration_time_ms, wl_lim, repetition):
        try:
            self.spectro_name = spectro_name
            self.integration_time_ms = integration_time_ms
            self.wl_lim = wl_lim
            self.repetition = repetition
            self.DeviceName = ""

            logger.info(f"🧩 Initialisation du spectromètre : {spectro_name}")

            # 🔍 Resolve plugin package
            self.pkg_name = self._resolve_plugin_package(spectro_name)
            logger.info(f"📦 Plugin détecté : {self.pkg_name}")

            # 📦 Import module
            module = importlib.import_module(self.pkg_name)

            # 🔥 Find correct class (robuste)
            bridge_class = self._find_bridge_class(module)

            # Instantiate
            self.spectrometer = bridge_class(integration_time_ms)

            logger.info(f"✅ {self.spectro_name} plugin initialisé ({bridge_class.__name__})")

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
            f"❌ Aucun plugin trouvé pour '{spectro_name}'. Vérifie l'installation et le pyproject.toml."
        )

    # -------------------------------------------------------------------------
    # 🔥 Find correct class inside module
    # -------------------------------------------------------------------------
    def _find_bridge_class(self, module):

        name = self.spectro_name
        class_name_bridge = f"{name}Bridge"

        # 1. Bridge classique
        if hasattr(module, class_name_bridge):
            return getattr(module, class_name_bridge)

        # 2. Nom exact
        if hasattr(module, name):
            return getattr(module, name)

        # 3. Nom capitalisé (OceanInsight)
        if hasattr(module, name.capitalize()):
            return getattr(module, name.capitalize())

        # 4. Nom CamelCase (oceaninsight → OceanInsight)
        camel = "".join(part.capitalize() for part in name.split("_"))
        if hasattr(module, camel):
            return getattr(module, camel)

        # 5. Fallback auto-détection
        candidates = [
            getattr(module, attr)
            for attr in dir(module)
            if inspect.isclass(getattr(module, attr))
        ]

        if len(candidates) == 1:
            logger.warning(f"⚠️ Classe auto-détectée : {candidates[0].__name__}")
            return candidates[0]

        raise ImportError(
            f"Aucune classe valide trouvée dans {module.__name__}. "
            f"Classes dispo: {[c.__name__ for c in candidates]}"
        )

    # -------------------------------------------------------------------------
    # 📡 API
    # -------------------------------------------------------------------------
    def spec_open(self):
        self.spectrometer.spec_open()
        self.DeviceName = self.spectrometer.DeviceName

        wavelengths = self.spectrometer.get_wavelengths()
        self.wavelengths = wavelengths

        self.idx_wl_lim = [
            np.abs(wavelengths - self.wl_lim[0]).argmin(),
            np.abs(wavelengths - self.wl_lim[1]).argmin(),
        ]

        logging.info(f'{self.spectro_name} spectrometer plugin is open')

    def set_integration_time(self):
        self.spectrometer.integration_time_ms = self.integration_time_ms
        self.spectrometer.set_integration_time()

        logging.info(f'{self.spectro_name} integration time set to {self.integration_time_ms} ms')

    def get_wavelengths(self):
        self.wavelengths = self.spectrometer.get_wavelengths()[
            self.idx_wl_lim[0]: self.idx_wl_lim[1] + 1
        ]
        return self.wavelengths

    def get_intensities(self):
        return self.spectrometer.get_intensities()[
            self.idx_wl_lim[0]: self.idx_wl_lim[1] + 1
        ]

    def spec_close(self):
        self.spectrometer.spec_close()
        logging.info(f'{self.spectro_name} spectrometer plugin closed')

    # -------------------------------------------------------------------------
    # ⚡ AUTO INTEGRATION TIME
    # -------------------------------------------------------------------------
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

            if mean_measurement.size > 0:
                peak_intensity = max(mean_measurement)
            else:
                peak_intensity = np.max(np.asarray(measurements))

            delta_intensity = peak_intensity - max_counts

            if verbose:
                logging.info(
                    f"T{count}={self.integration_time_ms} ms | peak={round(peak_intensity)}"
                )

            if abs(delta_intensity) < tolerance:
                break

            if count >= max_iterations:
                warnings.warn(
                    f"Stopped after {count} iterations. Final time: {self.integration_time_ms} ms."
                )
                break

            adjustment_factor = max_counts / peak_intensity
            self.integration_time_ms = int(self.integration_time_ms * adjustment_factor)

            self.integration_time_ms = max(
                min_integration_time,
                min(self.integration_time_ms, max_integration_time)
            )

            self.set_integration_time()
            count += 1

        if verbose:
            logging.info(f"Final integration time: {self.integration_time_ms} ms")

        cv2.destroyAllWindows()
        return self.integration_time_ms

    # -------------------------------------------------------------------------
    # 🧵 THREAD ACQUISITION
    # -------------------------------------------------------------------------
    def thread_singlepixel_measure(self, event, spectra, dynamic_tint=False):

        logging.info(f"{self.spectro_name} spectrometer begin to measure")

        if spectra is None or not isinstance(spectra, np.ndarray):
            raise ValueError("The spectra parameter must be a valid NumPy array.")

        try:
            cnt = 0
            self.spectra = spectra
            nb_patterns = np.size(spectra, 0)

            while cnt < nb_patterns:

                if event.is_set():

                    chronograms = []
                    for _ in range(self.repetition):
                        intensities = self.get_intensities()
                        chronograms.append(intensities)

                    self.spectra[cnt, :] = np.mean(chronograms, axis=0) / self.integration_time_ms

                    cnt += 1
                    event.clear()

                else:
                    time.sleep(1e-6)

        except Exception as e:
            logging.error(f"Acquisition error: {e}")