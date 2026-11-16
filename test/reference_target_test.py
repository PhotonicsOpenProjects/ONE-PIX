"""The reflectance of the reference target is folded into the saved reference spectrum."""
import io
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

from blueprints.analysis import reference_target as rt  # noqa: E402
from blueprints.analysis import routes  # noqa: E402
from run import create_app  # noqa: E402

WL = np.array([400.0, 500.0, 600.0, 700.0])


# ---- parsing the calibration table

def test_a_csv_with_a_header_is_read_and_percent_becomes_a_fraction():
    wl, r = rt.parse_table("wavelength_nm,reflectance_pct\n400,90\n500,95\n600,99\n")
    assert wl.tolist() == [400, 500, 600]
    assert r.tolist() == pytest.approx([0.90, 0.95, 0.99])


def test_fractions_are_kept_and_separators_can_be_tabs_or_semicolons():
    wl, r = rt.parse_table("# Spectralon\n400\t0.90\n500;0.95\n600 0.99\n")
    assert r.tolist() == pytest.approx([0.90, 0.95, 0.99])


def test_an_unsorted_table_is_sorted_by_wavelength():
    wl, r = rt.parse_table("600 0.6\n400 0.4\n500 0.5\n")
    assert wl.tolist() == [400, 500, 600]
    assert r.tolist() == pytest.approx([0.4, 0.5, 0.6])


def test_a_json_table_is_read():
    text = json.dumps({"wavelengths": [400, 800], "reflectance": [0.5, 0.7]})
    wl, r = rt.parse_table(text)
    assert wl.tolist() == [400, 800] and r.tolist() == pytest.approx([0.5, 0.7])


@pytest.mark.parametrize("text", [
    "", "   ", "a,b\nc,d\n", "400 0.9\n", "400 0.9\n400 0.8\n", "400 0\n500 0.5\n",
    "400 -0.1\n500 0.5\n", '{"wavelengths": [1, 2]}', '{"wavelengths": [1], "reflectance": [1, 2]}',
])
def test_a_table_that_cannot_be_used_is_refused_with_a_message(text):
    with pytest.raises(ValueError):
        rt.parse_table(text)


# ---- the reflectance on the measurement's wavelengths

def test_a_lambertian_target_is_the_same_everywhere():
    r = rt.target_reflectance({"mode": "lambertian", "percent": 50}, WL)
    assert r.tolist() == [0.5] * 4


@pytest.mark.parametrize("percent", [0, -3, 101, "abc", None, float("nan")])
def test_a_lambertian_percentage_out_of_range_is_refused(percent):
    with pytest.raises(ValueError):
        rt.target_reflectance({"mode": "lambertian", "percent": percent}, WL)


def test_a_table_is_interpolated_on_the_measurement_wavelengths():
    target = {"mode": "table", "wavelengths": [300, 800], "reflectance": [0.3, 0.8]}
    assert rt.target_reflectance(target, WL).tolist() == pytest.approx([0.4, 0.5, 0.6, 0.7])


def test_a_table_that_does_not_cover_the_measurement_is_refused_not_extrapolated():
    target = {"mode": "table", "wavelengths": [450, 800], "reflectance": [0.3, 0.8]}
    with pytest.raises(ValueError, match="450-800"):
        rt.target_reflectance(target, WL)


def test_no_target_means_relative_reflectance():
    assert rt.target_reflectance(None, WL) is None
    assert rt.target_reflectance({"mode": "none"}, WL) is None
    spectrum, info = rt.apply_target([1, 2, 3, 4], WL, None)
    assert spectrum.tolist() == [1, 2, 3, 4] and info is None


# ---- end to end with the reflectance_normalization plugin

def test_the_plugin_returns_an_absolute_reflectance(tmp_path, monkeypatch):
    from basic_treatments import reflectance_normalization

    monkeypatch.setattr(routes, "get_reference_dir", lambda: tmp_path)
    measured_reference = np.array([100.0, 200.0, 400.0, 800.0])
    path = routes.save_reference_spectrum(
        measured_reference, WL, {"mode": "lambertian", "percent": 50}
    )
    saved = json.loads(path.read_text())
    assert saved["target"] == {"mode": "lambertian", "percent": 50.0}

    # A sample that returns half of what the 50 % target returns: 25 % reflectance.
    sample = measured_reference / 2
    reflectance, _ = reflectance_normalization.transform(sample, WL, reference_path=str(path))
    assert reflectance == pytest.approx([0.25] * 4)


def test_without_a_target_the_reference_file_is_what_it_always_was(tmp_path, monkeypatch):
    monkeypatch.setattr(routes, "get_reference_dir", lambda: tmp_path)
    path = routes.save_reference_spectrum(np.array([1.0, 2.0, 3.0, 4.0]), WL)
    assert json.loads(path.read_text()) == {"wavelengths": WL.tolist(), "spectrum": [1, 2, 3, 4]}


# ---- the upload route

@pytest.fixture
def client():
    return create_app().test_client()


def upload(client, text, name="target.csv"):
    return client.post(
        "/analysis/reference/target_table",
        data={"file": (io.BytesIO(text.encode()), name)},
        content_type="multipart/form-data",
    )


def test_uploading_a_table_returns_it_parsed(client):
    response = upload(client, "400 90\n800 70\n")
    assert response.status_code == 200
    body = response.get_json()
    assert body["wavelengths"] == [400, 800]
    assert body["reflectance"] == pytest.approx([0.9, 0.7])
    assert (body["n_points"], body["min_nm"], body["max_nm"]) == (2, 400, 800)


def test_uploading_nothing_or_rubbish_is_a_400(client):
    assert client.post("/analysis/reference/target_table").status_code == 400
    response = upload(client, "not a table")
    assert response.status_code == 400 and response.get_json()["error"]


def test_a_huge_upload_is_a_413(client):
    big = "400 0.5\n" * (routes.MAX_TARGET_TABLE_BYTES // 8 + 10)
    assert upload(client, big).status_code == 413
