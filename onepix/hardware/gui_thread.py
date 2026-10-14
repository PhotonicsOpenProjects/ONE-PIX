"""Single persistent thread that owns every OpenCV HighGUI call for the
whole process.

OpenCV's Qt backend ties its internal QObjects (a window, the timer that
waitKey() drives) to whichever OS thread first touches them. Issuing a
later cv2.namedWindow/imshow/waitKey/... call from a *different* thread
can hang indefinitely - this is what happened when the hardware-tuning
panel's dedicated worker thread and each acquisition run's own
freshly-spawned projection thread both called cv2.* independently: after
the tuning panel had been opened once, the next real acquisition would
sometimes stall forever inside cv2.namedWindow(), never showing anything,
until Acquisition's join timeout gave up and reported an error.

Routing every HighGUI call - from Projection, from the tuning panel,
from the coregistration tool - through gui_thread.run() instead of
calling cv2.* directly keeps them all on the exact same OS thread for the
life of the process, which is what OpenCV's Qt backend actually requires.
"""

import logging
import queue
import threading

logger = logging.getLogger(__name__)

# How long a single OpenCV HighGUI call is allowed to run before run()
# gives up waiting on it. A projector/display glitch can wedge
# cv2.waitKey()/cv2.imshow() forever; since every call is funnelled
# through this one persistent thread (see module docstring), a wedged
# call used to block every later acquisition permanently - the only way
# out was to restart the whole process. A bounded wait turns that
# silent, indefinite hang into a fast, explicit error instead.
_CALL_TIMEOUT_S = 15.0


class GuiThreadStuckError(RuntimeError):
    """Raised when a call through gui_thread.run() doesn't return in time,
    or when a previous call left the shared worker thread wedged."""


class _GuiThread:

    def __init__(self):
        self._tasks = queue.Queue()
        # Once a call times out, the worker thread is presumed stuck
        # inside that call forever (Python threads can't be killed) - so
        # every later run() fails fast instead of silently queueing up
        # behind a task that will never be picked up.
        self._wedged = False

        self._thread = threading.Thread(
            target=self._loop,
            name="opencv-gui",
            daemon=True,
        )

        self._thread.start()

    def _loop(self):
        while True:
            fn, args, kwargs, done, result = self._tasks.get()

            try:
                result["value"] = fn(*args, **kwargs)

            except BaseException as exc:
                result["error"] = exc

            finally:
                done.set()

    def run(self, fn, *args, **kwargs):
        if self._wedged:
            raise GuiThreadStuckError(
                "Le fil d'affichage OpenCV est bloqué suite à un appel "
                "précédent qui n'a jamais abouti (écran/projecteur "
                "indisponible ?). Un redémarrage de l'application est "
                "nécessaire pour le débloquer."
            )

        done = threading.Event()
        result = {}

        self._tasks.put((fn, args, kwargs, done, result))

        if not done.wait(timeout=_CALL_TIMEOUT_S):
            self._wedged = True

            fn_name = getattr(fn, "__name__", str(fn))

            logger.error(
                "OpenCV GUI call %s did not return within %.0fs; "
                "marking the GUI thread as wedged, further display "
                "calls will fail fast until the app is restarted.",
                fn_name,
                _CALL_TIMEOUT_S,
            )

            raise GuiThreadStuckError(
                f"Appel d'affichage OpenCV ({fn_name}) bloqué depuis "
                f"plus de {_CALL_TIMEOUT_S:.0f}s."
            )

        if "error" in result:
            raise result["error"]

        return result.get("value")


gui_thread = _GuiThread()
