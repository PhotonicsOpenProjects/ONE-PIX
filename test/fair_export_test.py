"""FAIR export: every format can be read back, the package describes itself and checks out."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from onepix import export, fair, utils

ROWS, COLS, BANDS = 5, 6, 8
WAVELENGTHS = np.linspace(400.0, 750.0, BANDS)


@pytest.fixture
def config(tmp_path, monkeypatch):
    path = tmp_path / "fair_config.json"
    monkeypatch.setattr(fair, "FAIR_CONFIG_PATH", path)
    return fair.save_fair_config({
        "creator_name": "Ada Lovelace", "creator_orcid": "0000-0002-1825-0097",
        "affiliation": "Analytical Engine Lab", "contact_email": "ada@example.org",
        "project": "test", "keywords": "spectra, test", "license": "CC-BY-4.0",
    })


def make_result(tmp_path, with_fair=False, cube=True):
    metadata = {
        "imaging_method_name": "fouriershift",
        "acquisition_datetime": "2026-11-10T12:00:00",
        "hardware": {"spectrometer_name": "stub", "camera_name": "stubcam", "wl_lim": [400, 750],
                     "integration_time_ms": 10.0, "proj_position": None},
    }
    if with_fair:
        metadata["fair"] = fair.fair_block(fair.load_fair_config())
    result = {
        "metadata": metadata,
        "wavelengths": WAVELENGTHS.astype(np.float32),
        "drift_percent": {"offset": 0.5, "gain": 1.5},
        "saturation_suspected": False,
        "result2plot": np.zeros((ROWS, COLS, 3), np.uint8),
    }
    if cube:
        result["reconstructed_data"] = np.random.default_rng(0).random((ROWS, COLS, BANDS)).astype(np.float32)
    path = tmp_path / "reconstruction_results_test.json"
    utils.save_dict_json(result, path)
    return path, result


def test_every_format_round_trips(tmp_path, config):
    src, result = make_result(tmp_path)
    out = export.export_dataset(src, list(export.FORMATS), tmp_path / "out", config)
    assert out["skipped"] == {}
    folder, cube = out["folder"], result["reconstructed_data"]

    import h5py
    with h5py.File(folder / "reconstruction_results_test.h5") as f:
        np.testing.assert_array_equal(f["datacube"][:], cube)
        assert f["wavelength"].attrs["units"] == "nm"
        assert [d.label for d in f["datacube"].dims] == ["y", "x", "wavelength"]
        assert f.attrs["license"] == "CC-BY-4.0"
        assert json.loads(f.attrs["metadata_json"])["creator"]["name"] == "Ada Lovelace"

    npz = np.load(folder / "reconstruction_results_test.npz")
    np.testing.assert_array_equal(npz["datacube"], cube)
    assert json.loads(str(npz["metadata_json"]))["instrument"]["imaging_method"] == "fouriershift"

    from scipy.io import loadmat
    mat = loadmat(folder / "reconstruction_results_test.mat", simplify_cells=True)
    np.testing.assert_array_equal(mat["datacube"], cube)
    assert mat["metadata"]["license"]["id"] == "CC-BY-4.0"

    import spectral
    img = spectral.open_image(str(folder / "reconstruction_results_test.hdr"))
    assert img.shape == (ROWS, COLS, BANDS)
    assert img.metadata["wavelength units"] == "Nanometers"
    np.testing.assert_allclose(img.bands.centers, WAVELENGTHS, atol=1e-3)
    np.testing.assert_array_equal(np.asarray(img.load()), cube)

    import tifffile
    with tifffile.TiffFile(folder / "reconstruction_results_test.tif") as tif:
        assert tif.series[0].shape == (BANDS, ROWS, COLS)
        assert tif.imagej_metadata["Labels"][0] == "400.0 nm"

    assert (folder / "reconstruction_results_test.json").read_bytes() == src.read_bytes()


def test_package_describes_itself_and_checks_out(tmp_path, config):
    src, _ = make_result(tmp_path)
    folder = export.export_dataset(src, ["hdf5", "npz"], tmp_path / "out", config)["folder"]

    crate = json.loads((folder / "ro-crate-metadata.json").read_text())
    graph = {e["@id"]: e for e in crate["@graph"]}
    root = graph["./"]
    assert crate["@context"].startswith("https://w3id.org/ro/crate/")
    for required in ("name", "description", "datePublished", "license", "identifier"):
        assert root[required]
    assert graph["ro-crate-metadata.json"]["about"] == {"@id": "./"}
    assert graph[root["creator"]["@id"]]["name"] == "Ada Lovelace"
    for part in root["hasPart"]:
        assert (folder / part["@id"]).exists()
        assert graph[part["@id"]]["sha256"] == hashlib.sha256((folder / part["@id"]).read_bytes()).hexdigest()

    for line in (folder / "checksums.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest

    readme = (folder / "README.md").read_text()
    assert "Ada Lovelace" in readme and "h5py" in readme and "CC-BY-4.0" in readme


def test_identifier_is_stable_for_old_files_and_recorded_for_new_ones(tmp_path, config):
    old, _ = make_result(tmp_path)
    a, b = export.load_dataset(old, config), export.load_dataset(old, config)
    assert a.fair["identifier"] == b.fair["identifier"] and a.fair["identifier"].startswith("urn:uuid:")
    assert a.fair["recorded_at"] == "export"

    new_dir = tmp_path / "new"
    new_dir.mkdir()
    new, _ = make_result(new_dir, with_fair=True)
    ds = export.load_dataset(new, config)
    assert "recorded_at" not in ds.fair
    assert ds.fair["software"]["python"] == sys.version.split()[0]
    assert ds.fair["identifier"] != a.fair["identifier"]


def test_result_without_datacube_skips_envi_and_tiff_only(tmp_path, config):
    src, _ = make_result(tmp_path, cube=False)
    out = export.export_dataset(src, ["hdf5", "envi", "tiff", "npz"], tmp_path / "out", config)
    assert set(out["skipped"]) == {"envi", "tiff"}
    assert (out["folder"] / "reconstruction_results_test.h5").exists()
    assert (out["folder"] / "reconstruction_results_test.npz").exists()


def test_unknown_format_is_reported_not_fatal(tmp_path, config):
    src, _ = make_result(tmp_path)
    out = export.export_dataset(src, ["hdf5", "docx"], tmp_path / "out", config)
    assert out["skipped"] == {"docx": "unknown format"}


def test_config_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(fair, "FAIR_CONFIG_PATH", tmp_path / "c.json")
    for bad, why in (({"creator_orcid": "1234"}, "orcid"), ({"contact_email": "nope"}, "email"),
                     ({"license": "WTFPL"}, "license")):
        with pytest.raises(ValueError, match=why):
            fair.save_fair_config(bad)
    saved = fair.save_fair_config({"keywords": " a , b ,, "})
    assert saved["keywords"] == ["a", "b"] and fair.load_fair_config()["keywords"] == ["a", "b"]
    assert fair.load_fair_config()["license"] == "CC-BY-4.0"


def test_data_manager_routes(tmp_path, config, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "GUI" / "flask"))
    import io, zipfile
    from blueprints.data_manager import routes
    import run

    src, _ = make_result(tmp_path)
    monkeypatch.setattr(routes, "SAVE_PATH", tmp_path)
    client = run.create_app().test_client()

    assert {f["id"] for f in client.get("/data_manager/fair/formats").json} == set(export.FORMATS)
    assert client.get("/data_manager/fair/config").json["config"]["creator_name"] == "Ada Lovelace"
    assert client.post("/data_manager/fair/config", json={"creator_orcid": "x"}).json["error"] == "orcid"

    r = client.post("/data_manager/export", json={"files": [src.name], "formats": ["hdf5", "envi"]})
    assert r.status_code == 200 and json.loads(r.headers["X-Export-Skipped"]) == {}
    names = zipfile.ZipFile(io.BytesIO(r.data)).namelist()
    assert "reconstruction_results_test/reconstruction_results_test.h5" in names
    assert "reconstruction_results_test/ro-crate-metadata.json" in names

    assert client.post("/data_manager/export", json={"files": ["../etc/passwd"], "formats": ["hdf5"]}).status_code == 404
    assert client.post("/data_manager/export", json={"files": [src.name], "formats": ["exe"]}).status_code == 400
    assert client.post("/data_manager/export", json={"files": [], "formats": ["hdf5"]}).status_code == 400
