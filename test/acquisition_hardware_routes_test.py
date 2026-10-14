"""Flask-route-level tests for the spectrometer live-tuning panel
(GET /acquisition/hardware + the /acquisition/hardware/tuning/* JSON API).

Complements test/hardware_tuning_test.py, which exercises
SpectrometerTuningSession directly: this file checks the HTTP wiring
(routes, status codes, JSON shape) and the acquisition_parameters.json
persistence path, going through the real Flask app and its process-wide
tuning.session singleton (app/GUI/flask/blueprints/acquisition/tuning.py).

Only one real hardware start()/stop() cycle is shared across the lifecycle
test to keep the run fast - deeper session-loop behavior is already
covered in test/hardware_tuning_test.py.
"""

import json
import os
import sys
import time

import pytest

FLASK_APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask")
sys.path.insert(0, FLASK_APP_DIR)

from run import create_app  # noqa: E402
from blueprints.acquisition import tuning  # noqa: E402

ACQUISITION_PARAMETERS_JSON = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "conf", "acquisition_parameters.json")
)

SPECTRUM_TIMEOUT_S = 12.0


@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


@pytest.fixture(autouse=True)
def _stop_tuning_session_after_each_test():
    """Safety net: whatever a test does, never leak a running session (and
    its held hardware_lock) into the next test."""
    yield
    tuning.session.stop()


def wait_for_snapshot_with_spectrum(client, timeout=SPECTRUM_TIMEOUT_S):
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = client.get("/acquisition/hardware/tuning/snapshot").get_json()
        if data["spectrum"] is not None or data["error"] is not None:
            return data
        time.sleep(0.1)
    raise AssertionError("Timed out waiting for a spectrum/error over HTTP")


# ======================================================================
# PANEL RENDERING ("opening the panel")
# ======================================================================

def test_hardware_page_renders_tuning_panel(client):
    response = client.get("/acquisition/hardware")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert 'id="tuningStartBtn"' in html
    assert 'id="tuningStopBtn"' in html
    assert 'id="tuningChart"' in html
    assert "ONEPIX_TUNING_URLS" in html
    assert "hardware_tuning.js" in html


def test_software_page_does_not_load_tuning_panel(client):
    # The panel is hardware-specific - it must not leak onto the other
    # settings pages.
    response = client.get("/acquisition/software")
    html = response.get_data(as_text=True)
    assert "tuningStartBtn" not in html


# ======================================================================
# START / SNAPSHOT / INTEGRATION TIME / STOP over HTTP
# ======================================================================

def test_start_snapshot_integration_time_and_stop(client):
    start_response = client.post("/acquisition/hardware/tuning/start", json={})
    start_data = start_response.get_json()
    assert start_response.status_code == 200
    assert start_data["ok"] is True
    assert start_data["running"] is True

    data = wait_for_snapshot_with_spectrum(client)
    assert data["ok"] is True
    assert data["error"] is None
    spectrum = data["spectrum"]
    assert spectrum is not None
    assert spectrum["status"] in ("low", "ok", "saturation")

    ok_response = client.post(
        "/acquisition/hardware/tuning/integration_time",
        json={"integration_time_ms": 25},
    )
    assert ok_response.status_code == 200
    assert ok_response.get_json()["ok"] is True

    bad_response = client.post(
        "/acquisition/hardware/tuning/integration_time",
        json={"integration_time_ms": 999999},
    )
    assert bad_response.status_code == 400
    assert bad_response.get_json()["ok"] is False

    stop_response = client.post("/acquisition/hardware/tuning/stop")
    stop_data = stop_response.get_json()
    assert stop_response.status_code == 200
    assert stop_data["ok"] is True
    assert stop_data["running"] is False

    after_stop = client.get("/acquisition/hardware/tuning/snapshot").get_json()
    assert after_stop["running"] is False


def test_double_start_returns_409(client):
    first = client.post("/acquisition/hardware/tuning/start", json={})
    assert first.get_json()["ok"] is True

    second = client.post("/acquisition/hardware/tuning/start", json={})
    assert second.status_code == 409
    assert second.get_json()["ok"] is False


def test_restart_after_stop_streams_data_again(client):
    """Regression test for the reported bug: the spectrum streamed fine on
    the first Start, but a second Start (after Stop) never showed anything
    again - through the actual HTTP flow the browser panel uses."""
    client.post("/acquisition/hardware/tuning/start", json={})
    wait_for_snapshot_with_spectrum(client)
    client.post("/acquisition/hardware/tuning/stop")

    start_again = client.post("/acquisition/hardware/tuning/start", json={})
    assert start_again.get_json()["ok"] is True

    data = wait_for_snapshot_with_spectrum(client)
    assert data["spectrum"] is not None
    assert data["error"] is None


# ======================================================================
# PERSISTENCE ("apply" -> acquisition_parameters.json)
# ======================================================================

def test_apply_persists_integration_time_and_preserves_other_keys(client):
    with open(ACQUISITION_PARAMETERS_JSON, "r", encoding="utf-8") as f:
        original_bytes = f.read()
    original = json.loads(original_bytes)

    try:
        response = client.post(
            "/acquisition/hardware/tuning/apply",
            json={"integration_time_ms": 77},
        )
        assert response.status_code == 200
        assert response.get_json()["ok"] is True

        with open(ACQUISITION_PARAMETERS_JSON, "r", encoding="utf-8") as f:
            updated = json.load(f)

        assert updated["integration_time_ms"] == 77
        for key, value in original.items():
            if key == "integration_time_ms":
                continue
            assert updated[key] == value, f"apply must not touch '{key}'"

    finally:
        with open(ACQUISITION_PARAMETERS_JSON, "w", encoding="utf-8") as f:
            f.write(original_bytes)


def test_apply_rejects_out_of_range_value(client):
    response = client.post(
        "/acquisition/hardware/tuning/apply",
        json={"integration_time_ms": -5},
    )
    assert response.status_code == 400
    assert response.get_json()["ok"] is False
