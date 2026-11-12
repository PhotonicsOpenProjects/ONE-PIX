"""Socket.IO server: no connection without the token, and the instructions that do not need hardware."""
import importlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "websocket_server"))

TOKEN = "ws-test-token"


@pytest.fixture
def server(monkeypatch, tmp_path):
    monkeypatch.setenv("ONEPIX_WS_TOKEN", TOKEN)
    import websocket_server
    module = importlib.reload(websocket_server)           # the token is read when the module is imported
    (tmp_path / "hardware_config.json").write_text(json.dumps({"height": 400, "name": "stub", "ok": False}))
    monkeypatch.setattr(module, "CONF_DIR", str(tmp_path))
    return module


def connect(server, **auth):
    return server.socketio.test_client(server.app, auth=auth or None)


def test_connections_without_the_right_token_are_refused(server):
    assert not connect(server).is_connected()
    assert not connect(server, token="wrong").is_connected()
    assert not connect(server, token="").is_connected()
    assert connect(server, token=TOKEN).is_connected()


def test_without_any_configured_token_every_connection_is_refused(monkeypatch):
    monkeypatch.delenv("ONEPIX_WS_TOKEN", raising=False)
    import websocket_server
    module = importlib.reload(websocket_server)
    assert not module.socketio.test_client(module.app, auth={"token": TOKEN}).is_connected()
    assert not module.socketio.test_client(module.app, auth={"token": ""}).is_connected()


def received(client, name):
    return [m["args"][0] for m in client.get_received() if m["name"] == name]


def test_get_param_reads_a_setting_and_reports_an_unknown_one(server):
    client = connect(server, token=TOKEN)
    client.emit("instruction", {"action": "get_param", "key": "height"})
    assert received(client, "param_data") == [{"key": "height", "value": 400, "file": "hardware_config.json"}]
    client.emit("instruction", {"action": "get_param", "key": "nope"})
    assert "introuvable" in received(client, "erreur")[0]["message"]


def test_update_param_casts_like_the_existing_value_and_writes_the_file(server, tmp_path):
    client = connect(server, token=TOKEN)
    client.emit("instruction", {"action": "update_param", "key": "height", "value": "500"})
    client.emit("instruction", {"action": "update_param", "key": "ok", "value": "true"})
    saved = json.loads((tmp_path / "hardware_config.json").read_text())
    assert saved == {"height": 500, "name": "stub", "ok": True}
    assert [m["key"] for m in received(client, "config_updated")] == ["height", "ok"]
    assert [p for p in os.listdir(tmp_path) if p.endswith(".tmp")] == []


def test_a_value_of_the_wrong_type_is_reported_and_the_file_is_not_changed(server, tmp_path):
    before = (tmp_path / "hardware_config.json").read_text()
    client = connect(server, token=TOKEN)
    client.emit("instruction", {"action": "update_param", "key": "height", "value": "tall"})
    assert received(client, "erreur") and (tmp_path / "hardware_config.json").read_text() == before


def test_an_unknown_instruction_and_a_measurement_in_progress_are_answered(server):
    client = connect(server, token=TOKEN)
    client.emit("instruction", {"action": "reboot"})
    assert "inconnue" in received(client, "erreur")[0]["message"]

    assert server._measure_lock.acquire(blocking=False)
    try:
        client.emit("instruction", {"action": "mesure"})
    finally:
        server._measure_lock.release()
    assert "déjà en cours" in received(client, "erreur")[0]["message"]
