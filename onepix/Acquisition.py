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
from onepix.progress import progress as acquisition_progress
from onepix.progress import AcquisitionCancelled

import logging
from onepix.logging_config import root

logger = logging.getLogger(__name__)


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

            "dynamic_tint":
                self.acquisition_results.get(
                    "dynamic_tint"
                ),

            "normalisation_path":
                self.hardware_dict.get(
                    "normalisation_path"
                ),

            "normalisation":
                self.acquisition_results.get(
                    "Normalisation"
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

                self.est_duration = round(
                    (
                        self.nb_patterns
                        * (
                            self.hardware.periode_mes
                            + periode_pattern
                        )
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

                self.is_init = False

        else:

            logger.info(
                "measure is already init"
            )

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
                    self.dynamic_tint,
                    progress_callback=acquisition_progress.update,
                )
            except Exception as exc:
                thread_errors.put(exc)
                stop_event.set()

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

            patterns_thread.join(timeout=join_timeout)
            spectrometer_thread.join(timeout=join_timeout)

            if patterns_thread.is_alive() or spectrometer_thread.is_alive():
                stop_event.set()
                raise TimeoutError(
                    f"Acquisition threads did not finish within "
                    f"{join_timeout:.0f}s (estimated duration: "
                    f"{self.est_duration} min)."
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

            cv2.destroyAllWindows()

            raise

        except Exception as e:

            logging.error(
                f"An error occurred during acquisition: {e}"
            )

            acquisition_progress.fail(e)

            cv2.destroyAllWindows()

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
                "repetition": spectrometer.repetition,
                "stale_scan_flush_periods": spectrometer.STALE_SCAN_FLUSH_PERIODS,
                "wl_lim": self.hardware.wl_lim,
                "periode_pattern_ms": self.hardware.periode_pattern,
                "periode_mes_ms": self.hardware.periode_mes,
                "proj_position": proj_position,
            },
            "acquisition_parameters": {
                "dynamic_tint": self.dynamic_tint,
                "normalisation": self.normalisation,
                "normalisation_path": self.normalisation_path,
            },
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
