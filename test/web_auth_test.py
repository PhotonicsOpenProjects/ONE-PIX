"""Access control of the web interface (app/GUI/flask/web_auth.py)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

import web_auth  # noqa: E402
from run import create_app  # noqa: E402

TOKEN = "s3cret-token-for-tests"


@pytest.fixture
def open_client(monkeypatch):
    monkeypatch.delenv("ONEPIX_WEB_TOKEN", raising=False)
    return create_app().test_client()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ONEPIX_WEB_TOKEN", TOKEN)
    app = create_app()
    app.testing = True
    return app.test_client()


def test_without_a_token_the_interface_is_open_as_before(open_client):
    assert open_client.get("/logs/").status_code == 200
    assert open_client.get("/login").status_code == 404


def test_server_listens_on_this_machine_only_by_default():
    assert web_auth.server_settings({}) == ("127.0.0.1", 5000, None)
    assert web_auth.server_settings({"ONEPIX_HOST": "localhost"})[0] == "localhost"
    assert web_auth.server_settings({"ONEPIX_HOST": "::1"})[0] == "::1"


def test_opening_the_network_requires_a_token():
    with pytest.raises(RuntimeError, match="ONEPIX_WEB_TOKEN"):
        web_auth.server_settings({"ONEPIX_HOST": "0.0.0.0"})
    with pytest.raises(RuntimeError):
        web_auth.server_settings({"ONEPIX_HOST": "192.168.1.20", "ONEPIX_WEB_TOKEN": ""})
    assert web_auth.server_settings({"ONEPIX_HOST": "0.0.0.0", "ONEPIX_WEB_TOKEN": TOKEN, "ONEPIX_PORT": "8080"}) \
        == ("0.0.0.0", 8080, TOKEN)
    with pytest.raises(RuntimeError, match="ONEPIX_PORT"):
        web_auth.server_settings({"ONEPIX_PORT": "http"})


def test_requests_without_credentials_are_refused(client):
    page = client.get("/acquisition/hardware", headers={"Accept": "text/html"})
    assert page.status_code == 302 and "/login" in page.headers["Location"]
    # fetch() and scripts get a 401, not a redirect to an HTML page
    assert client.get("/logs/api/tail").status_code == 401
    assert client.post("/acquisition/save/hardware", data={"height": "1"}).status_code == 401
    assert client.get("/acquisition/run").status_code == 401        # an acquisition cannot be started
    assert client.post("/plugins_manager/api/actions", json={"action": "install"}).status_code == 401
    assert client.get("/static/css/design-system.css").status_code == 401


def test_bearer_header_is_accepted_and_a_wrong_one_is_not(client):
    assert client.get("/logs/api/tail", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200
    assert client.get("/logs/api/tail", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/logs/api/tail", headers={"Authorization": TOKEN}).status_code == 401


def test_signing_in_gives_a_strict_cookie_and_access(client, monkeypatch):
    monkeypatch.setattr(web_auth.time, "sleep", lambda s: None)
    bad = client.post("/login", data={"token": "nope"})
    assert bad.status_code == 401 and "onepix_session" not in bad.headers.get("Set-Cookie", "")

    good = client.post("/login", data={"token": TOKEN, "next": "/logs/"})
    assert good.status_code == 302 and good.headers["Location"] == "/logs/"
    cookie = good.headers["Set-Cookie"]
    assert "SameSite=Strict" in cookie and "HttpOnly" in cookie

    assert client.get("/logs/").status_code == 200
    client.get("/logout")
    assert client.get("/logs/api/tail").status_code == 401


def test_sign_in_never_redirects_to_another_site(client, monkeypatch):
    monkeypatch.setattr(web_auth.time, "sleep", lambda s: None)
    for target in ("https://evil.example/", "//evil.example/", "javascript:alert(1)", ""):
        r = client.post("/login", data={"token": TOKEN, "next": target})
        assert r.headers["Location"] == "/", target
