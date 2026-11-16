"""Each Apply of the analysis pipeline starts from the measurement, not from the previous Apply's result."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

from blueprints.analysis import routes, state  # noqa: E402
from onepix import utils  # noqa: E402
from run import create_app  # noqa: E402

WL = np.linspace(400.0, 700.0, 7)
REFERENCE = np.array([100.0, 120.0, 140.0, 160.0, 180.0, 200.0, 220.0])


@pytest.fixture
def loaded(tmp_path, monkeypatch):
    monkeypatch.setattr(routes, "get_measure_path", lambda: tmp_path)
    monkeypatch.setattr(routes, "get_reference_dir", lambda: tmp_path)

    rng = np.random.default_rng(0)
    cube = rng.uniform(50, 100, size=(4, 4, WL.size))
    utils.save_dict_json(
        {
            "metadata": {"imaging_method_name": "fouriersplit"},
            "wavelengths": WL,
            "reconstructed_data": cube,
            "result2plot": np.zeros((4, 4, 3)),
        },
        tmp_path / "reconstruction_results_test.json",
    )
    reference = tmp_path / "reference.json"
    reference.write_text(json.dumps({"wavelengths": WL.tolist(), "spectrum": REFERENCE.tolist()}))

    client = create_app().test_client()
    assert client.post("/analysis/load", json={"filename": "reconstruction_results_test.json"}).status_code == 200
    yield client, cube, str(reference)
    state.CURRENT_RECONSTRUCTION = state.ORIGINAL_RESULT = state.CURRENT_RESULT = state.CURRENT_FILENAME = None


def apply(client, reference):
    steps = [["reflectance_normalization", {"reference_path": reference}]]
    response = client.post("/analysis/run", json={"steps": steps})
    assert response.status_code == 200, response.data
    return np.array(state.CURRENT_RESULT["reconstructed_data"])


def test_applying_twice_gives_the_same_result_as_applying_once(loaded):
    client, cube, reference = loaded
    once = apply(client, reference)
    twice = apply(client, reference)
    assert once == pytest.approx(cube / REFERENCE)  # the normalisation of the measurement
    assert twice == pytest.approx(once)  # not the normalisation of the normalisation


def test_the_measurement_itself_is_left_alone(loaded):
    client, cube, reference = loaded
    apply(client, reference)
    assert np.array(state.ORIGINAL_RESULT["reconstructed_data"]) == pytest.approx(cube)
    assert "analysis_history" not in state.ORIGINAL_RESULT["metadata"]


def test_a_changed_pipeline_is_not_built_on_the_previous_one(loaded):
    client, cube, reference = loaded
    apply(client, reference)
    response = client.post("/analysis/run", json={"steps": [["reflectance_normalization", {"reference_path": ""}]]})
    assert response.status_code == 200
    # no reference: the data are the measured ones, not the previous Apply's reflectance
    assert np.array(state.CURRENT_RESULT["reconstructed_data"]) == pytest.approx(cube)
    assert len(state.CURRENT_RESULT["metadata"]["analysis_history"]) == 1
