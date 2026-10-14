import os
import json
import logging

from flask import Flask, redirect, url_for, request, make_response

from i18n import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    LANGUAGE_COOKIE,
    TRANSLATIONS,
    current_lang,
    t,
)

from blueprints.acquisition import (
    bp as acquisition_bp
)

from blueprints.analysis import (
    bp as analysis_bp,
    routes as analysis_routes
)

from blueprints.data_manager import (
    bp as data_manager_bp
)

from blueprints.plugins_manager import (
    bp as plugins_manager_bp
)

from blueprints.logs import (
    bp as logs_bp
)

from blueprints.acquisition import tuning

import gui_plugins

logger = logging.getLogger(__name__)

# Cookie-based theme preference, same pattern as LANGUAGE_COOKIE. Unlike
# language, toggling it doesn't need a server round-trip (no text to
# re-render), so there's no /set-theme route — the toggle button in the
# nav sets this cookie directly from JS. Reading it here is only to
# render the right data-theme attribute on the very first paint of a
# fresh page load, before that JS runs.
THEME_COOKIE = "onepix_theme"


def create_app():

    app = Flask(__name__)

    # ====================================
    # REGISTER BLUEPRINTS
    # ====================================

    app.register_blueprint(
        acquisition_bp
    )

    app.register_blueprint(
        analysis_bp
    )

    analysis_routes.register_imaging_method_specific_blueprints(
        app
    )

    app.register_blueprint(
        data_manager_bp
    )

    app.register_blueprint(
        plugins_manager_bp
    )

    app.register_blueprint(
        logs_bp
    )

    # ====================================
    # PLUGIN GUI EXTENSIONS
    # ====================================
    # Pages, settings panels and checks that belong to one plugin ship
    # with it and are discovered here - see gui_plugins.py.

    gui_plugins.register_analysis_pages(
        app,
        get_current_result=analysis_routes.get_current_result,
    )

    gui_plugins.register_method_extensions(
        app,
        hardware_lock=tuning.hardware_lock,
    )

    # ====================================
    # I18N
    # ====================================

    app.jinja_env.globals["t"] = t

    @app.context_processor
    def inject_i18n():
        lang = current_lang()
        theme = request.cookies.get(THEME_COOKIE, "")
        if theme not in ("light", "dark"):
            theme = ""
        return {
            "current_lang": lang,
            "supported_languages": SUPPORTED_LANGUAGES,
            "i18n_json": json.dumps(
                TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
            ),
            "plugin_pages": gui_plugins.ANALYSIS_PAGES,
            "current_theme": theme,
        }

    @app.route("/set-language/<lang>")
    def set_language(lang):

        if lang not in SUPPORTED_LANGUAGES:
            lang = DEFAULT_LANGUAGE

        target = request.referrer or url_for(
            "acquisition.acquisition_page"
        )

        response = make_response(redirect(target))

        response.set_cookie(
            LANGUAGE_COOKIE,
            lang,
            max_age=60 * 60 * 24 * 365,
        )

        return response

    # ====================================
    # HOME
    # ====================================

    @app.route("/")
    def home():

        return redirect(
            url_for(
                "acquisition.acquisition_page"
            )
        )

    return app


if __name__ == "__main__":

    app = create_app()

    # Debug mode enables the Werkzeug interactive debugger, which lets
    # anyone reaching this port run arbitrary Python on any unhandled
    # exception. Off by default; opt in explicitly for local dev only
    # with FLASK_DEBUG=1.
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=debug_mode,
        # /acquisition/run blocks for the whole acquisition (up to several
        # minutes). Without threaded=True the single-threaded dev server
        # can't serve /acquisition/progress polls (or anything else)
        # while that request is in flight.
        threaded=True,
    )
