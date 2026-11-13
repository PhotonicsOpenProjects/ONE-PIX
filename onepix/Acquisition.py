from onepix.hardware.HardwareConfig import *
from onepix.ImagingMethodBridge import *

import cv2
import os
import time
import threading
import queue
import numpy as np

from datetime import date, datetime
from pathlib import Path

import orjson

from onepix import utils as utils
from onepix import fair
from onepix.hardware.display_timing import frame_period_ms
from onepix.hardware.gui_thread import close_all_windows
from onepix.progress import progress as acquisition_progress
from onepix.progress import AcquisitionCancelled

import logging
from onepix.logging_config import root

logger = logging.getLogger(__name__)



def wait_for_threads(threads, current_progress, hard_timeout=None, stall_timeout=None, poll_s=0.5):
    """Wait for `threads` to finish; True if they all did, False if the wait was given up on.

    hard_timeout: give up this long after the start, whatever happens (None: never).
    stall_timeout: give up when `current_progress()` (patterns measured so far) has not moved for
    this long (None: never). A dynamic integration time can spend minutes on one dim pattern (up to
    MAX_INTEGRATION_TIME_MS per reading), so the total time cannot be predicted from the duration
    estimate, while the absence of progress still tells a stuck device from a slow one."""
    start = time.monotonic()
    last_value = current_progress()
    last_change = start
    while any(t.is_alive() for t in threads):
        for t in threads:
            t.join(timeout=poll_s / max(1, len(threads)))
        now = time.monotonic()
        value = current_progress()
        if value != last_value:
            last_value, last_change = value, now
        if hard_timeout is not None and now - start > hard_timeout:
            return False
        if stall_timeout is not None and now - last_change > stall_timeout:
            return False
    return True

