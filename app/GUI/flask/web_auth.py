"""Access control of the web interface.

The interface can start an acquisition, rewrite the hardware configuration, read and delete the
measurements and install plugins: it must not be open to a network by accident.

    ONEPIX_HOST       address the server listens on (default 127.0.0.1: this machine only)
    ONEPIX_PORT       port (default 5000)
    ONEPIX_WEB_TOKEN  shared secret

Listening on another address than loopback requires the token: the server refuses to start without
it. When a token is set, every request must carry it, either as the session cookie obtained by signing
in on /login or as an `Authorization: Bearer <token>` header (scripts). The session cookie is
`SameSite=Strict`, so a page of another site cannot make the browser act on the interface.
"""
import hmac
import ipaddress
import os
import secrets
import time
from urllib.parse import urlsplit

from flask import Blueprint, jsonify, redirect, render_template_string, request, session, url_for

from i18n import current_lang, register_translations, t

LOGIN_PATH = "/login"

TRANSLATIONS = {
    "en": {"auth.title": "Sign in", "auth.prompt": "Access token", "auth.submit": "Sign in",
           "auth.error": "Invalid token.", "auth.logout": "Sign out",
           "auth.hint": "Set by ONEPIX_WEB_TOKEN on the machine running ONE-PIX."},
    "fr": {"auth.title": "Connexion", "auth.prompt": "Jeton d'accès", "auth.submit": "Se connecter",
           "auth.error": "Jeton invalide.", "auth.logout": "Se déconnecter",
           "auth.hint": "Défini par ONEPIX_WEB_TOKEN sur la machine qui exécute ONE-PIX."},
    "es": {"auth.title": "Iniciar sesión", "auth.prompt": "Token de acceso", "auth.submit": "Entrar",
           "auth.error": "Token no válido.", "auth.logout": "Cerrar sesión",
           "auth.hint": "Definido por ONEPIX_WEB_TOKEN en la máquina que ejecuta ONE-PIX."},
    "de": {"auth.title": "Anmelden", "auth.prompt": "Zugriffstoken", "auth.submit": "Anmelden",
           "auth.error": "Ungültiges Token.", "auth.logout": "Abmelden",
           "auth.hint": "Festgelegt durch ONEPIX_WEB_TOKEN auf dem Rechner, auf dem ONE-PIX läuft."},
}

LOGIN_PAGE = """<!doctype html>
<html lang="{{ lang }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} · ONE-PIX</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 16px/1.5 system-ui, sans-serif; display: grid; place-items: center; min-height: 100vh; margin: 0; }
  form { width: min(360px, 90vw); display: grid; gap: 12px; }
  h1 { font-size: 1.3rem; margin: 0; }
  input, button { font: inherit; padding: 10px 12px; border-radius: 8px; border: 1px solid #8886; }
  button { cursor: pointer; background: #1f6feb; color: #fff; border-color: transparent; }
  .error { color: #d1242f; margin: 0; }
  .hint { opacity: .7; font-size: .85rem; margin: 0; }
</style></head><body>
<form method="post" autocomplete="off">
  <h1>ONE-PIX</h1>
  <label for="token">{{ prompt }}</label>
  <input id="token" name="token" type="password" autofocus required>
  {% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
  <input type="hidden" name="next" value="{{ next }}">
  <button type="submit">{{ submit }}</button>
  <p class="hint">{{ hint }}</p>
</form></body></html>"""

bp = Blueprint("web_auth", __name__)


def is_loopback(host):
    """True for localhost and loopback addresses (127.0.0.0/8, ::1)."""
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def server_settings(environ=None):
    """(host, port, token) from the environment. Raises RuntimeError, with a message to show as is,
    when the interface would listen beyond this machine without a token."""
    environ = os.environ if environ is None else environ
    host = environ.get("ONEPIX_HOST", "127.0.0.1").strip() or "127.0.0.1"
    token = environ.get("ONEPIX_WEB_TOKEN") or None
    try:
        port = int(environ.get("ONEPIX_PORT", "5000"))
    except ValueError:
        raise RuntimeError("ONEPIX_PORT must be a number") from None
    if not is_loopback(host) and not token:
        raise RuntimeError(
            f"ONEPIX_HOST={host} opens the web interface to the network: set ONEPIX_WEB_TOKEN to a "
            "secret first, e.g.\n  export ONEPIX_WEB_TOKEN=$(python -c "
            "'import secrets; print(secrets.token_urlsafe(32))')\nor leave ONEPIX_HOST unset to "
            "listen on this machine only."
        )
    return host, port, token


def _safe_next(target):
    """`target` if it is a path of this site, else the home page (no redirect to another site)."""
    if not target:
        return "/"
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//"):
        return "/"
    return target


def init_auth(app, token):
    """Require `token` on every request of `app` (no-op when token is empty)."""
    app.config["ONEPIX_AUTH_ENABLED"] = bool(token)
    if not token:
        return

    register_translations(TRANSLATIONS)
    # sessions do not survive a restart, which only means signing in again
    app.secret_key = secrets.token_urlsafe(32)
    app.config.update(
        SESSION_COOKIE_NAME="onepix_session",
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_HTTPONLY=True,
    )
    app.config["ONEPIX_WEB_TOKEN"] = token
    app.register_blueprint(bp)

    @app.context_processor
    def _auth_context():
        return {"auth_enabled": True}

    @app.before_request
    def _require_token():
        if request.path in (LOGIN_PATH,):
            return None
        if session.get("authenticated") is True:
            return None
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer ") and hmac.compare_digest(header[7:].encode(), token.encode()):
            return None
        # a browser navigating gets the sign-in page; fetch() and scripts get a 401
        if request.method == "GET" and request.accept_mimetypes.best == "text/html":
            return redirect(url_for("web_auth.login", next=request.full_path.rstrip("?")))
        return jsonify({"error": "authentication required"}), 401


@bp.route(LOGIN_PATH, methods=["GET", "POST"])
def login():
    from flask import current_app
    token = current_app.config["ONEPIX_WEB_TOKEN"]
    target = _safe_next(request.values.get("next"))
    error = None
    status = 200
    if request.method == "POST":
        given = request.form.get("token", "")
        if hmac.compare_digest(given.encode(), token.encode()):
            session.clear()
            session["authenticated"] = True
            return redirect(target)
        time.sleep(0.5)                      # slows down guessing
        error, status = t("auth.error"), 401
    lang = current_lang()
    return render_template_string(
        LOGIN_PAGE, lang=lang, title=t("auth.title"), prompt=t("auth.prompt"), submit=t("auth.submit"),
        hint=t("auth.hint"), error=error, next=target,
    ), status


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("web_auth.login"))
