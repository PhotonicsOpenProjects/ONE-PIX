"""Software settings > Normalisation: acquire a reference datacube and keep it as it is
(app/GUI/flask/blueprints/acquisition/normalisation.py). The acquisition is simulated: no hardware."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

from blueprints.acquisition import normalisation as N  # noqa: E402
from blueprints.acquisition import tuning  # noqa: E402
from onepix import utils  # noqa: E402
from onepix.progress import AcquisitionCancelled  # noqa: E402
from run import create_app  # noqa: E402

CUBE = np.random.default_rng(0).random((5, 6, 4)).astype(np.float32)


class FakeAcquisition:
    acquisition_results = {"integration_time_ms": 33.4, "spectro_scans2avg": 2}
    closed = 0

    def init_measure(self):
        pass

    def thread_acquisition(self):
        pass

    def close(self):
        type(self).closed += 1


class FakeReconstruction:
    def __init__(self, acquisition_results, plot_result=False):
        self.reconstruction_results = {}

    def data_reconstruction(self):
        self.reconstruction_results = {
            "reconstructed_data": CUBE, "wavelengths": [400, 500, 600, 700],
            "metadata": {"imaging_method_name": "fouriershift"},
        }

    def save_reconstruction_results(self, filename, save_path):
        utils.save_dict_json(self.reconstruction_results, os.path.join(save_path, filename))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(N, "reference_dir", lambda: tmp_path)
    monkeypatch.setattr(N, "Acquisition", FakeAcquisition)
    monkeypatch.setattr(N, "Reconstruction", FakeReconstruction)
    FakeAcquisition.closed = 0
    return create_app().test_client()


def run(client, **body):
    return client.post("/acquisition/normalisation/run", json=body)


def test_a_reference_is_stored_as_the_reconstruction_gives_it(client, tmp_path):
    r = run(client, name="White panel #1")
    assert r.status_code == 200
    ref = r.get_json()["reference"]
    assert ref["name"] == "White_panel_1" and ref["shape"] == [5, 6, 4] and ref["integration_time_ms"] == 33.4
    assert ref["imaging_method_name"] == "fouriershift" and ref["wavelength_min_nm"] == 400.0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["White_panel_1.json", "White_panel_1.meta.json"]

    stored = utils.load_dict_json(tmp_path / "White_panel_1.json")
    np.testing.assert_array_equal(stored["reconstructed_data"], CUBE)          # not reduced to a spectrum
    assert FakeAcquisition.closed == 1


def test_a_name_that_is_taken_is_refused_and_a_default_name_is_given(client):
    assert run(client, name="ref").status_code == 200
    taken = run(client, name="ref")
    assert taken.status_code == 409 and taken.get_json() == {"error": "exists", "name": "ref"}
    assert run(client).get_json()["reference"]["name"].startswith("reference_")


def test_the_list_is_newest_first_and_the_download_is_the_stored_file(client, tmp_path):
    run(client, name="a")
    run(client, name="b")
    names = [m["name"] for m in client.get("/acquisition/normalisation/list").get_json()["references"]]
    assert sorted(names) == ["a", "b"]
    d = client.get("/acquisition/normalisation/download/a")
    assert d.status_code == 200 and d.data == (tmp_path / "a.json").read_bytes()


def test_a_reference_can_be_deleted_and_names_cannot_escape_the_folder(client, tmp_path):
    run(client, name="gone")
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}")
    for bad in ("../outside", "..%2Foutside", "a/b", ""):
        assert client.post("/acquisition/normalisation/delete", json={"name": bad}).status_code == 404
    assert client.get("/acquisition/normalisation/download/..%2Foutside").status_code == 404
    assert outside.exists()

    assert client.post("/acquisition/normalisation/delete", json={"name": "gone"}).status_code == 200
    assert not (tmp_path / "gone.json").exists() and not (tmp_path / "gone.meta.json").exists()
    assert client.post("/acquisition/normalisation/delete", json={"name": "gone"}).status_code == 404


def test_a_failed_acquisition_leaves_nothing_and_frees_the_hardware(client, tmp_path, monkeypatch):
    class Boom(FakeAcquisition):
        def thread_acquisition(self):
            raise RuntimeError("no spectrometer")

    monkeypatch.setattr(N, "Acquisition", Boom)
    r = run(client, name="bad")
    assert r.status_code == 500 and r.get_json()["message"] == "no spectrometer"
    assert list(tmp_path.iterdir()) == []
    assert tuning.hardware_lock.acquire(blocking=False), "the hardware lock must be released"
    tuning.hardware_lock.release()


def test_a_cancelled_acquisition_saves_nothing(client, tmp_path, monkeypatch):
    class Cancelled(FakeAcquisition):
        def thread_acquisition(self):
            raise AcquisitionCancelled("stop")

    monkeypatch.setattr(N, "Acquisition", Cancelled)
    r = run(client, name="stopped")
    assert r.status_code == 499 and r.get_json()["error"] == "cancelled"
    assert list(tmp_path.iterdir()) == []


def test_it_is_refused_while_the_hardware_is_in_use(client, tmp_path):
    assert tuning.hardware_lock.acquire(blocking=False)
    try:
        r = run(client, name="busy")
    finally:
        tuning.hardware_lock.release()
    assert r.status_code == 409 and r.get_json()["error"] == "busy" and list(tmp_path.iterdir()) == []
