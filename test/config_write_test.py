"""Configuration files are written atomically and a partial save keeps the other keys."""
import json
import os
import stat
import sys

import pytest

from onepix import utils

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))


def leftovers(folder):
    return [p for p in os.listdir(folder) if p.endswith(".tmp")]


# ---------------------------------------------------------------- write_json_atomic

def test_writes_the_json_and_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "conf.json"
    utils.write_json_atomic(path, {"a": 1, "é": "x"}, indent=4)
    assert json.loads(path.read_text()) == {"a": 1, "é": "x"}
    assert '    "a"' in path.read_text()                       # indent honoured
    assert "\\u00e9" in path.read_text()                       # ensure_ascii defaults to json.dump's
    utils.write_json_atomic(path, {"é": "x"}, ensure_ascii=False)
    assert "é" in path.read_text()
    assert leftovers(tmp_path) == []


def test_permissions_of_an_existing_file_are_kept_and_a_new_one_is_not_private(tmp_path):
    path = tmp_path / "conf.json"
    path.write_text("{}")
    os.chmod(path, 0o664)
    utils.write_json_atomic(path, {"a": 1})
    assert stat.S_IMODE(path.stat().st_mode) == 0o664

    fresh = tmp_path / "new.json"
    utils.write_json_atomic(fresh, {"a": 1})
    assert stat.S_IMODE(fresh.stat().st_mode) & 0o044, "a new file must be readable like json.dump's"


def test_an_object_that_cannot_be_serialised_leaves_the_file_untouched(tmp_path):
    path = tmp_path / "conf.json"
    path.write_text('{"keep": true}')
    with pytest.raises(TypeError):
        utils.write_json_atomic(path, {"bad": object()})
    assert json.loads(path.read_text()) == {"keep": True}
    assert leftovers(tmp_path) == []


def test_a_failure_while_replacing_leaves_the_previous_file_and_no_temporary_file(tmp_path, monkeypatch):
    path = tmp_path / "conf.json"
    path.write_text('{"keep": true}')

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(utils.os, "replace", boom)
    with pytest.raises(OSError):
        utils.write_json_atomic(path, {"new": 1})
    assert json.loads(path.read_text()) == {"keep": True}
    assert leftovers(tmp_path) == []


def test_a_symbolic_link_is_written_through(tmp_path):
    target = tmp_path / "real.json"
    target.write_text("{}")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    utils.write_json_atomic(link, {"a": 1})
    assert link.is_symlink() and json.loads(target.read_text()) == {"a": 1}


# ---------------------------------------------------------------- the settings routes

@pytest.fixture
def client_and_file(tmp_path, monkeypatch):
    from blueprints.acquisition import controllers as ctl
    from run import create_app

    path = tmp_path / "hardware_config.json"
    path.write_text(json.dumps({"name_spectro": "stub", "height": 400, "width": 800, "wl_lim": [350, 900],
                                "max_gray_level": 100, "dark": False}))
    original = ctl.get_config_path
    monkeypatch.setattr(ctl, "get_config_path", lambda cat: str(path) if cat == "hardware" else original(cat))
    return create_app().test_client(), path


def test_a_partial_save_keeps_the_other_settings(client_and_file):
    client, path = client_and_file
    r = client.post("/acquisition/save/hardware", data={"height": "500"})
    assert r.status_code == 302
    saved = json.loads(path.read_text())
    assert saved["height"] == 500                                   # cast like the existing value
    assert saved["width"] == 800 and saved["max_gray_level"] == 100 and saved["name_spectro"] == "stub"
    assert saved["wl_lim"] == [350, 900] and saved["dark"] is False


def test_a_new_key_is_added_and_json_values_are_parsed(client_and_file):
    client, path = client_and_file
    client.post("/acquisition/save/hardware", data={"extra": "[1, 2]", "label": "plain text"})
    saved = json.loads(path.read_text())
    assert saved["extra"] == [1, 2] and saved["label"] == "plain text" and saved["height"] == 400


def test_an_unknown_category_is_not_found_instead_of_an_error(client_and_file):
    client, path = client_and_file
    before = path.read_text()
    assert client.post("/acquisition/save/unknown", data={"x": "1"}).status_code == 404
    assert path.read_text() == before


def test_a_crash_while_saving_leaves_the_configuration_intact(client_and_file, monkeypatch):
    client, path = client_and_file
    before = path.read_text()
    monkeypatch.setattr(utils.os, "replace", lambda src, dst: (_ for _ in ()).throw(OSError("power cut")))
    client.application.testing = False
    r = client.post("/acquisition/save/hardware", data={"height": "999"})
    assert r.status_code == 500
    assert path.read_text() == before and leftovers(path.parent) == []
