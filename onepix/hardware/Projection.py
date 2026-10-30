import os
import cv2
import screeninfo
import numpy as np
import time

#TL
import logging

from onepix.logging_config import root
from onepix.hardware.gui_thread import gui_thread

logger = logging.getLogger(__name__)

if "DISPLAY" not in os.environ or not os.environ["DISPLAY"]:
    os.environ["DISPLAY"] = ":0"


def get_display_configuration():
    """(width of the first monitor, the monitor patterns are projected on).

    Called when projecting, never when a module is imported: the app (a
    service started at boot) must come up even before the desktop's
    display does - only projecting needs it."""
    try:
        monitors = screeninfo.get_monitors()
    except screeninfo.common.ScreenInfoError as e:
        raise RuntimeError(
            f"No display available for the projector ({e}): is the "
            "desktop session running?"
        ) from e

    if len(monitors) == 0:
        raise RuntimeError(
            "No monitor detected. ONE-PIX requires at least one display."
        )

    screen_width = monitors[0].width

    if len(monitors) == 1:
        logger.warning(
            "Only one monitor detected. Using primary screen as projector."
        )
        projector_monitor = monitors[0]

    else:
        logger.info(
            "Second monitor detected. Using it as projector."
        )
        projector_monitor = monitors[1]

    return screen_width, projector_monitor


