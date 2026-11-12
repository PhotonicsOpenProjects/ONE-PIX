"""ONEPIX_SERVER selects the server that runs the web interface (app/GUI/flask/run.py)."""
import os
import socket
import sys
import threading
import time
import urllib.request

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

import run  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_an_unknown_server_is_refused_with_a_clear_message(monkeypatch):
    monkeypatch.setenv("ONEPIX_SERVER", "gunicorn")
    with pytest.raises(SystemExit, match="werkzeug.*waitress"):
        run.serve(object())


def test_waitress_without_the_package_says_how_to_install_it(monkeypatch):
    monkeypatch.setenv("ONEPIX_SERVER", "waitress")
    monkeypatch.setitem(sys.modules, "waitress", None)
    with pytest.raises(SystemExit, match="pip install waitress"):
        run.serve(object())


def test_waitress_serves_the_interface_and_a_slow_request_is_not_cut(monkeypatch):
    waitress = pytest.importorskip("waitress")
    monkeypatch.setenv("ONEPIX_SERVER", "waitress")
    monkeypatch.setenv("ONEPIX_THREADS", "4")
    monkeypatch.setenv("ONEPIX_CHANNEL_TIMEOUT", "30")
    app = run.create_app()

    @app.route("/slow")
    def slow():
        time.sleep(1.5)                  # stands for /acquisition/run, which answers when the measurement ends
        return "done"

    port = free_port()
    started = []

    def target():
        # waitress.serve blocks: close its server from the test through the trigger it creates
        original = waitress.create_server

        def capture(*a, **kw):
            srv = original(*a, **kw)
            started.append(srv)
            return srv

        monkeypatch.setattr(waitress, "create_server", capture)
        run.serve(app, host="127.0.0.1", port=port)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    for _ in range(100):
        if started:
            break
        time.sleep(0.05)
    assert started, "waitress did not start"

    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                assert urllib.request.urlopen(base + "/logs/", timeout=5).status == 200
                break
            except OSError:
                time.sleep(0.1)
        results = []
        slow_thread = threading.Thread(target=lambda: results.append(urllib.request.urlopen(base + "/slow", timeout=10).read()))
        slow_thread.start()
        time.sleep(0.3)
        # another page is served while the slow request is in progress
        assert urllib.request.urlopen(base + "/logs/", timeout=5).status == 200
        slow_thread.join(10)
        assert results == [b"done"]
    finally:
        started[0].close()
        thread.join(5)