class Acquisition:
    """
    Class Acquisition is used to set up ONE-PIX acquisitions.

    Allows parameters to be loaded from JSON files and optionally overridden
    by providing values at initialization.
    """

    def __init__(
        self,
        hardware_json_path=None,
        acquisition_json_path=None,
        **kwargs
    ):
        """
        Args:
            hardware_json_path (str | None):
                path to hardware_config.json

            acquisition_json_path (str | None):
                path to acquisition_parameters.json
        """

        # ==================================================
        # DEFAULT CONFIG PATH
        # ==================================================
        base_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "conf"
        )

        if hardware_json_path is None:

            hardware_json_path = os.path.join(
                base_path,
                "hardware_config.json"
            )

        if acquisition_json_path is None:

            acquisition_json_path = os.path.join(
                base_path,
                "acquisition_parameters.json"
            )

        # ==================================================
        # LOAD CONFIGS
        # ==================================================
        self.hardware_config_path = hardware_json_path
        self.acquisition_config_path = acquisition_json_path

        self.hardware_dict = self._load_json(
            hardware_json_path
        )

        self.acquisition_results = self._load_json(
            acquisition_json_path
        )

        # ==================================================
        # INITIAL PARAMETERS
        # ==================================================
        params = {

            "imaging_method_name":
                self.acquisition_results.get(
                    "imaging_method_name"
                ),

            # re-tune the integration time for every pattern (see
            # SpectrometerBridge.thread_singlepixel_measure)
            "dynamic_tint":
                bool(
                    self.acquisition_results.get(
                        "dynamic_tint", ACQUISITION_DEFAULTS["dynamic_tint"]
                    )
                ),

            "width":
                self.hardware_dict.get(
                    "width"
                ),

            "height":
                self.hardware_dict.get(
                    "height"
                ),
        }

        # ==================================================
        # RUNTIME OVERRIDES
        # ==================================================
        params.update(kwargs)

        self.acquisition_results.update(kwargs)

        for key, value in params.items():

            setattr(self, key, value)

        # ==================================================
        # COMPONENTS
        # ==================================================
        self.imaging_method = ImagingMethodBridge(
            self.imaging_method_name,
            self.height,
            self.width
        )

        self.hardware = Hardware(
            hardware_config_path=self.hardware_config_path,
            acquisition_parameter_path=self.acquisition_config_path
        )

        self.is_init = False

        logger.info(
            "✅ onepixAcquisition class is init"
        )

    # ======================================================
    # SMART JSON LOADER
    # ======================================================
    @staticmethod
    def _load_json(path):

        try:

            with open(path, "rb") as f:

                data = orjson.loads(
                    f.read()
                )

            # ==============================================
            # SMART DESERIALIZATION
            # ==============================================
            data = utils.deserialize_from_json(
                data
            )

            return data

        except FileNotFoundError:

            logger.warning(
                f"⚠️ Warning: {path} not found. "
                "Using empty config."
            )

            return {}

    # ======================================================
    # HARDWARE UPDATE
    # ======================================================
    def update_hardware(self, **kwargs):

        self.hardware = Hardware(**kwargs)

        logger.info("hardware is updated")

    # ======================================================
    # INIT MEASURE
    # ======================================================
    def init_measure(self):

        if not self.is_init:

            try:

                self.imaging_method.creation_patterns()

                self.nb_patterns = len(
                    self.imaging_method
                    .acquisition_results["patterns_order"]
                )

                self.hardware.hardware_initialisation()

                self.acquisition_results["wavelengths"] = (
                    self.hardware
                    .spectrometer
                    .wavelengths
                )

                self.spectra = np.zeros(
                    (
                        self.nb_patterns,
                        len(
                            self.hardware
                            .spectrometer
                            .wavelengths
                        )
                    ),
                    dtype=np.float32,
                )

                # Read the period off the Projection object rather than off
                # HardwareConfig: the projection loop is what actually paces
                # the run, and it can be given a different period (auto
                # integration-time tuning, manual tweak). Using the
                # HardwareConfig value instead would under-estimate the
                # duration and make thread_acquisition()'s join timeout abort
                # a perfectly healthy - but slower - acquisition.
                periode_pattern = getattr(
                    self.hardware.projection,
                    "periode_pattern",
                    self.hardware.periode_pattern,
                )

                measure_ms = self.hardware.periode_mes

                dark_ms = 0

                if self.dynamic_tint:
                    # each pattern is preceded by a search of its integration time
                    # (a couple of corrections of 2 readings each, plus the flush),
                    # and a dark exposure follows the sequence for every time used
                    tint = self.hardware.spectrometer.integration_time_ms
                    measure_ms += 8 * tint
                    dark_ms = 60 * tint

                self.est_duration = round(
                    (
                        self.nb_patterns
                        * (
                            measure_ms
                            + periode_pattern
                        )
                        + dark_ms
                    ) / (60 * 1000),
                    2
                )

                logger.info(
                    f"duration calculate : "
                    f"{self.est_duration}"
                )

                self.is_init = True

                logger.info("measure is init")

            except Exception as e:

                logger.error(
                    f"error during init_measure : {e}"
                )

                # The spectrometer may already be open: release it, or
                # the next attempt finds it busy.
                self.close()

        else:

            logger.info(
                "measure is already init"
            )

    # ======================================================
    # CLOSE
    # ======================================================
    def close(self):
        """Release the spectrometer opened by init_measure(). Each
        Acquisition opens its own: left open, it keeps the device
        busy and the next acquisition can't open it. Safe to call more
        than once, or after a failed init_measure(); the next
        init_measure() opens it again."""

        hardware = getattr(self, "hardware", None)
        spectrometer = getattr(hardware, "spectrometer", None)

        if spectrometer is not None:

            try:
                spectrometer.spec_close()
            except Exception as e:
                logger.warning(f"Could not close the spectrometer: {e}")

        self.is_init = False

    def _correct_dark(self):
        """Dynamic integration time: measure the dark with the projector black and subtract it."""
        projection = self.hardware.projection

        projection.show_dark()

        try:
            self.hardware.spectrometer.measure_dark_and_correct()
        finally:
            projection.hide_dark()

    # ======================================================
    # THREAD ACQUISITION
    # ======================================================
    def thread_acquisition(self, path=None):

        self.init_measure()

        if not self.is_init:

            raise RuntimeError(
                "Acquisition non initialisée. "
                "Voir l'erreur init_measure précédente."
            )

        logger.info(f"ACTIVE THREADS = {threading.enumerate()}")
        patterns = self.imaging_method.acquisition_results["patterns"]

        logger.info(f"patterns type = {type(patterns)}")
        logger.info(f"patterns len = {len(patterns)}")

        if len(patterns) > 0:
            logger.info(f"pattern[0] shape = {patterns[0].shape}")
            logger.info(f"pattern[0] dtype = {patterns[0].dtype}")

        logger.info(
            f"patterns_order len = "
            f"{len(self.imaging_method.acquisition_results['patterns_order'])}"
        )

        logger.info(
            f"patterns len = {len(patterns)}"
        )

        begin_acq = time.time()

        event = threading.Event()

        # Signalled by either thread if it dies with an exception, so
        # the other thread's busy-wait loop (which would otherwise
        # wait forever for an event.set()/clear() that will never
        # come) can break out immediately instead of hanging.
        stop_event = threading.Event()

        # Threads can't return/raise to the caller directly - any
        # exception raised inside one is captured here so it can be
        # re-raised from the main thread once both threads have
        # stopped.
        thread_errors = queue.Queue()

        def _run_projection_thread():
            try:
                self.hardware.projection.thread_projection(
                    event,
                    stop_event,
                    self.imaging_method.acquisition_results["patterns"],
                    self.imaging_method.acquisition_results["patterns_order"],
                    self.imaging_method.pattern_creation_method.interp_method,
                    measure_time_s=self.hardware.spectrometer.measure_time_s,
                )
            except Exception as exc:
                thread_errors.put(exc)
                stop_event.set()

        def _run_spectrometer_thread():
            try:
                self.hardware.spectrometer.thread_singlepixel_measure(
                    event,
                    stop_event,
                    self.spectra,
                    progress_callback=acquisition_progress.update,
                    dynamic_tint=self.dynamic_tint,
                    tint_frame_ms=tint_frame_ms,
                    dark_patterns=dark_patterns,
                )
            except Exception as exc:
                thread_errors.put(exc)
                stop_event.set()

        # With a dynamic integration time, each time is a whole number of display
        # frames (a projector's flicker fluctuates readings otherwise)
        tint_frame_ms = frame_period_ms() if self.dynamic_tint else None

        # black patterns (HAS ends with one) have no flux to tune the integration time on
        dark_patterns = (
            np.array([not np.any(p) for p in self.imaging_method.acquisition_results["patterns"]])
            if self.dynamic_tint else None
        )

        acquisition_progress.start(len(patterns), stop_event=stop_event)

        # --------------------------------------------------
        # Projection thread
        # --------------------------------------------------
        patterns_thread = threading.Thread(
            target=_run_projection_thread
        )

        # --------------------------------------------------
        # Spectrometer thread
        # --------------------------------------------------
        spectrometer_thread = threading.Thread(
            target=_run_spectrometer_thread
        )

        # Safety-net join timeout, sized off the estimated acquisition
        # duration (in minutes) rather than an arbitrary constant, so
        # a real (long) acquisition isn't aborted early while a truly
        # stuck one doesn't hang the process forever even if
        # stop_event itself somehow never gets checked in time.
        join_timeout = max(60.0, (self.est_duration or 0) * 60 * 3)

        try:

            logging.info("measure begin")

            logger.info("starting projection thread")
            patterns_thread.start()
            logger.info("projection thread started")

            logger.info("starting spectrometer thread")
            spectrometer_thread.start()
            logger.info("spectrometer thread started")

            if self.dynamic_tint:
                # no total limit: the integration time of each pattern is searched for (up to
                # MAX_INTEGRATION_TIME_MS per reading), so the estimate made with the starting time
                # means nothing. A stall of the progress is what tells a stuck device.
                spectro = self.hardware.spectrometer
                worst_pattern_s = 1.5 * (
                    (spectro.DYNAMIC_TINT_MAX_ITERATIONS + 1) * 2 + 2 + spectro.repetition
                ) * spectro.MAX_INTEGRATION_TIME_MS / 1000.0
                finished = wait_for_threads(
                    [patterns_thread, spectrometer_thread],
                    lambda: acquisition_progress.snapshot()["current"],
                    stall_timeout=max(join_timeout, worst_pattern_s),
                )
                limit_text = f"no progress for {max(join_timeout, worst_pattern_s):.0f}s"
            else:
                finished = wait_for_threads(
                    [patterns_thread, spectrometer_thread],
                    lambda: acquisition_progress.snapshot()["current"],
                    hard_timeout=join_timeout,
                )
                limit_text = f"{join_timeout:.0f}s"

            if not finished:
                stop_event.set()
                raise TimeoutError(
                    f"Acquisition threads did not finish ({limit_text}; estimated duration: "
                    f"{self.est_duration} min). The spectrometer may be stuck: check the USB "
                    f"connection and the integration time."
                )

            if not thread_errors.empty():
                raise thread_errors.get()

            # Both threads can also stop cleanly (no exception) because
            # stop_event was set from outside (user-requested cancel) -
            # that must not be reported as a successful acquisition.
            if stop_event.is_set():
                raise AcquisitionCancelled(
                    "Acquisition annulée par l'utilisateur."
                )

            if self.dynamic_tint:
                self._correct_dark()

            # ==============================================
            # Retrieve results
            # ==============================================
            self.spectra = (
                self.hardware
                .spectrometer
                .spectra
            )

            self.duration = (
                time.time() - begin_acq
            )

            self.create_acquisition_header()

            self.acquisition_results["spectra"] = (
                self.spectra
            )

            if self.dynamic_tint:

                # the time applied to each pattern (the spectra are in counts per ms)
                self.acquisition_results["integration_times_ms"] = (
                    self.hardware.spectrometer.tints_effective_ms.tolist()
                )

            self.acquisition_results = (
                self.acquisition_results
                | self.imaging_method.acquisition_results
            )

            # metadata first: put it ahead of the (potentially large)
            # spectra/patterns data so it's the first thing visible when
            # the saved JSON is opened.
            self.acquisition_results = (
                {"metadata": self.build_metadata()}
                | self.acquisition_results
            )

            logging.info("measure is complete")

            acquisition_progress.finish()

        except AcquisitionCancelled as e:

            logging.warning(f"Acquisition cancelled: {e}")

            acquisition_progress.stopped()

            close_all_windows()

            raise

        except Exception as e:

            logging.error(
                f"An error occurred during acquisition: {e}"
            )

            acquisition_progress.fail(e)

            close_all_windows()

            raise

        finally:

            self.is_init = False

    # ======================================================
    # METADATA
    # ======================================================
    def build_metadata(self):
        """Everything needed to trace this acquisition back to how it was
        produced: imaging method, the hardware settings actually in effect
        (not just what the config files say now - those can change before
        the next run) and timing. Saved alongside the raw data/
        reconstruction so a measurement can be understood, checked, or
        re-run later without having to remember or guess what parameters
        were used.

        """

        spectrometer = self.hardware.spectrometer

        proj_position = self.hardware.proj_position
        if hasattr(proj_position, "tolist"):
            proj_position = proj_position.tolist()

        return {
            "imaging_method_name": self.imaging_method_name,
            "acquisition_datetime": datetime.now().isoformat(timespec="seconds"),
            "duration_s": (
                round(self.duration, 3)
                if getattr(self, "duration", None) is not None
                else None
            ),
            "nb_patterns": self.nb_patterns,
            "pattern_height": self.height,
            "pattern_width": self.width,
            "hardware": {
                "spectrometer_name": self.hardware.name_spectro,
                "spectrometer_device": spectrometer.DeviceName,
                "camera_name": self.hardware.name_camera,
                "integration_time_ms": spectrometer.integration_time_ms,
                "effective_integration_time_ms": spectrometer.effective_integration_time_ms,
                "repetition": spectrometer.repetition,
                "stale_scan_flush_periods": (
                    0 if spectrometer.on_demand else spectrometer.STALE_SCAN_FLUSH_PERIODS
                ),
                "on_demand": spectrometer.on_demand,
                "hw_averaging": getattr(spectrometer, "hw_averaging", False),
                "wl_lim": self.hardware.wl_lim,
                "periode_pattern_ms": self.hardware.periode_pattern,
                "latency_hiding_ms": self.hardware.latency_hiding_ms,
                "max_gray_level": self.hardware.max_gray_level,
                "gray_response": bool(self.hardware.gray_response_path),
                "periode_mes_ms": self.hardware.periode_mes,
                "proj_position": proj_position,
            },
            # who/licence/software/identifier of the data (conf/fair_config.json), see onepix.fair
            "acquisition_parameters": {
                "dynamic_tint": self.dynamic_tint,
            },
            "fair": fair.fair_block(),
        }

    # ======================================================
    # HEADER
    # ======================================================
    def create_acquisition_header(self):

        fdate = date.today().strftime("%d_%m_%Y")

        actual_time = time.strftime("%H-%M-%S")

        self.title_param = (
            f"raw_acquisition_parameters_"
            f"{fdate}_{actual_time}.txt"
        )

        self.header = (
            f"ONE-PIX_raw_acquisition_"
            f"{fdate}_{actual_time}"
            + "\n"
            + "--------------------------------------------------------"
            + "\n\n"
            + f"Imaging method: "
            f"{self.imaging_method_name}\n"
            + "Acquisition duration: "
            "%f s" % self.duration
            + "\n"
            + f"Spectrometer "
            f"{self.hardware.name_spectro} : "
            f"{self.hardware.spectrometer.DeviceName}\n"
            + f"Camera: "
            f"{self.hardware.name_camera}\n"
            + "Number of projected patterns: "
            "%d" % self.nb_patterns
            + "\n"
            + "Height of pattern window: "
            "%d pixels" % self.height
            + "\n"
            + "Width of pattern window: "
            "%d pixels" % self.width
            + "\n"
            + "Number of spectral measures "
            "per pattern: %d  "
            % self.hardware.repetition
            + "\n"
            + "Integration time: %d ms"
            % self.hardware
            .spectrometer
            .integration_time_ms
            + "\n"
        )

        logging.info(
            "measure header is created"
        )

