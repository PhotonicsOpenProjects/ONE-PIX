"""Requests made by other web pages are refused, and uploads are capped (app/GUI/flask/request_guard.py)."""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app", "GUI", "flask"))

import request_guard  # noqa: E402
from blueprints.acquisition import tuning  # noqa: E402
from blueprints.data_manager import routes as data_routes  # noqa: E402
from run import create_app  # noqa: E402

SAVE = "/acquisition/hardware/tuning/stop"      # a POST that changes state and is harmless to call
RUN = "/acquisition/run"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("ONEPIX_TRUSTED_ORIGINS", raising=False)
    monkeypatch.delenv("ONEPIX_MAX_UPLOAD_MB", raising=False)
    return create_app().test_client()


@pytest.mark.parametrize("headers", [
    {"Sec-Fetch-Site": "cross-site"},
    {"Sec-Fetch-Site": "same-site"},                                   # a sibling sub-domain is another origin
    {"Origin": "http://evil.example"},
    {"Origin": "null"},
    {"Referer": "https://evil.example/page.html"},
    {"Origin": "http://localhost.evil.example"},
])
def test_a_post_from_another_site_is_refused(client, headers):
    r = client.post(SAVE, headers=headers)
    assert r.status_code == 403 and r.get_json()["error"] == "cross-site request refused"


@pytest.mark.parametrize("headers", [
    {},                                                                 # curl, a script: not a browser
    {"Sec-Fetch-Site": "same-origin"},
    {"Sec-Fetch-Site": "none"},
    {"Origin": "http://localhost"},                                    # the test client's host
    {"Referer": "http://localhost/acquisition/hardware"},
])
def test_a_post_from_the_interface_or_a_script_goes_through(client, headers):
    assert client.post(SAVE, headers=headers).status_code != 403


def test_get_that_starts_an_acquisition_is_protected_like_a_post(client):
    assert client.get(RUN, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get(RUN, headers={"Origin": "http://evil.example"}).status_code == 403
    # a same-origin request is not refused by the guard: it reaches the route, which finds the hardware
    # busy here (the lock is held), so no acquisition starts
    assert tuning.hardware_lock.acquire(blocking=False)
    try:
        assert client.get(RUN, headers={"Sec-Fetch-Site": "same-origin"}).status_code == 409
    finally:
        tuning.hardware_lock.release()


def test_ordinary_reads_from_another_site_are_not_blocked(client):
    # a page of another site can already not read the response; blocking would only break links
    assert client.get("/logs/", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 200


def test_trusted_origins_allow_a_reverse_proxy_host(monkeypatch):
    monkeypatch.setenv("ONEPIX_TRUSTED_ORIGINS", "onepix.lab.example, proxy.example:8443")
    c = create_app().test_client()
    assert c.post(SAVE, headers={"Origin": "https://onepix.lab.example"}).status_code != 403
    assert c.post(SAVE, headers={"Origin": "https://proxy.example:8443"}).status_code != 403
    assert c.post(SAVE, headers={"Origin": "https://evil.example"}).status_code == 403


def test_uploads_are_capped_and_the_error_says_the_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("ONEPIX_MAX_UPLOAD_MB", "1")
    monkeypatch.setattr(data_routes, "SAVE_PATH", tmp_path)
    c = create_app().test_client()

    ok = c.post("/data_manager/upload", data={"files": (io.BytesIO(b"{}" + b" " * 1000), "small.json")})
    assert ok.status_code == 200 and (tmp_path / "small.json").exists()

    big = c.post("/data_manager/upload", data={"files": (io.BytesIO(b" " * (2 * 1024 * 1024)), "big.json")})
    assert big.status_code == 413 and big.get_json() == {"error": "file too large", "max_mb": 1}
    assert not (tmp_path / "big.json").exists()


def test_the_default_limit_and_bad_values():
    assert request_guard.max_upload_bytes({}) == 1024 * 1024 * 1024
    assert request_guard.max_upload_bytes({"ONEPIX_MAX_UPLOAD_MB": "200"}) == 200 * 1024 * 1024
    assert request_guard.max_upload_bytes({"ONEPIX_MAX_UPLOAD_MB": "many"}) == 1024 * 1024 * 1024
    assert request_guard.max_upload_bytes({"ONEPIX_MAX_UPLOAD_MB": "0"}) == 1024 * 1024


# ---------------------------------------------------------------- headers and redirects

def test_every_response_carries_the_security_headers(client):
    for path in ("/logs/", "/acquisition/hardware", "/logs/api/tail", "/does-not-exist"):
        h = client.get(path).headers
        assert h["X-Content-Type-Options"] == "nosniff"
        assert h["X-Frame-Options"] == "SAMEORIGIN"
        assert h["Content-Security-Policy"] == "frame-ancestors 'self'"
        assert h["Referrer-Policy"] == "same-origin"


def test_the_language_choice_returns_to_this_site_only(client):
    back = client.get("/set-language/fr", headers={"Referer": "http://localhost/acquisition/hardware"})
    assert back.status_code == 302 and back.headers["Location"] == "http://localhost/acquisition/hardware"
    assert "onepix_lang=fr" in back.headers["Set-Cookie"]

    for referer in ("https://evil.example/page", "//evil.example/", ""):
        r = client.get("/set-language/en", headers={"Referer": referer})
        assert "evil.example" not in r.headers["Location"], referer
        assert r.headers["Location"].endswith("/acquisition/")
