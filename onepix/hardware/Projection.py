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
    monitors = screeninfo.get_monitors()

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


screenWidth, proj_monitor = get_display_configuration()

class Projection:
    """
    Projection handler.
    """

    def __init__(self, height, width, periode_pattern, proj_position):
        self.height = height
        self.width = width
        self.periode_pattern = periode_pattern
        self.proj_position = proj_position

        self.proj_shape = np.array(
            [proj_monitor.height, proj_monitor.width]
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
        gui_thread.run(cv2.moveWindow, "ImageWindow", proj_monitor.x, proj_monitor.y)
        gui_thread.run(
            cv2.setWindowProperty,
            "ImageWindow",
            cv2.WND_PROP_FULLSCREEN,
            1,
        )

    def create_integrated_frame(self):
        gui_thread.run(cv2.namedWindow, "background", cv2.WINDOW_NORMAL)
        gui_thread.run(cv2.moveWindow, "background", proj_monitor.x, proj_monitor.y)
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
            proj_monitor.x + self.proj_position[0],
            proj_monitor.y + self.proj_position[1],
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
    ):
        self.init_projection(
            patterns,
            patterns_order,
            interp_method,
        )

        logging.info(
            f"Projection system begins projecting patterns "
            f"({len(patterns)} patterns, "
            f"periode_pattern={self.periode_pattern} ms)"
        )

        # The projection loop is otherwise completely silent for the whole
        # run, so a long acquisition looks exactly like a frozen one in the
        # logs. Log every 10% so progress (or a genuine stall) is visible.
        progress_step = max(1, len(patterns) // 10)

        for idx, pattern in enumerate(patterns):

            if stop_event.is_set():
                logging.warning(
                    "Projection stopped early "
                    "(signalled by the other acquisition thread)"
                )
                break

            gui_thread.run(
                cv2.imshow,
                "ImageWindow",
                cv2.resize(
                    pattern,
                    (self.width, self.height),
                    interpolation=interp_method,
                ),
            )

            gui_thread.run(cv2.waitKey, int(self.periode_pattern))

            if idx % progress_step == 0:
                logging.info(
                    f"Projection progress: {idx}/{len(patterns)}"
                )

            event.set()

            time.sleep(1e-6)

            while event.is_set():
                if stop_event.is_set():
                    break
                time.sleep(1e-6)

        gui_thread.run(cv2.destroyAllWindows)

        logging.info(
            "Projection system finished projecting patterns"
        )
