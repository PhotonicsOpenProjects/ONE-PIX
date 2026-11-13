"""Acquisition.wait_for_threads: a slow acquisition is waited for, a stuck one is given up on."""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onepix.Acquisition import wait_for_threads  # noqa: E402


def thread(seconds):
    t = threading.Thread(target=time.sleep, args=(seconds,), daemon=True)
    t.start()
    return t


def test_returns_true_when_the_threads_finish():
    assert wait_for_threads([thread(0.2), thread(0.3)], lambda: 0, hard_timeout=5, poll_s=0.05)


def test_hard_timeout_gives_up_on_a_thread_that_does_not_finish():
    assert not wait_for_threads([thread(5)], lambda: 0, hard_timeout=0.3, poll_s=0.05)


def test_stall_timeout_gives_up_when_progress_stops():
    assert not wait_for_threads([thread(5)], lambda: 3, stall_timeout=0.3, poll_s=0.05)


def test_progress_keeps_a_slow_acquisition_going_past_the_stall_time():
    start = time.monotonic()
    t = thread(1.0)
    # the counter moves every ~0.1 s: never stalls for 0.4 s, although the run lasts 1 s
    assert wait_for_threads([t], lambda: int((time.monotonic() - start) * 10), stall_timeout=0.4, poll_s=0.05)
