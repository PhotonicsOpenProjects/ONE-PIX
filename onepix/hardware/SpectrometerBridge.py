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

    # Reference band used to judge whether a measured signal is usable.
    # These are the exact numbers get_optimal_integration_time() has always
    # converged on; centralised here as class constants so that method and
    # any other consumer (e.g. the hardware settings live-tuning panel)
    # share one definition instead of duplicating the thresholds.
    TARGET_PEAK_COUNTS = 30000
    PEAK_TOLERANCE = 2500
    MIN_INTEGRATION_TIME_MS = 1
    MAX_INTEGRATION_TIME_MS = 10000

    # How many integration periods to drain (read-and-discard) right
    # after a pattern's trigger before trusting a measurement - see the
    # comment in thread_singlepixel_measure(). 2x gives a safety margin
    # over a single scan of internal buffering without adding much real
    # time (a couple of ms at typical integration times).
    STALE_SCAN_FLUSH_PERIODS = 2

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
    def classify_signal(self, peak_intensity):
        """Classify a measured peak intensity against TARGET_PEAK_COUNTS /
        PEAK_TOLERANCE - the same acceptance band get_optimal_integration_time()
        converges the auto-tune loop on.

        Returns "low", "ok" or "saturation".
        """
        low_bound = self.TARGET_PEAK_COUNTS - self.PEAK_TOLERANCE
        high_bound = self.TARGET_PEAK_COUNTS + self.PEAK_TOLERANCE

        if peak_intensity < low_bound:
            return "low"

        if peak_intensity > high_bound:
            return "saturation"

        return "ok"

    def recommend_integration_time(self, peak_intensity, current_integration_time_ms=None):
        """Suggest an integration time (ms) that would bring peak_intensity
        to TARGET_PEAK_COUNTS, using the same proportional-adjustment rule
        get_optimal_integration_time() applies at each of its iterations.
        """
        current = (
            self.integration_time_ms
            if current_integration_time_ms is None
            else current_integration_time_ms
        )

        if peak_intensity <= 0:
            return current

        adjustment_factor = self.TARGET_PEAK_COUNTS / peak_intensity
        recommended = int(current * adjustment_factor)

        return max(
            self.MIN_INTEGRATION_TIME_MS,
            min(recommended, self.MAX_INTEGRATION_TIME_MS)
        )

    def get_optimal_integration_time(self, verbose=True):

        repetitions = 2
        max_counts = self.TARGET_PEAK_COUNTS
        tolerance = self.PEAK_TOLERANCE
        max_iterations = 10
        max_integration_time = self.MAX_INTEGRATION_TIME_MS
        min_integration_time = self.MIN_INTEGRATION_TIME_MS

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
    def thread_singlepixel_measure(
        self, event, stop_event, spectra, dynamic_tint=False, progress_callback=None
    ):

        logging.info(f"{self.spectro_name} spectrometer begin to measure")

        if spectra is None or not isinstance(spectra, np.ndarray):
            raise ValueError("The spectra parameter must be a valid NumPy array.")

        cnt = 0
        self.spectra = spectra
        nb_patterns = np.size(spectra, 0)

        # Minimum real time to spend draining (reading and discarding)
        # scans right after the trigger, before any reading is kept.
        #
        # Waiting longer before the trigger (periode_pattern, in
        # Projection) only helps with the *display's* settle time. It
        # cannot fix staleness that lives on the spectrometer side: this
        # device (seabreeze, default free-running trigger mode) acquires
        # continuously in the background, so the very first scan handed
        # back after a pattern changes can still be one that started
        # integrating *before* the change, or one already sitting in an
        # internal buffer waiting to be read out - no amount of on-screen
        # settle time changes what was already queued. Actively draining
        # for a couple of integration periods flushes that backlog so
        # every *kept* sample's integration window is guaranteed to fall
        # after the drain started, i.e. after the pattern had already
        # settled.
        flush_duration_s = (
            self.STALE_SCAN_FLUSH_PERIODS * self.integration_time_ms / 1000.0
        )

        # Throttled diagnostics: log flush stats for a sample of patterns
        # (not every single one - there can be thousands) so it's
        # possible to tell from the logs whether the drain is doing real
        # work (several scans actually discarded => there was a genuine
        # backlog) instead of just trusting it silently.
        diag_log_every = max(1, nb_patterns // 20)

        while cnt < nb_patterns:

            if stop_event.is_set():
                logging.warning(
                    f"{self.spectro_name} measurement stopped early "
                    "(signalled by the other acquisition thread)"
                )
                break

            if event.is_set():

                trigger_time = time.monotonic()
                flushed = 0
                while True:
                    self.get_intensities()
                    flushed += 1
                    if time.monotonic() - trigger_time >= flush_duration_s:
                        break

                chronograms = []
                for _ in range(self.repetition):
                    intensities = self.get_intensities()
                    chronograms.append(intensities)

                self.spectra[cnt, :] = np.mean(chronograms, axis=0) / self.integration_time_ms

                if cnt % diag_log_every == 0:
                    logging.info(
                        f"{self.spectro_name} pattern {cnt}/{nb_patterns}: "
                        f"flushed {flushed} stale scan(s) over "
                        f"{time.monotonic() - trigger_time:.4f}s before "
                        f"keeping {self.repetition} measurement(s)"
                    )

                cnt += 1
                event.clear()

                if progress_callback is not None:
                    progress_callback(cnt)

            else:
                time.sleep(1e-6)