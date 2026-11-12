"""Protection of the web interface against requests made by other web pages, and against oversized uploads.

The interface has no sign-in: anyone who can reach it can use it. What this module stops is a *web
page of another site* making the user's browser act on it (cross-site request forgery): such a page
could otherwise start an acquisition (an image tag is enough for a GET) or rewrite the hardware
configuration (a form is enough for a POST).

A request that changes something - a POST, PUT, PATCH or DELETE, and the few GET routes that start
something (STATE_CHANGING_GET) - is refused when the browser says it comes from another site:

  * Sec-Fetch-Site, sent by every current browser, must be same-origin (or none: typed address, bookmark);
  * otherwise the Origin (or Referer) host must be the host of the request;
  * a request without any of these headers is not a browser (curl, a Python script): a web page cannot
    forge it, so it goes through.

ONEPIX_TRUSTED_ORIGINS adds hosts allowed in Origin/Referer (comma separated host[:port]), for a reverse
proxy that rewrites the Host header. A DNS-rebinding page, whose name resolves to this machine, looks
same-origin to these checks: use the interface on a network you trust.

ONEPIX_MAX_UPLOAD_MB (default 1024) caps the size of an upload.

Every response also carries headers that make the browser stricter: the interface cannot be shown in a
frame of another site (a page could otherwise overlay it and have a button clicked), a file is not
interpreted as another type than the one announced, and the address of a page is not sent to other sites.
There is no Content-Security-Policy: the pages use inline scripts and styles.
"""
import os
from urllib.parse import urlsplit

from flask import jsonify, request

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# GET routes that start something, protected like a POST
STATE_CHANGING_GET = {"acquisition.run_acquisition"}

DEFAULT_MAX_UPLOAD_MB = 1024

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Content-Security-Policy": "frame-ancestors 'self'",
    "Referrer-Policy": "same-origin",
}


def same_site_target(target, req):
    """`target` (a Referer) if it is a page of this site, else None: a redirect must never leave it."""
    if not target:
        return None
    return target if urlsplit(target).netloc == req.host else None


def trusted_hosts(environ=None):
    environ = os.environ if environ is None else environ
    return {h.strip() for h in environ.get("ONEPIX_TRUSTED_ORIGINS", "").split(",") if h.strip()}


def comes_from_another_site(req, trusted=()):
    """True when the browser says `req` was triggered by a page of another site."""
    site = req.headers.get("Sec-Fetch-Site")
    if site is not None:
        return site not in ("same-origin", "none")

    origin = req.headers.get("Origin") or req.headers.get("Referer")
    if origin is None:
        return False                      # not a browser
    if origin == "null":
        return True                       # sandboxed frame, or the browser hides it
    host = urlsplit(origin).netloc
    return host != req.host and host not in trusted


def max_upload_bytes(environ=None):
    environ = os.environ if environ is None else environ
    try:
        megabytes = int(environ.get("ONEPIX_MAX_UPLOAD_MB", DEFAULT_MAX_UPLOAD_MB))
    except ValueError:
        megabytes = DEFAULT_MAX_UPLOAD_MB
    return max(1, megabytes) * 1024 * 1024


def init_guard(app):
    app.config["MAX_CONTENT_LENGTH"] = max_upload_bytes()
    trusted = trusted_hosts()

    @app.before_request
    def _refuse_cross_site_requests():
        changes_something = request.method not in SAFE_METHODS or request.endpoint in STATE_CHANGING_GET
        if changes_something and comes_from_another_site(request, trusted):
            return jsonify({"error": "cross-site request refused"}), 403
        return None

    @app.after_request
    def _add_security_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    @app.errorhandler(413)
    def _too_large(_error):
        return jsonify({
            "error": "file too large",
            "max_mb": app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
        }), 413
