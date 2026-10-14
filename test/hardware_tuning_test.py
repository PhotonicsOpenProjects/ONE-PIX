"""Tests for the spectrometer live-tuning session
(app/GUI/flask/blueprints/acquisition/tuning.py) and the SpectrometerBridge
signal-classification helpers it relies on.

Uses the same real-hardware-via-Stub-plugin approach as the rest of the
test suite (test/test_params/*.json -> StubSpectrometer/StubCamera), no
mocking framework - only StubSpectrometer.get_intensities() is monkeypatched
in a couple of places to get deterministic (non-random) readings for the
signal-classification checks.

SpectrometerTuningSession owns exactly one persistent OS thread for every
OpenCV/Qt GUI call across its whole lifetime (see the class docstring in
tuning.py for why - OpenCV's Qt HighGUI backend hangs if a second, *different*
thread tries to drive an already-touched window/timer later). A fresh
SpectrometerTuningSession() per test would each spawn their own such thread,
which - being different OS threads - would reproduce that exact hang from
the second hardware-touching test onward. So this file mirrors production
(a single long-lived tuning.session singleton reused across every
start()/stop() click) with one module-scoped session shared by every test
here, stopped (not destroyed) between tests.
"""

import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"),
)

from blueprints.acquisition import tuning  # noqa: E402
from onepix.hardware.SpectrometerBridge import SpectrometerBridge  # noqa: E402

TEST_PARAMS_DIR = os.path.join(os.path.dirname(__file__), "test_params")
HARDWARE_JSON = os.path.join(TEST_PARAMS_DIR, "hardware_config.json")
ACQUISITION_JSON = os.path.join(TEST_PARAMS_DIR, "acquisition_parameters.json")

# Settling time init_projection() blocks on before the polling loop starts
# reading the spectrometer (cv2.waitKey(3000) inside Projection.init_projection).
SETTLE_S = 3.5
SPECTRUM_TIMEOUT_S = SETTLE_S + 4.0


@pytest.fixture(scope="module")
def session():
    s = tuning.SpectrometerTuningSession(
        hardware_json_path=HARDWARE_JSON,
        acquisition_json_path=ACQUISITION_JSON,
    )
    yield s
    s.stop()


@pytest.fixture(autouse=True)
def _stop_after_each_test(session):
    # Never leak a running measurement (or its held hardware_lock) from one
    # test into the next - the session object itself (and its one worker
    # thread) stays alive across the whole module, only stop()ped here.
    yield
    session.stop()


def wait_for_spectrum(session, timeout=SPECTRUM_TIMEOUT_S):
    deadline = time.time() + timeout
    while time.time() < deadline:
        snap = session.snapshot()
        if snap["spectrum"] is not None or snap["error"] is not None:
            return snap
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for a spectrum/error")


def wait_until_stopped(session, timeout=SPECTRUM_TIMEOUT_S):
    deadline = time.time() + timeout
    snap = session.snapshot()
    while snap["running"] and time.time() < deadline:
        time.sleep(0.05)
        snap = session.snapshot()
    return snap


def force_reading(session, value):
    """Monkeypatch the underlying Stub plugin's get_intensities() so the
    next loop iteration reports a fixed, deterministic peak instead of the
    Stub's random one."""
    n = len(session.hardware.spectrometer.wavelengths)
    session.hardware.spectrometer.spectrometer.get_intensities = \
        lambda: np.full(n, float(value))


# ======================================================================
# SpectrometerBridge.classify_signal / recommend_integration_time
# (pure logic - no session/hardware needed)
# ======================================================================

def _bridge():
    return SpectrometerBridge("StubSpectrometer", 10, [400, 1000], 1)


def test_classify_signal_low_ok_saturation():
    bridge = _bridge()

    assert bridge.classify_signal(0) == "low"
    assert bridge.classify_signal(bridge.TARGET_PEAK_COUNTS - bridge.PEAK_TOLERANCE - 1) == "low"

    assert bridge.classify_signal(bridge.TARGET_PEAK_COUNTS) == "ok"
    assert bridge.classify_signal(bridge.TARGET_PEAK_COUNTS - bridge.PEAK_TOLERANCE) == "ok"
    assert bridge.classify_signal(bridge.TARGET_PEAK_COUNTS + bridge.PEAK_TOLERANCE) == "ok"

    assert bridge.classify_signal(bridge.TARGET_PEAK_COUNTS + bridge.PEAK_TOLERANCE + 1) == "saturation"
    assert bridge.classify_signal(65535) == "saturation"


