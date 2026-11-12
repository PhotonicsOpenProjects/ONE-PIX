"""A setting that has a default in the code is shown, and can be adjusted, even when the configuration file
does not contain it (a file reset to the repository's, for instance)."""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

from blueprints.acquisition import controllers as ctl  # noqa: E402
from onepix.hardware.HardwareConfig import ACQUISITION_DEFAULTS, HARDWARE_DEFAULTS, Hardware  # noqa: E402
from run import create_app  # noqa: E402

BARE_HARDWARE = {"name_spectro": "stub", "name_camera": "stubcam", "height": 400, "width": 800,
                 "wl_lim": [350, 900], "proj_position": "auto"}
BARE_SOFTWARE = {"imaging_method_name": "fouriershift", "integration_time_ms": 33.378, "spectro_scans2avg": 1}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    paths = {"hardware": tmp_path / "hardware_config.json", "software": tmp_path / "acquisition_parameters.json"}
    paths["hardware"].write_text(json.dumps(BARE_HARDWARE))
    paths["software"].write_text(json.dumps(BARE_SOFTWARE))
    monkeypatch.setattr(ctl, "get_config_path", lambda category: str(paths.get(category)) if category in paths else None)
    return create_app().test_client(), paths


def shown(client, page):
    return re.findall(r'id="f_(\w+)"', client.get(page).data.decode())


def test_the_hardware_page_shows_the_settings_the_file_lacks(setup):
    client, _ = setup
    fields = shown(client, "/acquisition/hardware")
    for key in HARDWARE_DEFAULTS:
        assert key in fields, f"{key} must be adjustable even if hardware_config.json does not hold it"
    assert 'id="f_max_gray_level" value="255"' in client.get("/acquisition/hardware").data.decode()


def test_the_software_page_shows_the_dynamic_integration_time_when_the_file_lacks_it(setup):
    client, _ = setup
    assert "dynamic_tint" in shown(client, "/acquisition/software")


def test_a_default_that_the_file_overrides_is_not_replaced(setup):
    client, paths = setup
    paths["hardware"].write_text(json.dumps({**BARE_HARDWARE, "max_gray_level": 100, "periode_pattern": 84}))
    page = client.get("/acquisition/hardware").data.decode()
    assert 'id="f_max_gray_level" value="100"' in page and 'id="f_periode_pattern" value="84"' in page


def test_saving_writes_the_setting_with_the_type_of_its_default_and_keeps_the_rest(setup):
    client, paths = setup
    client.post("/acquisition/save/hardware", data={"max_gray_level": "100", "periode_pattern": "84",
                                                    "latency_hiding_ms": "24", "gray_response_path": "gray_response.json"})
    saved = json.loads(paths["hardware"].read_text())
    assert saved["max_gray_level"] == 100 and saved["periode_pattern"] == 84
    assert saved["latency_hiding_ms"] == 24 and saved["gray_response_path"] == "gray_response.json"
    assert saved["name_spectro"] == "stub" and saved["wl_lim"] == [350, 900]            # untouched

    client.post("/acquisition/save/software", data={"dynamic_tint": "true"})
    soft = json.loads(paths["software"].read_text())
    assert soft["dynamic_tint"] is True and soft["integration_time_ms"] == 33.378


def test_hardware_uses_the_same_defaults_as_the_page_when_the_file_lacks_the_settings(monkeypatch):
    class NoScreenProjection:
        """Projection looks for the projector's screen, which a machine without a display does not have."""
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr("onepix.hardware.HardwareConfig.Projection", NoScreenProjection)
    params = os.path.join(os.path.dirname(__file__), "test_params")
    hardware = Hardware(
        hardware_config_path=os.path.join(params, "hardware_config.json"),
        acquisition_parameter_path=os.path.join(params, "acquisition_parameters.json"),
    )
    assert json.load(open(os.path.join(params, "hardware_config.json"))).keys().isdisjoint(HARDWARE_DEFAULTS)
    assert hardware.periode_pattern == HARDWARE_DEFAULTS["periode_pattern"]
    assert hardware.latency_hiding_ms == HARDWARE_DEFAULTS["latency_hiding_ms"]
    assert hardware.max_gray_level == HARDWARE_DEFAULTS["max_gray_level"]
    assert hardware.gray_response_path == HARDWARE_DEFAULTS["gray_response_path"]
    assert ACQUISITION_DEFAULTS == {"dynamic_tint": False}
