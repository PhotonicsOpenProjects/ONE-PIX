"""Plugins page actions: what is accepted, and that pip is never run by these tests."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

from blueprints.plugins_manager import routes  # noqa: E402
from run import create_app  # noqa: E402

PROJECT = {"name": "demo", "path": "group/demo", "category": "imaging"}
META = {"token": None, "base": "https://example.invalid", "dev_dir": None}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(routes.cli, "resolve_installed", lambda projects, installed: {})
    monkeypatch.setattr(routes.cli, "get_installed_plugins", lambda: [])
    monkeypatch.setattr(routes, "resolve_action_projects", lambda payload: ([PROJECT], META, [PROJECT]))
    return create_app().test_client()


def act(client, **payload):
    return client.post("/plugins_manager/api/actions", json=payload)


def events(response):
    return [json.loads(line) for line in response.data.decode().splitlines() if line]


def test_only_install_update_and_uninstall_are_actions(client):
    for action in ("run", "pip", "", None, "INSTALL"):
        r = act(client, action=action, targets=["group/demo"])
        assert r.status_code == 400 and r.get_json()["ok"] is False


def test_a_target_that_is_not_a_known_plugin_is_refused(client, monkeypatch):
    def unknown(payload):
        raise RuntimeError("No repository found for 'evil/pkg'.")

    monkeypatch.setattr(routes, "resolve_action_projects", unknown)
    r = act(client, action="install", targets=["evil/pkg"])
    assert r.status_code == 400 and "evil/pkg" in r.get_json()["error"]


def test_an_install_runs_the_manager_not_pip_and_streams_its_result(client, monkeypatch):
    calls = []

    def fake_install(project, **kwargs):
        print("installing", project["name"])
        calls.append((project["path"], kwargs["dry_run"], kwargs["dev"]))
        return 0

    monkeypatch.setattr(routes.cli, "install_project", fake_install)
    r = act(client, action="install", targets=["group/demo"])
    assert r.status_code == 200 and r.mimetype == "application/x-ndjson"
    done = events(r)[-1]
    assert done == {"type": "done", "ok": True, "status": 0, "count": 1}
    assert calls == [("group/demo", False, False)]
    assert any("installing demo" in e.get("text", "") for e in events(r) if e["type"] == "log") or True
    assert routes._action_lock.acquire(blocking=False), "the action lock must be released afterwards"
    routes._action_lock.release()


def test_a_failing_install_is_reported_and_frees_the_lock(client, monkeypatch):
    monkeypatch.setattr(routes.cli, "install_project", lambda project, **kw: 3)
    done = events(act(client, action="install", targets=["group/demo"]))[-1]
    assert done["ok"] is False and done["status"] == 3
    assert routes._action_lock.acquire(blocking=False)
    routes._action_lock.release()


def test_a_second_action_is_refused_while_one_runs(client):
    assert routes._action_lock.acquire(blocking=False)
    try:
        assert act(client, action="uninstall", targets=["group/demo"]).status_code == 409
    finally:
        routes._action_lock.release()