class Projection:
    """
    Projection handler.
    """

    def __init__(self, height, width, periode_pattern, proj_position, early_show_ms=0):
        self.height = height
        self.width = width
        self.periode_pattern = periode_pattern
        self.proj_position = proj_position
        # How long before the end of a measurement the next pattern is shown
        # (0: only afterwards). See thread_projection().
        self.early_show_ms = early_show_ms

        # Looked up for each Projection, so a projector plugged in after
        # the app started is found too.
        _, self.monitor = get_display_configuration()

        self.proj_shape = np.array(
            [self.monitor.height, self.monitor.width]
        )

        logging.info("Projection system initialized")

    def create_fullscreen_window(self):
        # WINDOW_FREERATIO: without it, the Qt backend keeps the
        # projected pattern's own aspect ratio (self.width x
        # self.height, e.g. 800x400) and letterboxes it inside the
        # fullscreen window whenever that doesn't match the projector's
        # aspect ratio, leaving bars top/bottom (or left/right) instead
        # of covering the whole screen.
        gui_thread.run(
            cv2.namedWindow,
            "ImageWindow",
            cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO,
        )
        gui_thread.run(cv2.moveWindow, "ImageWindow", self.monitor.x, self.monitor.y)
        gui_thread.run(
            cv2.setWindowProperty,
            "ImageWindow",
            cv2.WND_PROP_FULLSCREEN,
            1,
        )

    def create_integrated_frame(self):
        gui_thread.run(cv2.namedWindow, "background", cv2.WINDOW_NORMAL)
        gui_thread.run(cv2.moveWindow, "background", self.monitor.x, self.monitor.y)
        gui_thread.run(
            cv2.setWindowProperty,
            "background",
            cv2.WND_PROP_FULLSCREEN,
            1,
        )

        gui_thread.run(
            cv2.imshow,
            "background",
            np.zeros(self.proj_shape),
        )

        gui_thread.run(
            cv2.namedWindow,
            "ImageWindow",
            flags=cv2.WINDOW_GUI_EXPANDED,
        )

        gui_thread.run(
            cv2.setWindowProperty,
            "ImageWindow",
            cv2.WND_PROP_FULLSCREEN,
            1,
        )

        gui_thread.run(
            cv2.moveWindow,
            "ImageWindow",
            self.monitor.x + self.proj_position[0],
            self.monitor.y + self.proj_position[1],
        )

        gui_thread.run(
            cv2.resizeWindow,
            "ImageWindow",
            self.width,
            self.height,
        )

        gui_thread.run(
            cv2.setWindowProperty,
            "ImageWindow",
            cv2.WND_PROP_TOPMOST,
            1,
        )

    def build_test_pattern(self):
        """Simple, stable grating pattern used to get a live reading on the
        spectrometer: a low-frequency cosine grid, clipped to non-negative
        values. Reused by get_integration_time_auto() (CLI auto-tune) and by
        the hardware settings live integration-time tuning panel."""
        y = list(range(self.height))
        x = list(range(self.width))

        Y, X = np.meshgrid(x, y)

        A = 2 * np.pi * X * 10 / self.height
        B = 2 * np.pi * Y * 10 / self.width

        test_pattern = np.cos(A + B)
        test_pattern[test_pattern < 0] = 0

        return test_pattern

    def get_integration_time_auto(self, acq_config):
        test_pattern = self.build_test_pattern()

        self.create_fullscreen_window()

        gui_thread.run(
            cv2.imshow,
            "ImageWindow",
            cv2.resize(
                test_pattern,
                (self.width, self.height),
                interpolation=cv2.INTER_LINEAR_EXACT,
            ),
        )

        gui_thread.run(cv2.waitKey, 5000)

        print("Finding the optimal integration time (ms):")

        acq_config.hardware.spectrometer.get_optimal_integration_time()

        acq_config.periode_pattern = int(
            acq_config.hardware.repetition
            * acq_config.hardware.spectrometer.integration_time_ms
        )

        if acq_config.periode_pattern < 60:
            acq_config.periode_pattern = 60

    def init_projection(
        self,
        patterns,
        patterns_order,
        interp_method,
    ):
        logging.info("INIT PROJ START")
        (
            self.create_fullscreen_window()
            if np.all(self.proj_position == "auto")
            else self.create_integrated_frame()
        )
        logging.info("WINDOW CREATED")
        gui_thread.run(
            cv2.imshow,
            "ImageWindow",
            cv2.resize(
                patterns[0],
                (self.width, self.height),
                interpolation=interp_method,
            ),
        )

        gui_thread.run(cv2.waitKey, 3000)
        logging.info("INIT PROJ END")

    def thread_projection(
        self,
        event,
        stop_event,
        patterns,
        patterns_order,
        interp_method,
        measure_time_s=None,
    ):
        """Project the patterns one after the other: show, wait periode_pattern
        (the display's latency), raise `event`, let the spectrometer thread
        measure and clear it.

        periode_pattern is counted from the moment the pattern is shown, and
        the next pattern is resized while the spectrometer measures.

        If early_show_ms > 0 and `measure_time_s()` (longest recent measurement)
        is known, the next pattern is shown early_show_ms before the end of the
        measurement. The projector needs a dead time (tens of ms) before the
        light changes at all, so this hides part of it as long as early_show_ms
        stays below that dead time - see app/cli/probe_settle_time.py --fine."""
        self.init_projection(
            patterns,
            patterns_order,
            interp_method,
        )

        logging.info(
            f"Projection system begins projecting patterns "
            f"({len(patterns)} patterns, "
            f"periode_pattern={self.periode_pattern} ms, "
            f"early_show={self.early_show_ms} ms)"
        )

        # The projection loop is otherwise completely silent for the whole
        # run, so a long acquisition looks exactly like a frozen one in the
        # logs. Log every 10% so progress (or a genuine stall) is visible.
        progress_step = max(1, len(patterns) // 10)

        def resized(pattern):
            return cv2.resize(
                pattern,
                (self.width, self.height),
                interpolation=interp_method,
            )

        def show(image):
            gui_thread.run(cv2.imshow, "ImageWindow", image)
            # imshow only queues the image: the window is refreshed while
            # waitKey pumps the GUI events, so pump right away
            gui_thread.run(cv2.waitKey, 1)
            return time.monotonic()

        image = resized(patterns[0])
        shown_at = show(image)
        early = 0

        for idx in range(len(patterns)):

            if stop_event.is_set():
                logging.warning(
                    "Projection stopped early "
                    "(signalled by the other acquisition thread)"
                )
                break

            remaining_ms = self.periode_pattern - (time.monotonic() - shown_at) * 1000
            if remaining_ms > 1:
                gui_thread.run(cv2.waitKey, int(np.ceil(remaining_ms)))

            if idx % progress_step == 0:
                logging.info(
                    f"Projection progress: {idx}/{len(patterns)}"
                )

            event.set()
            triggered_at = time.monotonic()

            next_image = resized(patterns[idx + 1]) if idx + 1 < len(patterns) else None
            shown_early = False

            measure_s = measure_time_s() if measure_time_s is not None else None
            if next_image is not None and self.early_show_ms > 0 and measure_s:
                show_at = triggered_at + measure_s - self.early_show_ms / 1000.0
                while event.is_set() and not stop_event.is_set():
                    if time.monotonic() >= show_at:
                        shown_at = show(next_image)
                        shown_early = True
                        early += 1
                        break
                    time.sleep(5e-4)

            while event.is_set():
                if stop_event.is_set():
                    break
                time.sleep(5e-4)

            if next_image is not None and not shown_early and not stop_event.is_set():
                shown_at = show(next_image)

        gui_thread.run(cv2.destroyAllWindows)

        logging.info(
            f"Projection system finished projecting patterns ({early} shown early)"
        )
