"""Live spectrometer integration-time tuning session.

Backs the "Hardware settings" live tuning panel: projects the existing
calibration pattern (Projection.build_test_pattern / init_projection) and
continuously polls the spectrometer in a background thread so the browser
can poll a JSON snapshot and adjust integration time in real time.

Reuses onepix.hardware.HardwareConfig.Hardware / SpectrometerBridge /
Projection as-is - no new hardware communication is introduced here, only
the session/threading plumbing around them.
"""

import threading
import time
import logging

import numpy as np
import cv2

from onepix.hardware.HardwareConfig import Hardware
from onepix.hardware.SpectrometerBridge import SpectrometerBridge
from onepix.hardware.gui_thread import gui_thread
from onepix.logging_config import root

logger = logging.getLogger(__name__)

# Shared across the whole process: guards the physical spectrometer /
# projector so the live tuning panel and a full /run acquisition can never
# drive the hardware at the same time (same rationale as the _measure_lock
# in app/websocket_server/websocket_server.py, scoped to this process).
hardware_lock = threading.Lock()

# Minimum time between two spectrometer reads in the polling loop. Real
# spectrometer plugins already block for ~integration_time_ms inside
# get_intensities(), but stub/fast plugins don't - this keeps the loop (and
# the JSON snapshot it produces) from spinning needlessly fast.
_MIN_LOOP_INTERVAL_S = 0.02


class TuningError(RuntimeError):
    """User-facing tuning error (not connected, busy, invalid input, ...)."""


