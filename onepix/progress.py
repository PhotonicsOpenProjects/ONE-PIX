"""Thread-safe progress tracker for a running acquisition.

A single process-wide singleton, mirroring the pattern already used by
app/GUI/flask/blueprints/acquisition/tuning.py's SpectrometerTuningSession:
Acquisition.thread_acquisition() updates it as patterns are measured, and
the Flask /acquisition/progress route polls a thread-safe snapshot of it so
the browser can show a percentage while /acquisition/run's own (long,
blocking) request is still in flight.
"""

import threading
import time


class AcquisitionCancelled(RuntimeError):
    """Raised inside Acquisition.thread_acquisition() when a run was
    stopped early by a user-requested cancel (as opposed to a genuine
    hardware/thread error)."""


class AcquisitionProgress:

    def __init__(self):
        self._lock = threading.Lock()
        self._stop_event = None
        self._reset_locked()

    def _reset_locked(self):
        self.running = False
        self.status = "idle"  # idle | running | done | error | stopped
        self.current = 0
        self.total = 0
        self.error = None
        self.started_at = None
        self.updated_at = None

    # ------------------------------------------------------------------
    def start(self, total, stop_event=None):
        with self._lock:
            self._reset_locked()
            self.running = True
            self.status = "running"
            self.total = total
            self.started_at = time.time()
            self.updated_at = self.started_at
            self._stop_event = stop_event

    def update(self, current):
        with self._lock:
            if not self.running:
                return
            self.current = current
            self.updated_at = time.time()

    def finish(self):
        with self._lock:
            self.running = False
            self.status = "done"
            self.current = self.total
            self.updated_at = time.time()
            self._stop_event = None

    def fail(self, message):
        with self._lock:
            self.running = False
            self.status = "error"
            self.error = str(message)
            self.updated_at = time.time()
            self._stop_event = None

    def stopped(self):
        with self._lock:
            self.running = False
            self.status = "stopped"
            self.updated_at = time.time()
            self._stop_event = None

    def request_cancel(self):
        """Signal the in-flight acquisition's stop_event, if any is
        currently running. Returns True if a signal was actually sent."""
        with self._lock:
            if not self.running or self._stop_event is None:
                return False
            self._stop_event.set()
            self.status = "stopping"
            self.updated_at = time.time()
            return True

    # ------------------------------------------------------------------
    def snapshot(self):
        with self._lock:
            percent = (
                round(100 * self.current / self.total, 1)
                if self.total else 0.0
            )
            elapsed_s = (
                (self.updated_at or time.time()) - self.started_at
                if self.started_at else 0.0
            )
            return {
                "running": self.running,
                "status": self.status,
                "current": self.current,
                "total": self.total,
                "percent": percent,
                "elapsed_s": round(elapsed_s, 1),
                "error": self.error,
            }


# Process-wide singleton used by Acquisition.thread_acquisition() and the
# /acquisition/progress Flask route.
progress = AcquisitionProgress()
