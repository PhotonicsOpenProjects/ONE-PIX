"""Data page: only JSON files are accepted, and file names cannot leave the measure folder."""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

from blueprints.data_manager import routes  # noqa: E402
from run import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    folder = tmp_path / "measure"
    folder.mkdir()
    monkeypatch.setattr(routes, "SAVE_PATH", folder)
    return create_app().test_client(), folder


def upload(client, name, content=b"{}"):
    return client.post("/data_manager/upload", data={"files": (io.BytesIO(content), name)})


def test_only_json_files_are_stored(client):
    c, folder = client
    assert upload(c, "reconstruction_results_x.json").status_code == 200
    r = upload(c, "notes.txt")
    assert r.get_json()["uploaded"] == []
    assert sorted(p.name for p in folder.iterdir()) == ["reconstruction_results_x.json"]


@pytest.mark.parametrize("name", ["../../evil.json", "..\\..\\evil.json", "/etc/evil.json", "a/b/evil.json"])
def test_a_file_name_cannot_leave_the_measure_folder(client, name, tmp_path):
    c, folder = client
    upload(c, name)
    assert not (tmp_path / "evil.json").exists() and not (tmp_path.parent / "evil.json").exists()
    assert all(p.parent == folder for p in folder.rglob("*") if p.is_file())


def test_listing_shows_json_files_and_their_kind(client):
    c, folder = client
    (folder / "reconstruction_results_a.json").write_text("{}")
    (folder / "analysis_b.json").write_text("{}")
    (folder / "readme.txt").write_text("x")
    files = {f["name"]: f["type"] for f in c.get("/data_manager/files").get_json()}
    assert files == {"reconstruction_results_a.json": "reconstruction", "analysis_b.json": "analysis"}


def test_delete_stays_inside_the_folder(client, tmp_path):
    c, folder = client
    outside = tmp_path / "keep.json"
    outside.write_text("{}")
    (folder / "x.json").write_text("{}")
    r = c.post("/data_manager/delete", json={"files": ["../keep.json", "x.json", "missing.json"]})
    assert r.get_json()["deleted"] == ["x.json"] and outside.exists() and not (folder / "x.json").exists()