# ======================================================
# SAVE RAW DATA
# ======================================================
    def save_raw_data(
        self,
        filename=None,
        save_path=None
    ):

        # ==================================================
        # DEFAULT SAVE PATH
        # ==================================================
        if save_path is None:

            save_path = (
                Path(__file__)
                .resolve()
                .parent.parent
                / "measure"
            )

        save_path = Path(save_path)

        save_path.mkdir(exist_ok=True)

        # ==================================================
        # DATE
        # ==================================================
        fdate = date.today().strftime(
            "%d_%m_%Y"
        )

        actual_time = time.strftime(
            "%H-%M-%S"
        )

        # ==================================================
        # DEFAULT FILENAME
        # ==================================================
        if filename is None:

            filename = (
                f"acquisition_results_"
                f"{fdate}_{actual_time}.json"
            )

        filepath = save_path / filename

        # ==================================================
        # GENERIC JSON SAVE
        # ==================================================
        utils.save_dict_json(
            self.acquisition_results,
            filepath
        )

        # ==================================================
        # LOGS
        # ==================================================
        size_mb = (
            os.path.getsize(filepath)
            / (1024**2)
        )

        logger.info(
            f"Saved acquisition : "
            f"{filepath}"
        )

        logger.info(
            f"File size : "
            f"{size_mb:.2f} MB"
        )