class SpectrometerTuningSession:
    """One live spectrometer-tuning run: background acquisition thread +
    thread-safe latest-snapshot state. A single instance (see `session`
    below) is shared for the whole process, mirroring how the rest of the
    app treats hardware access as a singleton resource."""

    def __init__(self, hardware_json_path=None, acquisition_json_path=None):
        self._hardware_json_path = hardware_json_path
        self._acquisition_json_path = acquisition_json_path

        self._state_lock = threading.Lock()

        self.hardware = None
        self._running = False
        self._latest = None
        self._error = None

        # Device I/O (get_intensities()) lives on this persistent worker
        # thread across any number of start()/stop() cycles, instead of a
        # fresh thread per cycle. The actual OpenCV/Qt GUI calls it makes
        # (namedWindow, imshow, waitKey, destroyAllWindows) are further
        # routed through the process-wide onepix.hardware.gui_thread
        # singleton rather than issued directly on this thread: OpenCV's
        # Qt backend ties its internal QObjects (the window, the timer
        # waitKey() drives) to whichever OS thread first touches them, and
        # a real acquisition's own projection thread touches the same
        # windows - so every caller in the process must funnel through
        # that one shared GUI thread or risk hanging inside cv2 forever.
        self._run_requested = threading.Event()
        self._stop_requested = threading.Event()
        self._run_finished = threading.Event()
        self._run_finished.set()

        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="spectrometer-tuning",
            daemon=True,
        )
        self._worker_thread.start()

    # ------------------------------------------------------------------
    # START
    # ------------------------------------------------------------------
    def start(self, integration_time_ms=None):
        with self._state_lock:
            if self._running:
                raise TuningError("A tuning session is already running.")

        if not hardware_lock.acquire(blocking=False):
            raise TuningError(
                "The spectrometer/projector is in use by another acquisition."
            )

        try:
            hardware_kwargs = {}
            if integration_time_ms is not None:
                # Must be passed into the constructor (not set on the
                # `hardware` object afterwards): Hardware.__init__ builds
                # its SpectrometerBridge from this value immediately, so a
                # post-construction assignment on `hardware` itself would
                # never reach the bridge.
                hardware_kwargs["integration_time_ms"] = _validate_integration_time(
                    integration_time_ms
                )

            # Construction only (no device I/O, no OpenCV window yet) - safe
            # to do on the request thread. Opening the spectrometer and
            # creating/driving the projection window happens on the
            # persistent worker thread instead (see __init__'s comment).
            hardware = Hardware(
                hardware_config_path=self._hardware_json_path,
                acquisition_parameter_path=self._acquisition_json_path,
                **hardware_kwargs,
            )

        except Exception as exc:
            hardware_lock.release()
            raise TuningError(f"Could not start spectrometer tuning: {exc}") from exc

        self.hardware = hardware
        self._error = None
        self._latest = None
        self._stop_requested.clear()
        self._run_finished.clear()
        self._running = True

        # Wakes the persistent worker thread's wait() below.
        self._run_requested.set()

        logger.info("Spectrometer tuning session started")

        return self.snapshot()

    # ------------------------------------------------------------------
    # PERSISTENT WORKER — one iteration of this outer loop per
    # start()/stop() cycle, always on the same OS thread.
    # ------------------------------------------------------------------
    def _worker_loop(self):
        while True:
            self._run_requested.wait()
            self._run_requested.clear()
            self._run_one_measurement()
            self._run_finished.set()

    def _run_one_measurement(self):
        hardware = self.hardware
        spectrometer = hardware.spectrometer

        try:
            # Device open + OpenCV window creation, on the same thread
            # that will drive them for the rest of this run.
            hardware.hardware_initialisation()

            pattern = hardware.projection.build_test_pattern()
            hardware.projection.init_projection(
                [pattern],
                None,
                cv2.INTER_LINEAR_EXACT,
            )

            while not self._stop_requested.is_set():
                loop_start = time.time()

                try:
                    intensities = np.asarray(spectrometer.get_intensities())
                except Exception as exc:
                    logger.exception("Spectrometer read failed during tuning")
                    with self._state_lock:
                        self._error = str(exc)
                    break

                peak = float(np.max(intensities)) if intensities.size else 0.0

                with self._state_lock:
                    self._latest = {
                        "wavelengths": np.asarray(spectrometer.wavelengths).tolist(),
                        "intensities": intensities.tolist(),
                        "integration_time_ms": spectrometer.integration_time_ms,
                        "peak": peak,
                        "peak_pct": round(
                            100 * peak / SpectrometerBridge.TARGET_PEAK_COUNTS, 1
                        ),
                        "status": spectrometer.classify_signal(peak),
                        "recommended_integration_time_ms":
                            spectrometer.recommend_integration_time(peak),
                        "timestamp": time.time(),
                    }

                # Pump the OpenCV window's event loop so it stays responsive
                # (same purpose as the waitKey() calls in thread_projection).
                gui_thread.run(cv2.waitKey, 1)

                elapsed = time.time() - loop_start
                if elapsed < _MIN_LOOP_INTERVAL_S:
                    time.sleep(_MIN_LOOP_INTERVAL_S - elapsed)

        except Exception as exc:
            logger.exception("Failed to initialise hardware for spectrometer tuning")
            with self._state_lock:
                self._error = str(exc)

        finally:
            self._cleanup_hardware()

            with self._state_lock:
                self._running = False

            logger.info("Spectrometer tuning session stopped")

    # ------------------------------------------------------------------
    # STOP
    # ------------------------------------------------------------------
    def stop(self):
        with self._state_lock:
            was_running = self._running

        if not was_running:
            return self.snapshot()

        self._stop_requested.set()

        # Bounded wait for the worker to finish this run's cleanup. If it
        # never comes back (e.g. a real device wedged mid-read), fall back
        # to marking the session stopped anyway rather than leaving the
        # API permanently reporting "running" - same safety-net philosophy
        # as before, just against an Event instead of Thread.join().
        if not self._run_finished.wait(timeout=10.0):
            logger.error(
                "Spectrometer tuning worker did not stop within 10s; "
                "forcing the session into a stopped state."
            )
            self._cleanup_hardware()
            with self._state_lock:
                self._running = False

        return self.snapshot()

    def _cleanup_hardware(self):
        hardware = self.hardware
        self.hardware = None

        if hardware is None:
            return

        try:
            gui_thread.run(cv2.destroyAllWindows)
        except Exception:
            logger.exception("Error closing the projection window")

        try:
            hardware.spectrometer.spec_close()
        except Exception:
            logger.exception("Error closing the spectrometer")

        if hardware_lock.locked():
            try:
                hardware_lock.release()
            except RuntimeError:
                # Already released by a concurrent cleanup (e.g. stop()'s
                # safety net racing the background thread's own finally).
                pass

    # ------------------------------------------------------------------
    # LIVE INTEGRATION TIME CHANGE
    # ------------------------------------------------------------------
    def set_integration_time(self, integration_time_ms):
        with self._state_lock:
            if not self._running or self.hardware is None:
                raise TuningError("No tuning session is running.")

        value = _validate_integration_time(integration_time_ms)

        try:
            self.hardware.spectrometer.integration_time_ms = value
            self.hardware.spectrometer.set_integration_time()
        except Exception as exc:
            raise TuningError(f"Could not apply integration time: {exc}") from exc

        return self.snapshot()

    # ------------------------------------------------------------------
    # SNAPSHOT
    # ------------------------------------------------------------------
    def snapshot(self):
        with self._state_lock:
            return {
                "running": self._running,
                "error": self._error,
                "spectrum": self._latest,
                "bounds": {
                    "min_integration_time_ms": SpectrometerBridge.MIN_INTEGRATION_TIME_MS,
                    "max_integration_time_ms": SpectrometerBridge.MAX_INTEGRATION_TIME_MS,
                    "target_peak_counts": SpectrometerBridge.TARGET_PEAK_COUNTS,
                },
            }


def _validate_integration_time(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise TuningError("Integration time must be a number.")

    if not (
        SpectrometerBridge.MIN_INTEGRATION_TIME_MS
        <= value
        <= SpectrometerBridge.MAX_INTEGRATION_TIME_MS
    ):
        raise TuningError(
            "Integration time must be between "
            f"{SpectrometerBridge.MIN_INTEGRATION_TIME_MS} and "
            f"{SpectrometerBridge.MAX_INTEGRATION_TIME_MS} ms."
        )

    return value


# Process-wide singleton used by the Flask routes.
session = SpectrometerTuningSession()
