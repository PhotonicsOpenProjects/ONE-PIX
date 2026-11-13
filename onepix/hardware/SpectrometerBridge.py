import importlib
import importlib.metadata
import math
import numpy as np
import time
import warnings
import cv2
import logging
import inspect
import collections

from onepix.logging_config import root
logger = logging.getLogger(__name__)


class SpectrometerBridge:
    """
    Generic ONE-PIX spectrometer bridge (plugin-based).

    Compatible with:
    - entry points naming a module (Model), searched for the class
    - entry points naming the class itself (package.module:Class)
    - legacy plugins

    Convention supportée :
        model = "Model"
        → module Model
        → class Model

    Mandatory plugin API: spec_open(), set_integration_time(),
    get_wavelengths(), get_intensities(), spec_close() and the attributes
    DeviceName / integration_time_ms.

    Optional plugin capabilities (a plugin without them behaves as before):
        ON_DEMAND = True
            get_intensities() starts its own exposure, so it never returns a
            scan older than the call: no stale-scan flush is needed.
        set_scans_to_average(n)
            the device averages n scans per get_intensities() and returns the
            number applied (n, or less if it cannot). The spectrum must stay a
            mean, not a sum.
        effective_integration_time_ms
            the integration time the device really applies after
            set_integration_time() (rounded or quantised by the device); the
            spectra are normalised by it instead of the requested value.
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

    # Dynamic integration time (dynamic_tint): the time is re-tuned for each
    # pattern, starting from the previous one, so a couple of corrections are
    # enough; the allowed times are a coarse geometric ladder (this many steps
    # per doubling) so that few distinct times need a dark measurement.
    DYNAMIC_TINT_MAX_ITERATIONS = 6
    DYNAMIC_TINT_STEPS_PER_OCTAVE = 4
    # A reading far above the target is probably saturated, so its level is a lower bound and the
    # proportional correction falls short: step back further (a pattern much brighter than the
    # previous one, e.g. after a dark one that needed a long time).
    DYNAMIC_TINT_SATURATION_BACKOFF = 0.5

    def __init__(self, spectro_name, integration_time_ms, wl_lim, repetition):
        try:
            self.spectro_name = spectro_name
            self.integration_time_ms = integration_time_ms
            self.wl_lim = wl_lim
            self.repetition = repetition
            self.DeviceName = ""
            self.is_open = False
            self.effective_integration_time_ms = integration_time_ms
            self.hw_averaging = False
            # duration of the last pattern measurements (s), read by the projection
            # to show the next pattern while the last scans are still being read
            self._measure_times_s = collections.deque(maxlen=20)

            logger.info(f"🧩 Initialisation du spectromètre : {spectro_name}")

            # 🔍 Resolve plugin entry point
            entry_point = self._resolve_entry_point(spectro_name)
            self.pkg_name = entry_point.value
            logger.info(f"📦 Plugin détecté : {self.pkg_name}")

            if ":" in entry_point.value:
                # "package.module:Class" names the class itself
                bridge_class = entry_point.load()
            else:
                # 📦 A module: find the class in it (robuste)
                module = importlib.import_module(entry_point.value)
                bridge_class = self._find_bridge_class(module)

            # Instantiate
            self.spectrometer = bridge_class(integration_time_ms)

            logger.info(f"✅ {self.spectro_name} plugin initialisé ({bridge_class.__name__})")

        except Exception as e:
            raise Exception(f'Spectrometer bridge "{spectro_name}" could not be loaded: {e}')

    # -------------------------------------------------------------------------
    # 🔍 Resolve plugin entry point
    # -------------------------------------------------------------------------
    def _resolve_entry_point(self, spectro_name: str):
        eps = importlib.metadata.entry_points()

        if hasattr(eps, "select"):  # Python ≥3.10
            eps_group = eps.select(group="onepix.spectrometers")
        else:
            eps_group = eps.get("onepix.spectrometers", [])

        for ep in eps_group:
            if ep.name.lower() == spectro_name.lower():
                return ep

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
        self.is_open = True
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

        applied = getattr(self.spectrometer, "effective_integration_time_ms", None)
        self.effective_integration_time_ms = (
            float(applied) if applied else self.integration_time_ms
        )
        if abs(self.effective_integration_time_ms - self.integration_time_ms) > 1e-6:
            logging.warning(
                f"{self.spectro_name} applies {self.effective_integration_time_ms} ms "
                f"for the requested {self.integration_time_ms} ms: spectra are "
                "normalised by the applied value"
            )

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

    # -------------------------------------------------------------------------
    # Optional plugin capabilities (a plugin without them behaves as before)
    #   ON_DEMAND = True          get_intensities() starts its own exposure, so
    #                             it never returns a scan older than the call
    #   set_scans_to_average(n)   the device averages n scans per get_intensities()
    #                             (returns the number applied, may be lower than n)
    # -------------------------------------------------------------------------
    @property
    def on_demand(self):
        return bool(getattr(self.spectrometer, "ON_DEMAND", False))

    @property
    def can_hw_average(self):
        return (
            self.on_demand
            and callable(getattr(self.spectrometer, "set_scans_to_average", None))
            and self.repetition > 1
        )

    def flush_stale_scans(self, duration_s=None):
        """Read and discard scans for `duration_s` (default: STALE_SCAN_FLUSH_PERIODS
        integration periods) so that the next reading integrates after now.
        Returns the number of scans discarded; nothing for an on-demand device,
        which has no backlog."""
        if self.on_demand:
            return 0
        if duration_s is None:
            duration_s = (
                self.STALE_SCAN_FLUSH_PERIODS * self.effective_integration_time_ms / 1000.0
            )
        start = time.perf_counter()
        flushed = 0
        while True:
            self.get_intensities()
            flushed += 1
            if time.perf_counter() - start >= duration_s:
                return flushed

    def measure_time_s(self):
        """Longest of the recent pattern measurements (s), None before any."""
        return max(self._measure_times_s) if self._measure_times_s else None

    def spec_close(self):
        """Release the device, so the next spec_open() - from this or
        another bridge - can open it again: USB spectrometers refuse a
        second open while the first one holds them. A no-op when it
        isn't open, so callers can always call it."""
        if not self.is_open:
            return

        try:
            self.spectrometer.spec_close()
        finally:
            self.is_open = False
            # hardware_initialisation() reopens when this is empty
            self.DeviceName = ""

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

    @classmethod
    def snap_to_ladder(cls, time_ms):
        """`time_ms` moved to the nearest step of a geometric ladder (DYNAMIC_TINT_STEPS_PER_OCTAVE
        steps per doubling)."""
        steps = cls.DYNAMIC_TINT_STEPS_PER_OCTAVE
        return round(2 ** (round(math.log2(time_ms) * steps) / steps), 3)

    @classmethod
    def snap_to_frames(cls, time_ms, frame_ms):
        """`time_ms` moved to a whole number of display frames (`frame_ms` each), the number of
        frames being on the geometric ladder: a time that is not a whole number of frames makes the
        projector's flicker fluctuate each reading (see display_timing.frame_multiple_hint)."""
        steps = cls.DYNAMIC_TINT_STEPS_PER_OCTAVE
        frames = max(1.0, time_ms / frame_ms)
        count = max(1, round(2 ** (round(math.log2(frames) * steps) / steps)))
        return round(count * frame_ms, 3)

    def autoexpose(self, max_iterations=10, snap=None, verbose=True, saturation_backoff=1.0):
        """Adjust integration_time_ms, from its current value, until the peak of the spectrum is
        within PEAK_TOLERANCE of TARGET_PEAK_COUNTS. `snap(time_ms)`, when given, maps each proposed
        time to an allowed one (whole display frames, ladder...). `saturation_backoff` < 1 shortens
        the proposed time further when the peak is more than twice the target. Returns the
        integration time.

        It leaves the projector windows alone, so it can run between two patterns."""
        repetitions = 2
        self.set_integration_time()
        self.flush_stale_scans()

        delta_wl = round(0.05 * np.size(self.get_wavelengths()))
        count = 0

        while True:
            measurements = [self.get_intensities() for _ in range(repetitions)]

            mean_measurement = np.mean(np.array(measurements), axis=0)[delta_wl:-delta_wl]

            if mean_measurement.size > 0:
                peak_intensity = max(mean_measurement)
            else:
                peak_intensity = np.max(np.asarray(measurements))

            if verbose:
                logging.info(
                    f"T{count}={self.integration_time_ms} ms | peak={round(peak_intensity)}"
                )

            if abs(peak_intensity - self.TARGET_PEAK_COUNTS) < self.PEAK_TOLERANCE:
                break

            if count >= max_iterations:
                warnings.warn(
                    f"Stopped after {count} iterations. Final time: {self.integration_time_ms} ms."
                )
                break

            proposed = self.recommend_integration_time(peak_intensity, self.integration_time_ms)
            if peak_intensity > 2 * self.TARGET_PEAK_COUNTS:
                proposed = max(self.MIN_INTEGRATION_TIME_MS, int(proposed * saturation_backoff))
            if snap is not None:
                proposed = max(
                    self.MIN_INTEGRATION_TIME_MS,
                    min(snap(proposed), self.MAX_INTEGRATION_TIME_MS),
                )

            if proposed == self.integration_time_ms:
                # at a limit, or the allowed times are too far apart to get closer
                break

            self.integration_time_ms = proposed
            self.set_integration_time()
            self.flush_stale_scans()
            count += 1

        if verbose:
            logging.info(f"Final integration time: {self.integration_time_ms} ms")

        return self.integration_time_ms

    def get_optimal_integration_time(self, verbose=True):
        self.autoexpose(max_iterations=10, verbose=verbose)
        from onepix.hardware.gui_thread import close_all_windows
        close_all_windows()
        return self.integration_time_ms

    def measure_dark_and_correct(self, spectra=None):
        """Subtract the dark signal from the spectra measured with a dynamic integration time.

        The signal of a dark exposure is not proportional to its duration (readout offset), so spectra
        normalised by different times do not share the same offset and the differences between
        patterns that split methods rely on would carry a bias. The dark is measured, with the
        projector black, once for each integration time that was used, and removed. Call it after the
        measurement thread, with the projector showing black."""
        requested = getattr(self, "tints_requested_ms", None)
        if requested is None:
            raise RuntimeError("no dynamic measurement to correct")
        spectra = self.spectra if spectra is None else spectra

        initial = self.initial_integration_time_ms
        rates = {}
        try:
            for tint in sorted(set(float(t) for t in requested if not np.isnan(t))):
                self.integration_time_ms = tint
                self.set_integration_time()
                self.flush_stale_scans()
                reads = [self.get_intensities() for _ in range(self.repetition)]
                rates[tint] = np.mean(reads, axis=0) / self.effective_integration_time_ms
        finally:
            self.integration_time_ms = initial
            self.set_integration_time()

        for i, tint in enumerate(requested):
            if not np.isnan(tint):
                spectra[i, :] -= rates[float(tint)]

        self.dark_rates = rates
        logging.info(f"dark subtracted for {len(rates)} integration time(s)")
        return rates

    # -------------------------------------------------------------------------
    # 🧵 THREAD ACQUISITION
    # -------------------------------------------------------------------------
    def thread_singlepixel_measure(
        self, event, stop_event, spectra, progress_callback=None,
        dynamic_tint=False, tint_frame_ms=None, dark_patterns=None,
    ):
        """Measure one spectrum each time `event` is set, until `spectra` is full.

        dynamic_tint: re-tune the integration time for every pattern (autoexpose, starting from the
        previous pattern's time) so each spectrum uses the detector's range whatever the pattern's
        brightness. The times are kept in tints_requested_ms / tints_effective_ms and the spectra stay
        normalised by the time actually applied; measure_dark_and_correct() then removes the dark.
        `tint_frame_ms`: the display's frame period, to keep the times to whole numbers of frames.
        `dark_patterns`: one boolean per pattern, True for a black one (HAS projects one after its
        zones). There is no flux to tune on: the search would climb to MAX_INTEGRATION_TIME_MS and
        still not reach the target, taking minutes and measuring the dark with a time of its own. A
        black pattern is measured with the time of the pattern before it, a time the zones used too,
        so the dark correction that follows (measure_dark_and_correct) takes it off like the others.
        """

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
        # An on-demand device has no backlog to flush: each get_intensities()
        # starts its exposure after the call.
        flush_duration_s = (
            0.0 if self.on_demand
            else self.STALE_SCAN_FLUSH_PERIODS * self.effective_integration_time_ms / 1000.0
        )

        # Let the device average the repetitions itself: one transfer per
        # pattern instead of `repetition`. Only for the duration of the
        # measurement, so autotune, live tuning and the projector probe keep
        # getting raw single scans.
        scans_per_read = 1
        if self.can_hw_average:
            applied = self.spectrometer.set_scans_to_average(self.repetition)
            if applied == self.repetition:
                scans_per_read = self.repetition
            else:
                logging.warning(
                    f"{self.spectro_name} averages at most {applied} scan(s) "
                    f"per reading, not {self.repetition}: averaging in software"
                )
                self.spectrometer.set_scans_to_average(None)
        self.hw_averaging = scans_per_read > 1

        self.initial_integration_time_ms = self.integration_time_ms
        self.tints_requested_ms = np.full(nb_patterns, np.nan) if dynamic_tint else None
        self.tints_effective_ms = np.full(nb_patterns, np.nan) if dynamic_tint else None
        snap = None
        if dynamic_tint:
            snap = (
                (lambda t: self.snap_to_frames(t, tint_frame_ms))
                if tint_frame_ms
                else self.snap_to_ladder
            )

        # Throttled diagnostics: log flush stats for a sample of patterns
        # (not every single one - there can be thousands) so it's
        # possible to tell from the logs whether the drain is doing real
        # work (several scans actually discarded => there was a genuine
        # backlog) instead of just trusting it silently.
        diag_log_every = max(1, nb_patterns // 20)

        try:
            while cnt < nb_patterns:

                if stop_event.is_set():
                    logging.warning(
                        f"{self.spectro_name} measurement stopped early "
                        "(signalled by the other acquisition thread)"
                    )
                    break

                if event.is_set():

                    # perf_counter, not monotonic: on Windows monotonic
                    # only moves in ~15.6 ms steps, coarser than the
                    # few-millisecond measurements timed here (and by
                    # Projection, which paces patterns on them).
                    trigger_time = time.perf_counter()

                    if dynamic_tint:
                        if dark_patterns is not None and dark_patterns[cnt]:
                            self.set_integration_time()
                        else:
                            self.autoexpose(
                                self.DYNAMIC_TINT_MAX_ITERATIONS, snap=snap, verbose=False,
                                saturation_backoff=self.DYNAMIC_TINT_SATURATION_BACKOFF,
                            )
                        self.tints_requested_ms[cnt] = self.integration_time_ms
                        self.tints_effective_ms[cnt] = self.effective_integration_time_ms
                        flush_duration_s = (
                            0.0 if self.on_demand
                            else self.STALE_SCAN_FLUSH_PERIODS * self.effective_integration_time_ms / 1000.0
                        )

                    flushed = self.flush_stale_scans(flush_duration_s) if flush_duration_s > 0 else 0

                    chronograms = []
                    for _ in range(self.repetition // scans_per_read):
                        intensities = self.get_intensities()
                        chronograms.append(intensities)

                    self.spectra[cnt, :] = (
                        np.mean(chronograms, axis=0) / self.effective_integration_time_ms
                    )
                    self._measure_times_s.append(time.perf_counter() - trigger_time)

                    if cnt % diag_log_every == 0:
                        logging.info(
                            f"{self.spectro_name} pattern {cnt}/{nb_patterns}: "
                            f"flushed {flushed} stale scan(s) over "
                            f"{time.perf_counter() - trigger_time:.4f}s before "
                            f"keeping {self.repetition} measurement(s)"
                        )

                    cnt += 1
                    event.clear()

                    if progress_callback is not None:
                        progress_callback(cnt)

                else:
                    # blocks until the projection thread sets the event
                    # (no busy loop competing with the GUI/USB threads);
                    # the timeout keeps stop_event checked
                    event.wait(0.01)
        finally:
            if self.hw_averaging:
                self.spectrometer.set_scans_to_average(None)
            if dynamic_tint:
                # back to the configured time (measure_dark_and_correct() relies on the arrays above,
                # not on the device state)
                try:
                    self.integration_time_ms = self.initial_integration_time_ms
                    self.set_integration_time()
                except Exception as exc:
                    logging.warning(f"could not restore the integration time: {exc}")
