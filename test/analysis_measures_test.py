"""The Analysis page lists the measurements newest first."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

from blueprints.analysis import routes  # noqa: E402
from run import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(routes, "get_measure_path", lambda: tmp_path)
    return create_app().test_client(), tmp_path


def make(folder, name, age_s):
    path = folder / name
    path.write_text("{}")
    stamp = 1_800_000_000 - age_s
    os.utime(path, (stamp, stamp))


def test_measurements_are_listed_newest_first_whatever_their_names(client):
    c, folder = client
    # dd_mm_yyyy names: sorted by name, 31_10 would come after 02_11 and 12_11 before 02_11
    make(folder, "reconstruction_results_31_10_2026_09-00-00.json", 900)
    make(folder, "reconstruction_results_02_11_2026_09-00-00.json", 600)
    make(folder, "analysis_results_12_11_2026_09-00-00.json", 100)
    make(folder, "reconstruction_results_05_11_2026_09-00-00.json", 300)
    assert c.get("/analysis/measures").get_json() == [
        "analysis_results_12_11_2026_09-00-00.json",
        "reconstruction_results_05_11_2026_09-00-00.json",
        "reconstruction_results_02_11_2026_09-00-00.json",
        "reconstruction_results_31_10_2026_09-00-00.json",
    ]


def test_same_time_is_ordered_by_name_and_other_files_are_ignored(client):
    c, folder = client
    make(folder, "a.json", 10)
    make(folder, "b.json", 10)
    (folder / "notes.txt").write_text("x")
    assert c.get("/analysis/measures").get_json() == ["b.json", "a.json"]


def test_an_empty_or_missing_folder_gives_an_empty_list(client, monkeypatch):
    c, folder = client
    assert c.get("/analysis/measures").get_json() == []
    monkeypatch.setattr(routes, "get_measure_path", lambda: folder / "missing")
    assert c.get("/analysis/measures").get_json() == []