def test_recommend_integration_time_scales_and_clamps():
    bridge = _bridge()

    # Half the target peak -> roughly double the integration time.
    recommended = bridge.recommend_integration_time(
        bridge.TARGET_PEAK_COUNTS / 2, current_integration_time_ms=10
    )
    assert recommended == pytest.approx(20, abs=1)

    # Clamped to the documented bounds either direction.
    assert bridge.recommend_integration_time(1, current_integration_time_ms=10000) \
        == bridge.MAX_INTEGRATION_TIME_MS
    assert bridge.recommend_integration_time(1_000_000_000, current_integration_time_ms=10000) \
        == bridge.MIN_INTEGRATION_TIME_MS

    # Zero/negative peak: nothing to scale from, current value is returned.
    assert bridge.recommend_integration_time(0, current_integration_time_ms=7) == 7


def test_validate_integration_time_bounds():
    assert tuning._validate_integration_time(SpectrometerBridge.MIN_INTEGRATION_TIME_MS) \
        == SpectrometerBridge.MIN_INTEGRATION_TIME_MS
    assert tuning._validate_integration_time(SpectrometerBridge.MAX_INTEGRATION_TIME_MS) \
        == SpectrometerBridge.MAX_INTEGRATION_TIME_MS

    with pytest.raises(tuning.TuningError):
        tuning._validate_integration_time(SpectrometerBridge.MIN_INTEGRATION_TIME_MS - 1)

    with pytest.raises(tuning.TuningError):
        tuning._validate_integration_time(SpectrometerBridge.MAX_INTEGRATION_TIME_MS + 1)

    with pytest.raises(tuning.TuningError):
        tuning._validate_integration_time("not-a-number")


# ======================================================================
# SESSION LIFECYCLE — cheap cases (no real hardware settle needed)
# ======================================================================

def test_set_integration_time_requires_running_session(session):
    with pytest.raises(tuning.TuningError):
        session.set_integration_time(10)


def test_double_start_is_rejected_while_running(session):
    state = session.start()
    assert state["running"] is True

    with pytest.raises(tuning.TuningError):
        session.start()


# ======================================================================
# SESSION LIFECYCLE — real hardware
# ======================================================================

def test_start_wait_for_spectrum_then_stop(session):
    state = session.start()
    assert state["running"] is True

    snap = wait_for_spectrum(session)
    assert snap["running"] is True
    assert snap["error"] is None

    spectrum = snap["spectrum"]
    assert spectrum is not None
    assert len(spectrum["wavelengths"]) == len(spectrum["intensities"])
    assert spectrum["status"] in ("low", "ok", "saturation")
    assert spectrum["peak"] >= 0

    stopped = session.stop()
    assert stopped["running"] is False
    assert not tuning.hardware_lock.locked()

    # stop() must be safe to call again (closing the panel twice, etc).
    assert session.stop()["running"] is False


def test_restart_after_stop_produces_a_fresh_spectrum(session):
    """Regression test for the exact bug reported in production: the live
    spectrum streamed fine on the first "Start measurement", but a second
    Start (after Stop) never showed anything again. Root cause was a fresh
    background thread per start() driving OpenCV/Qt from a different OS
    thread each time; SpectrometerTuningSession now keeps one persistent
    worker thread for its whole lifetime instead."""
    session.start()
    wait_for_spectrum(session)
    session.stop()
    assert not session.snapshot()["running"]

    state = session.start()
    assert state["running"] is True

    snap = wait_for_spectrum(session)
    assert snap["running"] is True
    assert snap["spectrum"] is not None

    session.stop()


def test_integration_time_change_and_signal_status(session):
    session.start()
    wait_for_spectrum(session)

    # ---- change integration time while running ----
    session.set_integration_time(37)
    time.sleep(0.3)
    assert session.snapshot()["spectrum"]["integration_time_ms"] == 37

    with pytest.raises(tuning.TuningError):
        session.set_integration_time(999999)

    # ---- weak signal is classified as "low" ----
    force_reading(session, 100.0)
    time.sleep(0.3)
    assert session.snapshot()["spectrum"]["status"] == "low"

    # ---- strong signal is classified as "saturation" ----
    force_reading(session, 60000.0)
    time.sleep(0.3)
    assert session.snapshot()["spectrum"]["status"] == "saturation"


# ======================================================================
# ERROR HANDLING
# ======================================================================

def test_spectrometer_read_error_surfaces_and_stops_cleanly(session):
    session.start()
    wait_for_spectrum(session)

    def boom():
        raise RuntimeError("simulated spectrometer failure")

    session.hardware.spectrometer.spectrometer.get_intensities = boom

    snap = wait_until_stopped(session)

    assert snap["running"] is False
    assert snap["error"] and "simulated spectrometer failure" in snap["error"]

    # The hardware lock must be released even though the session stopped
    # itself due to an error, not via stop().
    assert not tuning.hardware_lock.locked()
